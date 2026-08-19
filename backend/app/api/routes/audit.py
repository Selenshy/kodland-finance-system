from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_global_role
from app.models.audit import AuditLog
from app.models.enums import Role
from app.models.tenant import User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/api/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_log(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_global_role(Role.ACCOUNTANT)),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    return q.order_by(AuditLog.changed_at.desc()).limit(limit).all()
