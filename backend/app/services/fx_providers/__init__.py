from app.services.fx_providers.base import FxRateProvider
from app.services.fx_providers.cbr import CbrProvider
from app.services.fx_providers.frankfurter import FrankfurterProvider
from app.services.fx_providers.open_er_api import OpenErApiProvider


def get_providers() -> list[FxRateProvider]:
    """Providers tried in order, most-authoritative first.

    CBR is authoritative for RUB pairs; Frankfurter (ECB) covers most
    other historical pairs; open.er-api.com is a latest-only, best-effort
    fallback for anything else (e.g. very old dates or exotic currencies).
    """
    return [CbrProvider(), FrankfurterProvider(), OpenErApiProvider()]
