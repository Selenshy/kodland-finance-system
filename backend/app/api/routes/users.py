from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import accessible_entity_ids, require_global_role
from app.core.security import hash_password
from app.models.enums import Role
from app.models.tenant import User, UserEntityRole
from app.schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_global_role(Role.ADMIN))):
    users = db.query(User).filter(User.account_id == _admin.account_id).all()
    out = []
    for u in users:
        item = UserOut.model_validate(u)
        item.entity_ids = accessible_entity_ids(u, db)
        out.append(item)
    return out


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_global_role(Role.ADMIN))
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        account_id=admin.account_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        global_role=payload.global_role,
    )
    db.add(user)
    db.flush()
    for entity_id in payload.entity_role_ids:
        db.add(UserEntityRole(user_id=user.id, legal_entity_id=entity_id, role=payload.global_role))
    db.commit()
    db.refresh(user)
    out = UserOut.model_validate(user)
    out.entity_ids = payload.entity_role_ids or None
    return out


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_global_role(Role.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id, User.account_id == admin.account_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.global_role is not None:
        user.global_role = payload.global_role
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    out = UserOut.model_validate(user)
    out.entity_ids = accessible_entity_ids(user, db)
    return out
