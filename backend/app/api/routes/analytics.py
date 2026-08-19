from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_entity_role
from app.models.analytics import CostCenter, Counterparty, Project
from app.models.enums import Role
from app.models.tenant import User
from app.schemas.analytics import DimensionCreate, DimensionOut, DimensionUpdate


def build_dimension_router(model, slug: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=f"/api/legal-entities/{{legal_entity_id}}/{slug}", tags=[tag])

    @router.get("", response_model=list[DimensionOut])
    def list_items(
        legal_entity_id: int, db: Session = Depends(get_db), _user: User = Depends(require_entity_role(Role.VIEWER))
    ):
        return db.query(model).filter(model.legal_entity_id == legal_entity_id).order_by(model.name).all()

    @router.post("", response_model=DimensionOut, status_code=status.HTTP_201_CREATED)
    def create_item(
        legal_entity_id: int,
        payload: DimensionCreate,
        db: Session = Depends(get_db),
        _user: User = Depends(require_entity_role(Role.ADMIN)),
    ):
        item = model(legal_entity_id=legal_entity_id, **payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @router.patch("/{item_id}", response_model=DimensionOut)
    def update_item(
        legal_entity_id: int,
        item_id: int,
        payload: DimensionUpdate,
        db: Session = Depends(get_db),
        _user: User = Depends(require_entity_role(Role.ADMIN)),
    ):
        item = db.query(model).filter(model.id == item_id, model.legal_entity_id == legal_entity_id).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    return router


cost_center_router = build_dimension_router(CostCenter, "cost-centers", "cost-centers")
counterparty_router = build_dimension_router(Counterparty, "counterparties", "counterparties")
project_router = build_dimension_router(Project, "projects", "projects")
