from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AccountType, CfCategory
from app.models.mixins import TimestampMixin


class ChartOfAccount(Base, TimestampMixin):
    """One account in a legal entity's chart of accounts.

    `report_line` is a free-form code grouping accounts within a report
    section (e.g. "REVENUE", "COGS", "CASH", "AR", "AP", "PPE",
    "SHARE_CAPITAL"); the report engine groups and labels by this code.
    `cf_category`/`cf_line` classify this account when it is the
    *counterpart* of a cash movement, for the direct-method cash flow
    statement (see app/services/report_engine.py).
    """

    __tablename__ = "chart_of_accounts"
    __table_args__ = (
        UniqueConstraint("legal_entity_id", "code", name="uq_coa_entity_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_entity_id: Mapped[int] = mapped_column(
        ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type_enum"), nullable=False)
    report_line: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_cash: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cf_category: Mapped[CfCategory | None] = mapped_column(
        Enum(CfCategory, name="cf_category_enum"), nullable=True
    )
    cf_line: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_postable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    legal_entity: Mapped["LegalEntity"] = relationship(back_populates="accounts")
    parent: Mapped["ChartOfAccount | None"] = relationship(remote_side="ChartOfAccount.id")
