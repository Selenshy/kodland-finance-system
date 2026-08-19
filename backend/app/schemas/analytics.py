from pydantic import BaseModel


class DimensionBase(BaseModel):
    name: str
    is_active: bool = True


class DimensionCreate(DimensionBase):
    pass


class DimensionUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class DimensionOut(DimensionBase):
    id: int
    legal_entity_id: int

    model_config = {"from_attributes": True}
