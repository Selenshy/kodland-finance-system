from pydantic import BaseModel

from app.models.enums import AccountType, CfCategory


class ChartOfAccountBase(BaseModel):
    code: str
    name: str
    parent_id: int | None = None
    account_type: AccountType
    report_line: str = ""
    is_cash: bool = False
    cf_category: CfCategory | None = None
    cf_line: str = ""
    is_postable: bool = True
    is_active: bool = True


class ChartOfAccountCreate(ChartOfAccountBase):
    pass


class ChartOfAccountUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    parent_id: int | None = None
    account_type: AccountType | None = None
    report_line: str | None = None
    is_cash: bool | None = None
    cf_category: CfCategory | None = None
    cf_line: str | None = None
    is_postable: bool | None = None
    is_active: bool | None = None


class ChartOfAccountOut(ChartOfAccountBase):
    id: int
    legal_entity_id: int

    model_config = {"from_attributes": True}


class CoaImportRow(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    account_type: AccountType
    report_line: str = ""
    is_cash: bool = False


class CoaImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]
