from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.currency import FxRate
from app.services.fx_providers import get_providers


def get_rate(db: Session, rate_date: date, currency_from: str, currency_to: str) -> float:
    """Rate such that amount_in_to = amount_in_from * rate, on `rate_date`.

    Looks up `fx_rates` first (direct or inverse pair); on a cache miss it
    queries providers in order and persists the result for reuse. Raises
    if no provider can supply a rate, so callers can surface a clear error
    instead of silently posting a wrong amount.
    """
    if currency_from == currency_to:
        return 1.0

    direct = (
        db.query(FxRate)
        .filter(
            and_(
                FxRate.rate_date == rate_date,
                FxRate.currency_from == currency_from,
                FxRate.currency_to == currency_to,
            )
        )
        .first()
    )
    if direct:
        return float(direct.rate)

    inverse = (
        db.query(FxRate)
        .filter(
            and_(
                FxRate.rate_date == rate_date,
                FxRate.currency_from == currency_to,
                FxRate.currency_to == currency_from,
            )
        )
        .first()
    )
    if inverse and float(inverse.rate) != 0:
        return 1.0 / float(inverse.rate)

    for provider in get_providers():
        rate = provider.get_rate(rate_date, currency_from, currency_to)
        if rate is not None:
            db.add(
                FxRate(
                    rate_date=rate_date,
                    currency_from=currency_from,
                    currency_to=currency_to,
                    rate=rate,
                    source=provider.name,
                )
            )
            db.flush()
            return rate

    raise ValueError(
        f"No FX rate available for {currency_from}->{currency_to} on {rate_date}. "
        "An administrator can enter it manually in FX Rates."
    )


def get_closing_rate(db: Session, period_end: date, currency_from: str, currency_to: str) -> float:
    """IAS 21 closing rate for balance-sheet items: the latest known rate
    on or before the end of the reporting period."""
    if currency_from == currency_to:
        return 1.0

    candidate = (
        db.query(FxRate)
        .filter(
            and_(
                FxRate.currency_from == currency_from,
                FxRate.currency_to == currency_to,
                FxRate.rate_date <= period_end,
            )
        )
        .order_by(FxRate.rate_date.desc())
        .first()
    )
    if candidate:
        return float(candidate.rate)

    inverse = (
        db.query(FxRate)
        .filter(
            and_(
                FxRate.currency_from == currency_to,
                FxRate.currency_to == currency_from,
                FxRate.rate_date <= period_end,
            )
        )
        .order_by(FxRate.rate_date.desc())
        .first()
    )
    if inverse and float(inverse.rate) != 0:
        return 1.0 / float(inverse.rate)

    # No cached rate on/before period_end yet: fetch (and cache) the rate
    # for period_end itself, which providers resolve to the latest
    # available trading day at or before it.
    return get_rate(db, period_end, currency_from, currency_to)
