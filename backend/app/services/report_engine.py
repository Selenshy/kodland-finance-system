"""Report engine for P&L, direct-method Cash Flow, and Balance.

IAS 21 translation rule, applied whenever a line must be shown in a
currency other than the amount already stored on it:
  - P&L movements are translated at the rate on the transaction date
    (`fx_service.get_rate`), because each is a distinct historical event.
  - Balance sheet (point-in-time) items are translated at the closing
    rate for the period end (`fx_service.get_closing_rate`), because IAS
    21 requires all monetary balances to be restated at one rate as of
    the reporting date, not at each contributing transaction's own rate.

Every journal line already carries `local_currency_amount` (its legal
entity's own functional currency) and `usd_amount`, both computed at the
transaction-date rate when the line was posted. Displaying in the
entity's own functional currency or in USD is therefore just reading the
stored figure. Displaying in any third currency (e.g. a group report
shown in one particular entity's local currency, when other entities
have a different functional currency) requires one extra conversion,
done here via the FX service using the rule above.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.coa import ChartOfAccount
from app.models.enums import AccountType, EntryDirection
from app.models.journal import JournalEntry, JournalLine
from app.models.opening_balance import OpeningBalance
from app.schemas.reports import ReportLineOut, ReportOut, ReportSectionOut
from app.services import fx_service


def _signed_debit_positive(amount: float, direction: EntryDirection) -> float:
    return amount if direction == EntryDirection.DEBIT else -amount


@dataclass
class _Ctx:
    db: Session
    legal_entity_ids: list[int]
    currency: str
    entity_functional_currency: dict[int, str]
    period_end: date
    _closing_rate_cache: dict[str, float] = field(default_factory=dict)
    _txn_rate_cache: dict[tuple[str, date], float] = field(default_factory=dict)

    def balance_amount(self, account_local_currency: str, amount_local: float, amount_usd: float) -> float:
        if self.currency == account_local_currency:
            return amount_local
        if self.currency == "USD":
            return amount_usd
        key = self.currency
        if key not in self._closing_rate_cache:
            self._closing_rate_cache[key] = fx_service.get_closing_rate(self.db, self.period_end, "USD", self.currency)
        return amount_usd * self._closing_rate_cache[key]

    def flow_amount(self, account_local_currency: str, amount_local: float, amount_usd: float, txn_date: date) -> float:
        if self.currency == account_local_currency:
            return amount_local
        if self.currency == "USD":
            return amount_usd
        key = (self.currency, txn_date)
        if key not in self._txn_rate_cache:
            self._txn_rate_cache[key] = fx_service.get_rate(self.db, txn_date, "USD", self.currency)
        return amount_usd * self._txn_rate_cache[key]


def _accounts_by_id(db: Session, legal_entity_ids: list[int]) -> dict[int, ChartOfAccount]:
    rows = db.query(ChartOfAccount).filter(ChartOfAccount.legal_entity_id.in_(legal_entity_ids)).all()
    return {a.id: a for a in rows}


def _entities_functional_currency(db, legal_entity_ids: list[int]) -> dict[int, str]:
    from app.models.legal_entity import LegalEntity

    rows = db.query(LegalEntity).filter(LegalEntity.id.in_(legal_entity_ids)).all()
    return {e.id: e.functional_currency for e in rows}


def _section(title: str, grouped: dict[str, float]) -> ReportSectionOut:
    lines = [ReportLineOut(code=code, label=code, amount=round(amt, 2)) for code, amt in sorted(grouped.items())]
    total = round(sum(grouped.values()), 2)
    return ReportSectionOut(title=title, lines=lines, total=total)


def compute_pl(
    db: Session, legal_entity_ids: list[int], period_start: date, period_end: date, currency: str
) -> ReportOut:
    entity_currency = _entities_functional_currency(db, legal_entity_ids)
    accounts = _accounts_by_id(db, legal_entity_ids)
    ctx = _Ctx(db, legal_entity_ids, currency, entity_currency, period_end)

    revenue: dict[str, float] = defaultdict(float)
    expense: dict[str, float] = defaultdict(float)

    q = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .filter(JournalEntry.legal_entity_id.in_(legal_entity_ids))
        .filter(JournalEntry.entry_date >= period_start, JournalEntry.entry_date <= period_end)
    )
    for line, entry in q:
        account = accounts.get(line.account_id)
        if account is None or account.account_type not in (AccountType.INCOME, AccountType.EXPENSE):
            continue
        local_ccy = entity_currency[entry.legal_entity_id]
        amt = ctx.flow_amount(local_ccy, float(line.local_currency_amount), float(line.usd_amount), entry.entry_date)
        signed = _signed_debit_positive(amt, line.direction)
        report_line = account.report_line or account.account_type.value.upper()
        if account.account_type == AccountType.INCOME:
            revenue[report_line] += -signed  # credit-positive
        else:
            expense[report_line] += signed  # debit-positive

    revenue_section = _section("Revenue", revenue)
    expense_section = _section("Expenses", expense)
    net_profit = round(revenue_section.total - expense_section.total, 2)

    return ReportOut(
        report_type="pl",
        legal_entity_ids=legal_entity_ids,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        sections=[
            revenue_section,
            expense_section,
            ReportSectionOut(title="Net Profit", lines=[ReportLineOut(code="NET_PROFIT", label="Net Profit", amount=net_profit, is_subtotal=True)], total=net_profit),
        ],
    )


def compute_balance(db: Session, legal_entity_ids: list[int], period_end: date, currency: str) -> ReportOut:
    entity_currency = _entities_functional_currency(db, legal_entity_ids)
    accounts = _accounts_by_id(db, legal_entity_ids)
    ctx = _Ctx(db, legal_entity_ids, currency, entity_currency, period_end)

    balances: dict[int, float] = defaultdict(float)  # account_id -> debit-positive amount, in display currency

    for ob in db.query(OpeningBalance).filter(
        OpeningBalance.legal_entity_id.in_(legal_entity_ids), OpeningBalance.as_of_date <= period_end
    ):
        account = accounts.get(ob.account_id)
        if account is None:
            continue
        local_ccy = entity_currency[ob.legal_entity_id]
        amt = ctx.balance_amount(local_ccy, float(ob.local_currency_amount), float(ob.usd_amount))
        balances[ob.account_id] += amt

    q = (
        db.query(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .filter(JournalEntry.legal_entity_id.in_(legal_entity_ids))
        .filter(JournalEntry.entry_date <= period_end)
    )
    for line, entry in q:
        account = accounts.get(line.account_id)
        if account is None:
            continue
        local_ccy = entity_currency[entry.legal_entity_id]
        amt = ctx.balance_amount(local_ccy, float(line.local_currency_amount), float(line.usd_amount))
        balances[line.account_id] += _signed_debit_positive(amt, line.direction)

    assets: dict[str, float] = defaultdict(float)
    liabilities: dict[str, float] = defaultdict(float)
    equity: dict[str, float] = defaultdict(float)
    cumulative_income = 0.0
    cumulative_expense = 0.0

    for account_id, debit_positive in balances.items():
        account = accounts[account_id]
        report_line = account.report_line or account.account_type.value.upper()
        if account.account_type == AccountType.ASSET:
            assets[report_line] += debit_positive
        elif account.account_type == AccountType.LIABILITY:
            liabilities[report_line] += -debit_positive
        elif account.account_type == AccountType.EQUITY:
            equity[report_line] += -debit_positive
        elif account.account_type == AccountType.INCOME:
            cumulative_income += -debit_positive
        elif account.account_type == AccountType.EXPENSE:
            cumulative_expense += debit_positive

    net_profit_to_date = round(cumulative_income - cumulative_expense, 2)
    equity["RETAINED_EARNINGS_CURRENT"] = equity.get("RETAINED_EARNINGS_CURRENT", 0.0) + net_profit_to_date

    assets_section = _section("Assets", assets)
    liabilities_section = _section("Liabilities", liabilities)
    equity_section = _section("Equity", equity)
    check_ok = abs(assets_section.total - (liabilities_section.total + equity_section.total)) < 0.05

    return ReportOut(
        report_type="balance",
        legal_entity_ids=legal_entity_ids,
        period_start=period_end,
        period_end=period_end,
        currency=currency,
        sections=[assets_section, liabilities_section, equity_section],
        check_ok=check_ok,
    )


def compute_cf(
    db: Session, legal_entity_ids: list[int], period_start: date, period_end: date, currency: str
) -> ReportOut:
    entity_currency = _entities_functional_currency(db, legal_entity_ids)
    accounts = _accounts_by_id(db, legal_entity_ids)
    ctx = _Ctx(db, legal_entity_ids, currency, entity_currency, period_end)

    by_category: dict[str, dict[str, float]] = {
        "operating": defaultdict(float),
        "investing": defaultdict(float),
        "financing": defaultdict(float),
    }

    q = (
        db.query(JournalEntry)
        .filter(JournalEntry.legal_entity_id.in_(legal_entity_ids))
        .filter(JournalEntry.entry_date >= period_start, JournalEntry.entry_date <= period_end)
    )
    for entry in q:
        has_cash_line = any(accounts[l.account_id].is_cash for l in entry.lines if l.account_id in accounts)
        if not has_cash_line:
            continue
        local_ccy = entity_currency[entry.legal_entity_id]
        for line in entry.lines:
            account = accounts.get(line.account_id)
            if account is None or account.is_cash:
                continue
            amt = ctx.flow_amount(local_ccy, float(line.local_currency_amount), float(line.usd_amount), entry.entry_date)
            contribution = -_signed_debit_positive(amt, line.direction)
            category = (account.cf_category.value if account.cf_category else "operating")
            cf_line = account.cf_line or account.report_line or "OTHER"
            by_category[category][cf_line] += contribution

    sections = [
        _section("Operating Activities", by_category["operating"]),
        _section("Investing Activities", by_category["investing"]),
        _section("Financing Activities", by_category["financing"]),
    ]
    net_change = round(sum(s.total for s in sections), 2)
    sections.append(
        ReportSectionOut(
            title="Net Change in Cash",
            lines=[ReportLineOut(code="NET_CHANGE_IN_CASH", label="Net Change in Cash", amount=net_change, is_subtotal=True)],
            total=net_change,
        )
    )

    return ReportOut(
        report_type="cf",
        legal_entity_ids=legal_entity_ids,
        period_start=period_start,
        period_end=period_end,
        currency=currency,
        sections=sections,
    )
