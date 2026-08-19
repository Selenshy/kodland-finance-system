from datetime import date

import pytest

from app.models.coa import ChartOfAccount
from app.models.enums import AccountType, CfCategory, EntryDirection
from app.models.journal import JournalEntry, JournalLine
from app.models.opening_balance import OpeningBalance
from app.services import report_engine


@pytest.fixture()
def small_ledger(db_session, seed_basic):
    entity = seed_basic["entity"]  # USD functional currency
    bank = ChartOfAccount(legal_entity_id=entity.id, code="1010", name="Bank", account_type=AccountType.ASSET, is_cash=True, report_line="CASH")
    equity = ChartOfAccount(legal_entity_id=entity.id, code="3000", name="Equity", account_type=AccountType.EQUITY, report_line="SHARE_CAPITAL")
    revenue = ChartOfAccount(legal_entity_id=entity.id, code="4000", name="Revenue", account_type=AccountType.INCOME, report_line="REVENUE", cf_category=CfCategory.OPERATING, cf_line="SALES")
    expense = ChartOfAccount(legal_entity_id=entity.id, code="5000", name="Expense", account_type=AccountType.EXPENSE, report_line="OPEX", cf_category=CfCategory.OPERATING, cf_line="OPEX")
    db_session.add_all([bank, equity, revenue, expense])
    db_session.flush()

    db_session.add(OpeningBalance(legal_entity_id=entity.id, account_id=bank.id, as_of_date=date(2025, 1, 1), local_currency_amount=1000, usd_amount=1000))
    db_session.add(OpeningBalance(legal_entity_id=entity.id, account_id=equity.id, as_of_date=date(2025, 1, 1), local_currency_amount=-1000, usd_amount=-1000))

    def line(account_id, direction, amount):
        return JournalLine(
            account_id=account_id, direction=direction, transaction_currency="USD", transaction_amount=amount,
            local_currency_amount=amount, usd_amount=amount, fx_rate_to_local=1, fx_rate_to_usd=1,
        )

    sale = JournalEntry(legal_entity_id=entity.id, entry_date=date(2025, 1, 10), description="Cash sale",
                         lines=[line(bank.id, EntryDirection.DEBIT, 500), line(revenue.id, EntryDirection.CREDIT, 500)])
    spend = JournalEntry(legal_entity_id=entity.id, entry_date=date(2025, 1, 15), description="Cash expense",
                          lines=[line(expense.id, EntryDirection.DEBIT, 200), line(bank.id, EntryDirection.CREDIT, 200)])
    db_session.add_all([sale, spend])
    db_session.commit()

    return {"entity": entity, "bank": bank, "equity": equity, "revenue": revenue, "expense": expense}


def test_pl_matches_expected_revenue_and_expense(db_session, small_ledger):
    entity = small_ledger["entity"]
    report = report_engine.compute_pl(db_session, [entity.id], date(2025, 1, 1), date(2025, 1, 31), "USD")

    revenue_section = next(s for s in report.sections if s.title == "Revenue")
    expense_section = next(s for s in report.sections if s.title == "Expenses")
    net_profit_section = next(s for s in report.sections if s.title == "Net Profit")

    assert revenue_section.total == 500
    assert expense_section.total == 200
    assert net_profit_section.total == 300


def test_balance_sheet_converges(db_session, small_ledger):
    entity = small_ledger["entity"]
    report = report_engine.compute_balance(db_session, [entity.id], date(2025, 1, 31), "USD")

    assets = next(s for s in report.sections if s.title == "Assets")
    liabilities = next(s for s in report.sections if s.title == "Liabilities")
    equity = next(s for s in report.sections if s.title == "Equity")

    assert assets.total == 1300  # 1000 opening + 500 sale - 200 expense
    assert liabilities.total == 0
    assert equity.total == 1300  # 1000 opening equity + 300 net profit to date
    assert report.check_ok is True


def test_cash_flow_direct_method_matches_cash_movement(db_session, small_ledger):
    entity = small_ledger["entity"]
    report = report_engine.compute_cf(db_session, [entity.id], date(2025, 1, 1), date(2025, 1, 31), "USD")

    net_change = next(s for s in report.sections if s.title == "Net Change in Cash")
    assert net_change.total == 300  # matches bank account movement: +500 - 200
