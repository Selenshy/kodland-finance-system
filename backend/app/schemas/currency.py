from datetime import date

from pydantic import BaseModel


class CurrencyOut(BaseModel):
    code: str
    name: str

    model_config = {"from_attributes": True}


class CurrencyCreate(BaseModel):
    code: str
    name: str


class FxRateOut(BaseModel):
    id: int
    rate_date: date
    currency_from: str
    currency_to: str
    rate: float
    source: str

    model_config = {"from_attributes": True}


class FxRateUpsert(BaseModel):
    rate_date: date
    currency_from: str
    currency_to: str
    rate: float
