from datetime import date

import pytest

from app.models.coa import ChartOfAccount
from app.models.enums import AccountType, EntryDirection
from app.models.currency import FxRate
from app.schemas.journal import JournalLineCreate
from app.services import fx_service, journal_service


def test_fx_rate_cache_hit_avoids_provider_call(db_session, seed_basic):
    """Once a rate is stored in fx_rates, get_rate must use it and never
    reach out to a network provider (providers aren't reachable/desired
    in a unit test)."""
    db_session.add(FxRate(rate_date=date(2025, 1, 15), currency_from="EUR", currency_to="USD", rate=1.05, source="test"))
    db_session.commit()

    rate = fx_service.get_rate(db_session, date(2025, 1, 15), "EUR", "USD")
    assert rate == 1.05


def test_fx_rate_inverse_lookup(db_session, seed_basic):
    db_session.add(FxRate(rate_date=date(2025, 1, 15), currency_from="USD", currency_to="EUR", rate=0.9, source="test"))
    db_session.commit()

    rate = fx_service.get_rate(db_session, date(2025, 1, 15), "EUR", "USD")
    assert rate == pytest.approx(1 / 0.9)


def test_build_line_computes_all_three_amounts(db_session, seed_basic):
    entity = seed_basic["entity"]  # functional_currency = USD
    account = ChartOfAccount(legal_entity_id=entity.id, code="1010", name="Bank", account_type=AccountType.ASSET, is_cash=True)
    db_session.add(account)
    db_session.flush()

    db_session.add(FxRate(rate_date=date(2025, 2, 1), currency_from="EUR", currency_to="USD", rate=1.1, source="test"))
    db_session.commit()

    line_in = JournalLineCreate(account_id=account.id, direction=EntryDirection.DEBIT, transaction_currency="EUR", transaction_amount=100)
    line = journal_service.build_line(db_session, entity, date(2025, 2, 1), line_in)

    assert line.transaction_amount == 100
    assert line.local_currency_amount == pytest.approx(110.0)  # entity functional currency is USD
    assert line.usd_amount == pytest.approx(110.0)
    assert line.fx_rate_to_local == pytest.approx(1.1)
    assert line.fx_rate_to_usd == pytest.approx(1.1)


def test_check_balance_rejects_unbalanced_entry(db_session, seed_basic):
    entity = seed_basic["entity"]
    a1 = ChartOfAccount(legal_entity_id=entity.id, code="1010", name="Bank", account_type=AccountType.ASSET)
    a2 = ChartOfAccount(legal_entity_id=entity.id, code="4000", name="Revenue", account_type=AccountType.INCOME)
    db_session.add_all([a1, a2])
    db_session.flush()

    debit = journal_service.build_line(
        db_session, entity, date(2025, 2, 1),
        JournalLineCreate(account_id=a1.id, direction=EntryDirection.DEBIT, transaction_currency="USD", transaction_amount=100),
    )
    credit = journal_service.build_line(
        db_session, entity, date(2025, 2, 1),
        JournalLineCreate(account_id=a2.id, direction=EntryDirection.CREDIT, transaction_currency="USD", transaction_amount=99),
    )

    with pytest.raises(ValueError, match="does not balance"):
        journal_service.check_balance([debit, credit])


def test_check_balance_accepts_balanced_entry(db_session, seed_basic):
    entity = seed_basic["entity"]
    a1 = ChartOfAccount(legal_entity_id=entity.id, code="1010", name="Bank", account_type=AccountType.ASSET)
    a2 = ChartOfAccount(legal_entity_id=entity.id, code="4000", name="Revenue", account_type=AccountType.INCOME)
    db_session.add_all([a1, a2])
    db_session.flush()

    debit = journal_service.build_line(
        db_session, entity, date(2025, 2, 1),
        JournalLineCreate(account_id=a1.id, direction=EntryDirection.DEBIT, transaction_currency="USD", transaction_amount=100),
    )
    credit = journal_service.build_line(
        db_session, entity, date(2025, 2, 1),
        JournalLineCreate(account_id=a2.id, direction=EntryDirection.CREDIT, transaction_currency="USD", transaction_amount=100),
    )

    journal_service.check_balance([debit, credit])  # should not raise
