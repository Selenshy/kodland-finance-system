from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import require_entity_role
from app.models.enums import Role
from app.models.journal import JournalEntry, JournalLine
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.journal import (
    BulkEditRequest,
    BulkEditResult,
    JournalEntryCreate,
    JournalEntryOut,
    JournalEntryUpdate,
)
from app.services import audit_service, journal_service

router = APIRouter(prefix="/api/legal-entities/{legal_entity_id}/journal-entries", tags=["journal"])


def _get_entity(db: Session, legal_entity_id: int, account_id: int) -> LegalEntity:
    entity = db.query(LegalEntity).filter(
        LegalEntity.id == legal_entity_id, LegalEntity.account_id == account_id
    ).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal entity not found")
    return entity


@router.get("", response_model=list[JournalEntryOut])
def list_entries(
    legal_entity_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    counterparty_id: int | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.VIEWER)),
):
    _get_entity(db, legal_entity_id, user.account_id)
    q = (
        db.query(JournalEntry)
        .options(joinedload(JournalEntry.lines))
        .filter(JournalEntry.legal_entity_id == legal_entity_id)
    )
    if date_from:
        q = q.filter(JournalEntry.entry_date >= date_from)
    if date_to:
        q = q.filter(JournalEntry.entry_date <= date_to)
    if account_id:
        q = q.filter(JournalEntry.lines.any(JournalLine.account_id == account_id))
    if counterparty_id:
        q = q.filter(JournalEntry.lines.any(JournalLine.counterparty_id == counterparty_id))
    return (
        q.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .distinct()
        .offset(offset)
        .limit(min(limit, 1000))
        .all()
    )


@router.post("", response_model=JournalEntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    legal_entity_id: int,
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    entity = _get_entity(db, legal_entity_id, user.account_id)
    if payload.legal_entity_id != legal_entity_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="legal_entity_id mismatch")
    try:
        entry = journal_service.create_entry(db, entity, payload, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=JournalEntryOut)
def update_entry(
    legal_entity_id: int,
    entry_id: int,
    payload: JournalEntryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    entity = _get_entity(db, legal_entity_id, user.account_id)
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.legal_entity_id == legal_entity_id
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

    if payload.entry_date is not None and payload.entry_date != entry.entry_date:
        audit_service.log_change(db, "journal_entries", entry.id, "entry_date", entry.entry_date, payload.entry_date, user.id)
        entry.entry_date = payload.entry_date
    if payload.description is not None and payload.description != entry.description:
        audit_service.log_change(db, "journal_entries", entry.id, "description", entry.description, payload.description, user.id)
        entry.description = payload.description

    if payload.lines is not None:
        audit_service.log_change(db, "journal_entries", entry.id, "lines", f"{len(entry.lines)} lines", f"{len(payload.lines)} lines", user.id)
        entry.lines.clear()
        db.flush()
        new_lines = [journal_service.build_line(db, entity, entry.entry_date, li) for li in payload.lines]
        try:
            journal_service.check_balance(new_lines)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        entry.lines = new_lines

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    legal_entity_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.legal_entity_id == legal_entity_id
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    audit_service.log_change(db, "journal_entries", entry.id, "deleted", "false", "true", user.id)
    db.delete(entry)
    db.commit()


@router.post("/bulk-edit", response_model=BulkEditResult)
def bulk_edit(
    legal_entity_id: int,
    payload: BulkEditRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    _get_entity(db, legal_entity_id, user.account_id)
    lines = (
        db.query(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .filter(JournalEntry.legal_entity_id == legal_entity_id, JournalEntry.id.in_(payload.entry_ids))
        .all()
    )
    updated = 0
    for line in lines:
        for field, value in (
            ("counterparty_id", payload.set_counterparty_id),
            ("cost_center_id", payload.set_cost_center_id),
            ("project_id", payload.set_project_id),
            ("account_id", payload.set_account_id),
        ):
            if value is not None:
                old_value = getattr(line, field)
                if old_value != value:
                    audit_service.log_change(db, "journal_lines", line.id, field, old_value, value, user.id)
                    setattr(line, field, value)
                    updated += 1
    db.commit()
    return BulkEditResult(updated_lines=updated)
