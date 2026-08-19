from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import Role
from app.models.tenant import User, UserEntityRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_ROLE_RANK = {Role.VIEWER: 0, Role.ACCOUNTANT: 1, Role.ADMIN: 2}


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_error
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise credentials_error
    return user


def require_global_role(minimum: Role):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if _ROLE_RANK[user.global_role] < _ROLE_RANK[minimum]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker


def role_for_entity(user: User, legal_entity_id: int, db: Session) -> Role | None:
    """Effective role of `user` on a given legal entity, or None if no access.

    If the user has no per-entity role rows, the global role applies to
    every legal entity in their account. If rows exist, access is
    restricted to exactly the legal entities listed.
    """
    overrides = db.query(UserEntityRole).filter(UserEntityRole.user_id == user.id).all()
    if not overrides:
        return user.global_role
    for override in overrides:
        if override.legal_entity_id == legal_entity_id:
            return override.role
    return None


def require_entity_role(minimum: Role):
    def _checker(
        legal_entity_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        role = role_for_entity(user, legal_entity_id, db)
        if role is None or _ROLE_RANK[role] < _ROLE_RANK[minimum]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker


def accessible_entity_ids(user: User, db: Session) -> list[int] | None:
    """Legal entity ids `user` may access, or None meaning "all in account"."""
    overrides = db.query(UserEntityRole).filter(UserEntityRole.user_id == user.id).all()
    if not overrides:
        return None
    return [o.legal_entity_id for o in overrides]
