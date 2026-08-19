from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_entity_role
from app.models.enums import Role
from app.models.opening_balance import OpeningBalance
from app.models.tenant import User
from app.schemas.opening_balance import OpeningBalanceIn, OpeningBalanceOut

router = APIRouter(prefix="/api/legal-entities/{legal_entity_id}/opening-balances", tags=["opening-balances"])


@router.get("", response_model=list[OpeningBalanceOut])
def list_opening_balances(
    legal_entity_id: int, db: Session = Depends(get_db), _user: User = Depends(require_entity_role(Role.VIEWER))
):
    return (
        db.query(OpeningBalance)
        .filter(OpeningBalance.legal_entity_id == legal_entity_id)
        .order_by(OpeningBalance.account_id)
        .all()
    )


@router.put("", response_model=OpeningBalanceOut)
def upsert_opening_balance(
    legal_entity_id: int,
    payload: OpeningBalanceIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    existing = (
        db.query(OpeningBalance)
        .filter(
            OpeningBalance.legal_entity_id == legal_entity_id,
            OpeningBalance.account_id == payload.account_id,
            OpeningBalance.as_of_date == payload.as_of_date,
        )
        .first()
    )
    if existing:
        existing.local_currency_amount = payload.local_currency_amount
        existing.usd_amount = payload.usd_amount
        row = existing
    else:
        row = OpeningBalance(legal_entity_id=legal_entity_id, **payload.model_dump())
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{opening_balance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opening_balance(
    legal_entity_id: int,
    opening_balance_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    row = db.query(OpeningBalance).filter(
        OpeningBalance.id == opening_balance_id, OpeningBalance.legal_entity_id == legal_entity_id
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(row)
    db.commit()
