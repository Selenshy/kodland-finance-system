from datetime import date

from sqlalchemy.orm import Session

from app.models.enums import EntryDirection
from app.models.journal import JournalEntry, JournalLine
from app.models.legal_entity import LegalEntity
from app.schemas.journal import JournalEntryCreate, JournalLineCreate
from app.services.fx_service import get_rate

BALANCE_TOLERANCE = 0.01


def build_line(
    db: Session, legal_entity: LegalEntity, entry_date: date, line_in: JournalLineCreate
) -> JournalLine:
    fx_to_local = get_rate(db, entry_date, line_in.transaction_currency, legal_entity.functional_currency)
    fx_to_usd = get_rate(db, entry_date, line_in.transaction_currency, "USD")

    return JournalLine(
        account_id=line_in.account_id,
        cost_center_id=line_in.cost_center_id,
        counterparty_id=line_in.counterparty_id,
        project_id=line_in.project_id,
        direction=line_in.direction,
        transaction_currency=line_in.transaction_currency,
        transaction_amount=line_in.transaction_amount,
        local_currency_amount=round(line_in.transaction_amount * fx_to_local, 2),
        usd_amount=round(line_in.transaction_amount * fx_to_usd, 2),
        fx_rate_to_local=fx_to_local,
        fx_rate_to_usd=fx_to_usd,
        memo=line_in.memo,
    )


def check_balance(lines: list[JournalLine]) -> None:
    debit_total = sum(l.local_currency_amount for l in lines if l.direction == EntryDirection.DEBIT)
    credit_total = sum(l.local_currency_amount for l in lines if l.direction == EntryDirection.CREDIT)
    if abs(debit_total - credit_total) > BALANCE_TOLERANCE:
        raise ValueError(
            f"Entry does not balance: debit {debit_total:.2f} vs credit {credit_total:.2f} "
            "(in functional currency)"
        )


def create_entry(
    db: Session, legal_entity: LegalEntity, entry_in: JournalEntryCreate, created_by_user_id: int | None
) -> JournalEntry:
    lines = [build_line(db, legal_entity, entry_in.entry_date, li) for li in entry_in.lines]
    check_balance(lines)

    entry = JournalEntry(
        legal_entity_id=legal_entity.id,
        entry_date=entry_in.entry_date,
        description=entry_in.description,
        created_by_user_id=created_by_user_id,
        lines=lines,
    )
    db.add(entry)
    db.flush()
    return entry
