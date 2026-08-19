from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    field: str
    old_value: str | None
    new_value: str | None
    changed_by_user_id: int | None
    changed_at: datetime

    model_config = {"from_attributes": True}
