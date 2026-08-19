from datetime import date

from pydantic import BaseModel, model_validator

from app.models.enums import EntryDirection


class JournalLineCreate(BaseModel):
    account_id: int
    direction: EntryDirection
    transaction_currency: str
    transaction_amount: float
    cost_center_id: int | None = None
    counterparty_id: int | None = None
    project_id: int | None = None
    memo: str = ""


class JournalLineOut(BaseModel):
    id: int
    account_id: int
    direction: EntryDirection
    transaction_currency: str
    transaction_amount: float
    local_currency_amount: float
    usd_amount: float
    fx_rate_to_local: float
    fx_rate_to_usd: float
    cost_center_id: int | None = None
    counterparty_id: int | None = None
    project_id: int | None = None
    memo: str = ""

    model_config = {"from_attributes": True}


class JournalEntryCreate(BaseModel):
    legal_entity_id: int
    entry_date: date
    description: str = ""
    lines: list[JournalLineCreate]

    @model_validator(mode="after")
    def _at_least_two_lines(self):
        if len(self.lines) < 2:
            raise ValueError("A journal entry needs at least two lines (debit and credit)")
        return self


class JournalEntryUpdate(BaseModel):
    entry_date: date | None = None
    description: str | None = None
    lines: list[JournalLineCreate] | None = None


class JournalEntryOut(BaseModel):
    id: int
    legal_entity_id: int
    entry_date: date
    description: str
    import_batch_id: int | None = None
    lines: list[JournalLineOut]

    model_config = {"from_attributes": True}


class BulkEditRequest(BaseModel):
    entry_ids: list[int]
    set_counterparty_id: int | None = None
    set_cost_center_id: int | None = None
    set_project_id: int | None = None
    set_account_id: int | None = None


class BulkEditResult(BaseModel):
    updated_lines: int
