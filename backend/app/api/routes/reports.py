from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import accessible_entity_ids, get_current_user
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.reports import ReportOut
from app.services import report_engine, report_export

router = APIRouter(prefix="/api/reports", tags=["reports"])

ENGINES = {"pl": report_engine.compute_pl, "cf": report_engine.compute_cf}


def _resolve_entities(db: Session, user: User, legal_entity_ids: list[int]) -> list[int]:
    if not legal_entity_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="legal_entity_ids is required")
    owned = {
        e.id for e in db.query(LegalEntity).filter(LegalEntity.account_id == user.account_id).all()
    }
    allowed = accessible_entity_ids(user, db)
    for eid in legal_entity_ids:
        if eid not in owned or (allowed is not None and eid not in allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to legal entity {eid}")
    return legal_entity_ids


def _build(
    db: Session,
    user: User,
    report_type: str,
    legal_entity_ids: list[int],
    period_start: date,
    period_end: date,
    currency: str,
) -> ReportOut:
    entities = _resolve_entities(db, user, legal_entity_ids)
    currency = currency.upper()
    if report_type == "balance":
        return report_engine.compute_balance(db, entities, period_end, currency)
    return ENGINES[report_type](db, entities, period_start, period_end, currency)


@router.get("/{report_type}", response_model=ReportOut)
def get_report(
    report_type: str,
    legal_entity_ids: list[int] = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    currency: str = Query("USD"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if report_type not in ("pl", "cf", "balance"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown report type")
    return _build(db, user, report_type, legal_entity_ids, period_start, period_end, currency)


@router.get("/{report_type}/export/excel")
def export_excel(
    report_type: str,
    legal_entity_ids: list[int] = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    currency: str = Query("USD"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if report_type not in ("pl", "cf", "balance"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown report type")
    report = _build(db, user, report_type, legal_entity_ids, period_start, period_end, currency)
    content = report_export.to_excel(report)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_type}_{period_start}_{period_end}.xlsx"'},
    )


@router.get("/{report_type}/export/pdf")
def export_pdf(
    report_type: str,
    legal_entity_ids: list[int] = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    currency: str = Query("USD"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if report_type not in ("pl", "cf", "balance"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown report type")
    report = _build(db, user, report_type, legal_entity_ids, period_start, period_end, currency)
    content = report_export.to_pdf(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_type}_{period_start}_{period_end}.pdf"'},
    )
