from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_change(
    db: Session,
    entity_type: str,
    entity_id: int,
    field: str,
    old_value,
    new_value,
    changed_by_user_id: int | None,
) -> None:
    if old_value == new_value:
        return
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            field=field,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
            changed_by_user_id=changed_by_user_id,
        )
    )
