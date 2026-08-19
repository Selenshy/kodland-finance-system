from datetime import date

from pydantic import BaseModel


class ReportLineOut(BaseModel):
    code: str
    label: str
    amount: float
    is_subtotal: bool = False


class ReportSectionOut(BaseModel):
    title: str
    lines: list[ReportLineOut]
    total: float


class ReportOut(BaseModel):
    report_type: str
    legal_entity_ids: list[int]
    period_start: date
    period_end: date
    currency: str
    sections: list[ReportSectionOut]
    check_ok: bool | None = None
