from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class FxRate(Base, TimestampMixin):
    """Rate such that amount_in_to = amount_in_from * rate."""

    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("rate_date", "currency_from", "currency_to", name="uq_fx_rate_day_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency_from: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    currency_to: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
