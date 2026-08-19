from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ImportMappingTemplate(Base, TimestampMixin):
    """A saved column-mapping configuration, reusable across uploads from
    the same source (e.g. "Bank X statement", "1C chart export")."""

    __tablename__ = "import_mapping_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    legal_entity_id: Mapped[int | None] = mapped_column(
        ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="journal_entries")
    column_mapping: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ImportBatch(Base, TimestampMixin):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mapping_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_mapping_templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    row_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Draft-stage staging: holds the parsed file between upload -> mapping
    # -> validate -> commit requests, since a serverless function has no
    # local disk to persist it on between invocations. Cleared on commit.
    staged_columns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    staged_rows: Mapped[list | None] = mapped_column(JSON, nullable=True)
