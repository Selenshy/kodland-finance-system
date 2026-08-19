from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EntryDirection
from app.models.mixins import TimestampMixin


class JournalEntry(Base, TimestampMixin):
    """Header for one accounting transaction (one or more journal lines)."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True
    )

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.id"
    )


class JournalLine(Base, TimestampMixin):
    """One debit or credit line, carrying all three multi-currency amounts.

    - transaction_amount: amount in `transaction_currency`, as it occurred.
    - local_currency_amount: converted to the legal entity's functional
      currency, at the FX rate on the entry date.
    - usd_amount: converted to USD, at the FX rate on the entry date.
    """

    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("chart_of_accounts.id"), nullable=False)
    cost_center_id: Mapped[int | None] = mapped_column(ForeignKey("cost_centers.id"), nullable=True)
    counterparty_id: Mapped[int | None] = mapped_column(ForeignKey("counterparties.id"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)

    direction: Mapped[EntryDirection] = mapped_column(Enum(EntryDirection, name="entry_direction_enum"), nullable=False)

    transaction_currency: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)
    transaction_amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)

    local_currency_amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    usd_amount: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    fx_rate_to_local: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    fx_rate_to_usd: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)

    memo: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["ChartOfAccount"] = relationship()
