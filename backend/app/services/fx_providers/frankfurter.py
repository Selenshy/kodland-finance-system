from datetime import date, timedelta

import httpx

from app.services.fx_providers.base import FxRateProvider

FRANKFURTER_URL = "https://api.frankfurter.app/{date}"


class FrankfurterProvider(FxRateProvider):
    """ECB-based historical rates (api.frankfurter.app), no API key.
    Does not cover RUB or very old (pre-1999) dates."""

    name = "frankfurter"

    def get_rate(self, rate_date: date, currency_from: str, currency_to: str) -> float | None:
        if currency_from == currency_to:
            return 1.0
        if "RUB" in (currency_from, currency_to):
            return None

        for offset in range(0, 5):
            day = rate_date - timedelta(days=offset)
            try:
                resp = httpx.get(
                    FRANKFURTER_URL.format(date=day.isoformat()),
                    params={"from": currency_from, "to": currency_to},
                    timeout=10,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                rate = data.get("rates", {}).get(currency_to)
                if rate:
                    return float(rate)
            except httpx.HTTPError:
                continue
        return None
