from datetime import date

from pydantic import BaseModel


class OpeningBalanceIn(BaseModel):
    account_id: int
    as_of_date: date
    local_currency_amount: float
    usd_amount: float


class OpeningBalanceOut(OpeningBalanceIn):
    id: int
    legal_entity_id: int

    model_config = {"from_attributes": True}
