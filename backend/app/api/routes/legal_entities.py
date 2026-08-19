from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import accessible_entity_ids, get_current_user, require_global_role
from app.models.coa import ChartOfAccount
from app.models.enums import Role
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.legal_entity import LegalEntityCreate, LegalEntityOut, LegalEntityUpdate

router = APIRouter(prefix="/api/legal-entities", tags=["legal-entities"])


@router.get("", response_model=list[LegalEntityOut])
def list_legal_entities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(LegalEntity).filter(LegalEntity.account_id == user.account_id)
    allowed = accessible_entity_ids(user, db)
    if allowed is not None:
        q = q.filter(LegalEntity.id.in_(allowed))
    return q.all()


@router.post("", response_model=LegalEntityOut, status_code=status.HTTP_201_CREATED)
def create_legal_entity(
    payload: LegalEntityCreate, db: Session = Depends(get_db), admin: User = Depends(require_global_role(Role.ADMIN))
):
    entity = LegalEntity(
        account_id=admin.account_id,
        name=payload.name,
        country=payload.country,
        functional_currency=payload.functional_currency,
    )
    db.add(entity)
    db.flush()

    if payload.copy_coa_from_entity_id:
        source_accounts = (
            db.query(ChartOfAccount)
            .filter(ChartOfAccount.legal_entity_id == payload.copy_coa_from_entity_id)
            .order_by(ChartOfAccount.id)
            .all()
        )
        id_map: dict[int, int] = {}
        for src in source_accounts:
            clone = ChartOfAccount(
                legal_entity_id=entity.id,
                parent_id=id_map.get(src.parent_id) if src.parent_id else None,
                code=src.code,
                name=src.name,
                account_type=src.account_type,
                report_line=src.report_line,
                is_cash=src.is_cash,
                cf_category=src.cf_category,
                cf_line=src.cf_line,
                is_postable=src.is_postable,
                is_active=src.is_active,
            )
            db.add(clone)
            db.flush()
            id_map[src.id] = clone.id

    db.commit()
    db.refresh(entity)
    return entity


@router.patch("/{legal_entity_id}", response_model=LegalEntityOut)
def update_legal_entity(
    legal_entity_id: int,
    payload: LegalEntityUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_global_role(Role.ADMIN)),
):
    entity = db.query(LegalEntity).filter(
        LegalEntity.id == legal_entity_id, LegalEntity.account_id == admin.account_id
    ).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal entity not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)

    db.commit()
    db.refresh(entity)
    return entity
