from pydantic import BaseModel


class LegalEntityBase(BaseModel):
    name: str
    country: str = ""
    functional_currency: str


class LegalEntityCreate(LegalEntityBase):
    copy_coa_from_entity_id: int | None = None


class LegalEntityUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    functional_currency: str | None = None


class LegalEntityOut(LegalEntityBase):
    id: int
    account_id: int

    model_config = {"from_attributes": True}
