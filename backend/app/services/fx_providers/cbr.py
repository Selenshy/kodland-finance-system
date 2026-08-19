import xml.etree.ElementTree as ET
from datetime import date, timedelta

import httpx

from app.services.fx_providers.base import FxRateProvider

CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


class CbrProvider(FxRateProvider):
    """Bank of Russia daily rates, RUB-denominated. Authoritative for any
    pair involving RUB; returns None otherwise."""

    name = "cbr"

    def get_rate(self, rate_date: date, currency_from: str, currency_to: str) -> float | None:
        if currency_from == currency_to:
            return 1.0
        if "RUB" not in (currency_from, currency_to):
            return None

        other = currency_to if currency_from == "RUB" else currency_from
        if other == "RUB":
            return 1.0

        rub_per_unit = self._fetch_rub_per_unit(rate_date, other)
        if rub_per_unit is None:
            return None

        if currency_from == "RUB":
            return 1.0 / rub_per_unit
        return rub_per_unit

    def _fetch_rub_per_unit(self, rate_date: date, currency_code: str) -> float | None:
        # CBR does not publish on weekends/holidays; walk back a few days.
        for offset in range(0, 7):
            day = rate_date - timedelta(days=offset)
            try:
                resp = httpx.get(CBR_URL, params={"date_req": day.strftime("%d/%m/%Y")}, timeout=10)
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
            except (httpx.HTTPError, ET.ParseError):
                continue
            for valute in root.findall("Valute"):
                char_code = valute.findtext("CharCode")
                if char_code != currency_code:
                    continue
                nominal = float(valute.findtext("Nominal", "1"))
                value = float(valute.findtext("Value", "0").replace(",", "."))
                if value <= 0:
                    return None
                return value / nominal
        return None
