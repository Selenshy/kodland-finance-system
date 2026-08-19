"""Seed demo data: a tenant account with 3 legal entities in different
functional currencies, a chart of accounts each, opening balances as of
2025-01-01, and a few dozen journal entries spanning Jan-Mar 2025 --
enough to exercise multi-currency conversion, accrual P&L, direct-method
CF, and a balancing Balance Sheet end to end.

Run with:  .venv/Scripts/python.exe scripts/seed.py
Idempotent: safe to re-run against an empty-ish demo account (skips if
the demo tenant account already exists).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.coa import ChartOfAccount
from app.models.currency import Currency
from app.models.enums import AccountType, CfCategory, EntryDirection, Role
from app.models.legal_entity import LegalEntity
from app.models.opening_balance import OpeningBalance
from app.models.tenant import TenantAccount, User
from app.services.fx_service import get_rate
from app.services.journal_service import build_line
from app.schemas.journal import JournalLineCreate

CURRENCIES = [("USD", "US Dollar"), ("RUB", "Russian Ruble"), ("EUR", "Euro")]

COA_TEMPLATE = [
    dict(code="1000", name="Cash and Cash Equivalents", parent=None, account_type=AccountType.ASSET, is_postable=False, report_line="CASH"),
    dict(code="1010", name="Operating Bank Account", parent="1000", account_type=AccountType.ASSET, is_cash=True, report_line="CASH"),
    dict(code="1020", name="Cash on Hand", parent="1000", account_type=AccountType.ASSET, is_cash=True, report_line="CASH"),
    dict(code="1100", name="Accounts Receivable", parent=None, account_type=AccountType.ASSET, report_line="AR"),
    dict(code="1200", name="Fixed Assets", parent=None, account_type=AccountType.ASSET, report_line="PPE", cf_category=CfCategory.INVESTING, cf_line="CAPEX"),
    dict(code="2000", name="Accounts Payable", parent=None, account_type=AccountType.LIABILITY, report_line="AP"),
    dict(code="2100", name="Loans Payable", parent=None, account_type=AccountType.LIABILITY, report_line="LOANS", cf_category=CfCategory.FINANCING, cf_line="LOAN_PROCEEDS_REPAYMENT"),
    dict(code="2200", name="Taxes Payable", parent=None, account_type=AccountType.LIABILITY, report_line="TAXES_PAYABLE", cf_category=CfCategory.OPERATING, cf_line="TAXES_PAID"),
    dict(code="3000", name="Share Capital", parent=None, account_type=AccountType.EQUITY, report_line="SHARE_CAPITAL", cf_category=CfCategory.FINANCING, cf_line="CAPITAL_CONTRIBUTIONS"),
    dict(code="3100", name="Retained Earnings", parent=None, account_type=AccountType.EQUITY, report_line="RETAINED_EARNINGS"),
    dict(code="4000", name="Sales Revenue", parent=None, account_type=AccountType.INCOME, report_line="REVENUE", cf_category=CfCategory.OPERATING, cf_line="RECEIPTS_FROM_CUSTOMERS"),
    dict(code="4100", name="Other Income", parent=None, account_type=AccountType.INCOME, report_line="OTHER_INCOME", cf_category=CfCategory.OPERATING, cf_line="OTHER_RECEIPTS"),
    dict(code="5000", name="Cost of Services", parent=None, account_type=AccountType.EXPENSE, report_line="COGS", cf_category=CfCategory.OPERATING, cf_line="PAYMENTS_TO_SUPPLIERS"),
    dict(code="5100", name="Salaries and Wages", parent=None, account_type=AccountType.EXPENSE, report_line="OPEX_SALARIES", cf_category=CfCategory.OPERATING, cf_line="PAYMENTS_TO_EMPLOYEES"),
    dict(code="5200", name="Rent Expense", parent=None, account_type=AccountType.EXPENSE, report_line="OPEX_RENT", cf_category=CfCategory.OPERATING, cf_line="PAYMENTS_TO_SUPPLIERS"),
    dict(code="5300", name="Marketing Expense", parent=None, account_type=AccountType.EXPENSE, report_line="OPEX_MARKETING", cf_category=CfCategory.OPERATING, cf_line="PAYMENTS_TO_SUPPLIERS"),
    dict(code="5900", name="Tax Expense", parent=None, account_type=AccountType.EXPENSE, report_line="TAX_EXPENSE", cf_category=CfCategory.OPERATING, cf_line="TAXES_PAID"),
]

ENTITIES = [
    dict(name="Kodland LLC", country="Russia", functional_currency="RUB", opening_cash=5_000_000),
    dict(name="Kodland Games Inc", country="United States", functional_currency="USD", opening_cash=200_000),
    dict(name="Kodland Europe s.r.o.", country="Czech Republic", functional_currency="EUR", opening_cash=150_000),
]

OPENING_DATE = date(2025, 1, 1)


def build_coa(db, entity_id: int) -> dict[str, ChartOfAccount]:
    by_code: dict[str, ChartOfAccount] = {}
    for row in COA_TEMPLATE:
        account = ChartOfAccount(
            legal_entity_id=entity_id,
            code=row["code"],
            name=row["name"],
            account_type=row["account_type"],
            is_cash=row.get("is_cash", False),
            is_postable=row.get("is_postable", True),
            report_line=row.get("report_line", ""),
            cf_category=row.get("cf_category"),
            cf_line=row.get("cf_line", ""),
        )
        db.add(account)
        db.flush()
        by_code[row["code"]] = account
    for row in COA_TEMPLATE:
        if row["parent"]:
            by_code[row["code"]].parent_id = by_code[row["parent"]].id
    db.flush()
    return by_code


def add_entry(db, entity, coa, entry_date, description, debit_code, credit_code, amount, currency=None):
    from app.models.journal import JournalEntry

    currency = currency or entity.functional_currency
    debit = build_line(db, entity, entry_date, JournalLineCreate(
        account_id=coa[debit_code].id, direction=EntryDirection.DEBIT,
        transaction_currency=currency, transaction_amount=amount,
    ))
    credit = build_line(db, entity, entry_date, JournalLineCreate(
        account_id=coa[credit_code].id, direction=EntryDirection.CREDIT,
        transaction_currency=currency, transaction_amount=amount,
    ))
    entry = JournalEntry(legal_entity_id=entity.id, entry_date=entry_date, description=description, lines=[debit, credit])
    db.add(entry)
    db.flush()


def demo_entries(entity):
    fc = entity.functional_currency
    cash = 1_000_000 if fc == "RUB" else (10_000 if fc == "USD" else 8_000)
    return [
        (date(2025, 1, 10), "Invoice issued to customer", "1100", "4000", cash * 1.2, fc),
        (date(2025, 1, 20), "Customer payment received", "1010", "1100", cash * 1.2, fc),
        (date(2025, 1, 25), "January salaries paid", "5100", "1010", cash * 0.4, fc),
        (date(2025, 1, 28), "Office rent paid", "5200", "1010", cash * 0.1, fc),
        (date(2025, 2, 3), "Marketing campaign paid", "5300", "1010", cash * 0.08, fc),
        (date(2025, 2, 8), "Invoice issued to customer", "1100", "4000", cash * 1.5, fc),
        (date(2025, 2, 15), "Customer payment received", "1010", "1100", cash * 1.0, fc),
        (date(2025, 2, 25), "February salaries paid", "5100", "1010", cash * 0.42, fc),
        (date(2025, 2, 26), "Office rent paid", "5200", "1010", cash * 0.1, fc),
        (date(2025, 2, 27), "Subcontractor services invoiced", "5000", "2000", cash * 0.3, fc),
        (date(2025, 3, 1), "Paid subcontractor invoice", "2000", "1010", cash * 0.3, fc),
        (date(2025, 3, 5), "Bank loan drawdown", "1010", "2100", cash * 0.6, fc),
        (date(2025, 3, 10), "Purchased office equipment", "1200", "1010", cash * 0.25, fc),
        (date(2025, 3, 12), "Invoice issued to customer", "1100", "4000", cash * 1.3, fc),
        (date(2025, 3, 20), "Customer payment received", "1010", "1100", cash * 1.3, fc),
        (date(2025, 3, 25), "March salaries paid", "5100", "1010", cash * 0.42, fc),
        (date(2025, 3, 26), "Office rent paid", "5200", "1010", cash * 0.1, fc),
        (date(2025, 3, 28), "Quarterly tax accrued", "5900", "2200", cash * 0.18, fc),
        (date(2025, 3, 30), "Quarterly tax paid", "2200", "1010", cash * 0.18, fc),
        (date(2025, 3, 31), "Interest / other income received", "1010", "4100", cash * 0.03, fc),
    ]


def main():
    db = SessionLocal()
    try:
        if db.query(TenantAccount).filter(TenantAccount.name == "Kodland Demo").first():
            print("Demo account already seeded, skipping.")
            return

        for code, name in CURRENCIES:
            if not db.get(Currency, code):
                db.add(Currency(code=code, name=name))
        db.flush()

        tenant = TenantAccount(name="Kodland Demo")
        db.add(tenant)
        db.flush()

        admin = User(
            account_id=tenant.id,
            email="admin@demo.kodland-finance.app",
            hashed_password=hash_password("Admin12345!"),
            full_name="Demo Admin",
            global_role=Role.ADMIN,
        )
        accountant = User(
            account_id=tenant.id,
            email="accountant@demo.kodland-finance.app",
            hashed_password=hash_password("Accountant12345!"),
            full_name="Demo Accountant",
            global_role=Role.ACCOUNTANT,
        )
        viewer = User(
            account_id=tenant.id,
            email="viewer@demo.kodland-finance.app",
            hashed_password=hash_password("Viewer12345!"),
            full_name="Demo Viewer",
            global_role=Role.VIEWER,
        )
        db.add_all([admin, accountant, viewer])
        db.flush()

        for spec in ENTITIES:
            entity = LegalEntity(
                account_id=tenant.id,
                name=spec["name"],
                country=spec["country"],
                functional_currency=spec["functional_currency"],
            )
            db.add(entity)
            db.flush()

            coa = build_coa(db, entity.id)

            opening_cash = spec["opening_cash"]
            usd_rate = get_rate(db, OPENING_DATE, entity.functional_currency, "USD")
            db.add(OpeningBalance(
                legal_entity_id=entity.id, account_id=coa["1010"].id, as_of_date=OPENING_DATE,
                local_currency_amount=opening_cash, usd_amount=round(opening_cash * usd_rate, 2),
            ))
            db.add(OpeningBalance(
                legal_entity_id=entity.id, account_id=coa["3000"].id, as_of_date=OPENING_DATE,
                local_currency_amount=-opening_cash, usd_amount=round(-opening_cash * usd_rate, 2),
            ))
            db.flush()

            for entry_date, desc, debit_code, credit_code, amount, currency in demo_entries(entity):
                add_entry(db, entity, coa, entry_date, desc, debit_code, credit_code, round(amount, 2), currency)

            print(f"Seeded {entity.name} ({entity.functional_currency}): {len(coa)} accounts, {len(demo_entries(entity))} journal entries")

        db.commit()
        print("\nDemo login credentials:")
        print("  admin@demo.kodland-finance.app       / Admin12345!")
        print("  accountant@demo.kodland-finance.app  / Accountant12345!")
        print("  viewer@demo.kodland-finance.app      / Viewer12345!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
