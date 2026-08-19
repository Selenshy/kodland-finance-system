from datetime import date

import httpx

from app.services.fx_providers.base import FxRateProvider

OPEN_ER_API_URL = "https://open.er-api.com/v6/latest/{base}"


class OpenErApiProvider(FxRateProvider):
    """Latest-only rates (open.er-api.com), no API key. Used as a last
    resort fallback when the requested date has no historical data
    elsewhere -- the caller is responsible for flagging that the rate is
    a "latest" approximation rather than an as-of-date rate."""

    name = "open_er_api_latest"

    def get_rate(self, rate_date: date, currency_from: str, currency_to: str) -> float | None:
        if currency_from == currency_to:
            return 1.0
        try:
            resp = httpx.get(OPEN_ER_API_URL.format(base=currency_from), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("rates", {}).get(currency_to)
            return float(rate) if rate else None
        except httpx.HTTPError:
            return None
