from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import Role
from app.models.mixins import TimestampMixin


class TenantAccount(Base, TimestampMixin):
    """The top-level tenant: one customer account holding several legal entities."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    legal_entities: Mapped[list["LegalEntity"]] = relationship(back_populates="tenant_account")
    users: Mapped[list["User"]] = relationship(back_populates="tenant_account")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    global_role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), nullable=False)

    tenant_account: Mapped["TenantAccount"] = relationship(back_populates="users")
    entity_roles: Mapped[list["UserEntityRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserEntityRole(Base, TimestampMixin):
    """Optional per-legal-entity role override / access restriction.

    If a user has no rows here, `User.global_role` applies to every legal
    entity in the account. If rows exist, access is restricted to exactly
    the legal entities listed, using that row's role.
    """

    __tablename__ = "user_entity_roles"
    __table_args__ = (UniqueConstraint("user_id", "legal_entity_id", name="uq_user_entity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    legal_entity_id: Mapped[int] = mapped_column(
        ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="entity_roles")
    legal_entity: Mapped["LegalEntity"] = relationship(back_populates="user_roles")
