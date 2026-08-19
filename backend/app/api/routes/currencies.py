from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_global_role
from app.models.currency import Currency, FxRate
from app.models.enums import Role
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.currency import CurrencyCreate, CurrencyOut, FxRateOut, FxRateUpsert
from app.services import fx_service

router = APIRouter(prefix="/api", tags=["currencies"])


@router.get("/currencies", response_model=list[CurrencyOut])
def list_currencies(db: Session = Depends(get_db)):
    return db.query(Currency).order_by(Currency.code).all()


@router.post("/currencies", response_model=CurrencyOut, status_code=status.HTTP_201_CREATED)
def create_currency(
    payload: CurrencyCreate, db: Session = Depends(get_db), _admin: User = Depends(require_global_role(Role.ADMIN))
):
    if db.get(Currency, payload.code):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Currency already exists")
    currency = Currency(code=payload.code.upper(), name=payload.name)
    db.add(currency)
    db.commit()
    db.refresh(currency)
    return currency


@router.get("/fx-rates", response_model=list[FxRateOut])
def list_fx_rates(
    currency_from: str | None = None,
    currency_to: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_global_role(Role.VIEWER)),
):
    q = db.query(FxRate)
    if currency_from:
        q = q.filter(FxRate.currency_from == currency_from.upper())
    if currency_to:
        q = q.filter(FxRate.currency_to == currency_to.upper())
    if date_from:
        q = q.filter(FxRate.rate_date >= date_from)
    if date_to:
        q = q.filter(FxRate.rate_date <= date_to)
    return q.order_by(FxRate.rate_date.desc()).limit(500).all()


@router.put("/fx-rates", response_model=FxRateOut)
def upsert_fx_rate(
    payload: FxRateUpsert, db: Session = Depends(get_db), admin: User = Depends(require_global_role(Role.ADMIN))
):
    """Manual admin correction of a rate, e.g. when no provider covers a pair/date."""
    existing = (
        db.query(FxRate)
        .filter(
            FxRate.rate_date == payload.rate_date,
            FxRate.currency_from == payload.currency_from.upper(),
            FxRate.currency_to == payload.currency_to.upper(),
        )
        .first()
    )
    if existing:
        existing.rate = payload.rate
        existing.source = "manual"
        rate_row = existing
    else:
        rate_row = FxRate(
            rate_date=payload.rate_date,
            currency_from=payload.currency_from.upper(),
            currency_to=payload.currency_to.upper(),
            rate=payload.rate,
            source="manual",
        )
        db.add(rate_row)
    db.commit()
    db.refresh(rate_row)
    return rate_row


def _check_cron_secret(x_cron_secret: str | None, authorization: str | None) -> None:
    """Accepts either a custom X-Cron-Secret header (manual/admin calls)
    or Vercel Cron's own `Authorization: Bearer <CRON_SECRET>` convention
    (Vercel Cron Jobs only issue GET requests and attach that header
    automatically when a CRON_SECRET env var is configured)."""
    settings = get_settings()
    if x_cron_secret == settings.fx_cron_secret:
        return
    if authorization == f"Bearer {settings.fx_cron_secret}":
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")


@router.api_route("/fx-rates/refresh", methods=["GET", "POST"])
def refresh_daily_rates(
    x_cron_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Pre-fetch today's rates for every functional currency <-> USD pair
    currently in use, so intraday postings don't each pay the provider
    round-trip cost. Called once a day by a Vercel Cron Job (GET) or
    manually by an admin (POST)."""
    _check_cron_secret(x_cron_secret, authorization)

    today = date.today()
    currencies = {c for (c,) in db.query(LegalEntity.functional_currency).distinct()}
    currencies.add("USD")
    fetched = []
    failed = []
    for ccy in currencies:
        if ccy == "USD":
            continue
        for pair in ((ccy, "USD"), ("USD", ccy)):
            try:
                rate = fx_service.get_rate(db, today, *pair)
                fetched.append({"from": pair[0], "to": pair[1], "rate": rate})
            except ValueError:
                failed.append({"from": pair[0], "to": pair[1]})
    db.commit()
    return {"date": today.isoformat(), "fetched": fetched, "failed": failed}
