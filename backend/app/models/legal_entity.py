from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class LegalEntity(Base, TimestampMixin):
    __tablename__ = "legal_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    functional_currency: Mapped[str] = mapped_column(ForeignKey("currencies.code"), nullable=False)

    tenant_account: Mapped["TenantAccount"] = relationship(back_populates="legal_entities")
    user_roles: Mapped[list["UserEntityRole"]] = relationship(back_populates="legal_entity")
    accounts: Mapped[list["ChartOfAccount"]] = relationship(back_populates="legal_entity")
