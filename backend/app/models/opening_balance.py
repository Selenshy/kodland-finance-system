from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class OpeningBalance(Base, TimestampMixin):
    """Manually entered starting balance per account, as the point where
    ledger-based accounting begins for a legal entity (e.g. 2025-01-01).
    Stored directly in local currency and USD (no transaction currency,
    since these are not real transactions).
    """

    __tablename__ = "opening_balances"
    __table_args__ = (
        UniqueConstraint("legal_entity_id", "account_id", "as_of_date", name="uq_opening_balance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    local_currency_amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    usd_amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
