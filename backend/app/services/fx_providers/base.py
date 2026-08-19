from abc import ABC, abstractmethod
from datetime import date


class FxRateProvider(ABC):
    """A pluggable source of currency->currency rates for a given date.

    `rate` is such that amount_in_to = amount_in_from * rate.
    """

    name: str

    @abstractmethod
    def get_rate(self, rate_date: date, currency_from: str, currency_to: str) -> float | None:
        """Return the rate, or None if this provider cannot supply it."""
        raise NotImplementedError
