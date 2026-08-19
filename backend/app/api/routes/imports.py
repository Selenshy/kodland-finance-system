from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_entity_role
from app.models.enums import Role
from app.models.import_batch import ImportBatch, ImportMappingTemplate
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.imports import (
    ImportCommitRequest,
    ImportCommitResult,
    ImportMappingTemplateCreate,
    ImportMappingTemplateOut,
    ImportUploadResult,
    ImportValidateRequest,
    ImportValidateResult,
)
from app.models.mixins import utcnow
from app.services import import_service

router = APIRouter(prefix="/api/legal-entities/{legal_entity_id}/imports", tags=["imports"])


def _get_entity(db: Session, legal_entity_id: int, account_id: int) -> LegalEntity:
    entity = db.query(LegalEntity).filter(
        LegalEntity.id == legal_entity_id, LegalEntity.account_id == account_id
    ).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal entity not found")
    return entity


def _get_batch(db: Session, legal_entity_id: int, upload_token: str) -> ImportBatch:
    try:
        batch_id = int(upload_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload_token")
    batch = db.query(ImportBatch).filter(
        ImportBatch.id == batch_id, ImportBatch.legal_entity_id == legal_entity_id
    ).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found or expired")
    return batch


@router.post("/upload", response_model=ImportUploadResult)
async def upload_file(
    legal_entity_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    _get_entity(db, legal_entity_id, user.account_id)
    content = await file.read()
    try:
        columns, rows = import_service.parse_file(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse file: {exc}") from exc

    batch = ImportBatch(
        legal_entity_id=legal_entity_id,
        file_name=file.filename,
        status="draft",
        row_count=len(rows),
        created_by_user_id=user.id,
        staged_columns=columns,
        staged_rows=rows,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return ImportUploadResult(
        upload_token=str(batch.id),
        columns=columns,
        preview_rows=rows[: import_service.PREVIEW_ROW_LIMIT],
        total_rows=len(rows),
    )


@router.post("/validate", response_model=ImportValidateResult)
def validate_upload(
    legal_entity_id: int,
    payload: ImportValidateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    entity = _get_entity(db, legal_entity_id, user.account_id)
    batch = _get_batch(db, legal_entity_id, payload.upload_token)

    _resolved, errors = import_service.resolve_and_validate(db, entity, payload.column_mapping, batch.staged_rows or [])
    valid_rows = len(batch.staged_rows or []) - len(errors)

    return ImportValidateResult(
        valid_rows=max(valid_rows, 0),
        invalid_rows=len(errors),
        errors=errors[:200],
        can_commit=valid_rows > 0,
    )


@router.post("/commit", response_model=ImportCommitResult)
def commit_upload(
    legal_entity_id: int,
    payload: ImportCommitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    entity = _get_entity(db, legal_entity_id, user.account_id)
    batch = _get_batch(db, legal_entity_id, payload.upload_token)
    if batch.status == "committed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This import batch was already committed")

    resolved, errors = import_service.resolve_and_validate(db, entity, payload.column_mapping, batch.staged_rows or [])
    entries_created, lines_created = import_service.commit_rows(db, entity, resolved, errors, batch, user.id)

    batch.file_name = payload.file_name or batch.file_name
    batch.status = "committed"
    batch.error_count = len(errors)
    batch.committed_at = utcnow()
    batch.staged_rows = None
    batch.staged_columns = None
    if payload.mapping_template_id:
        batch.mapping_template_id = payload.mapping_template_id

    db.commit()

    return ImportCommitResult(
        import_batch_id=batch.id,
        entries_created=entries_created,
        lines_created=lines_created,
        error_count=len(errors),
        errors=errors[:200],
    )


@router.get("/mapping-templates", response_model=list[ImportMappingTemplateOut])
def list_mapping_templates(
    legal_entity_id: int, db: Session = Depends(get_db), user: User = Depends(require_entity_role(Role.VIEWER))
):
    return (
        db.query(ImportMappingTemplate)
        .filter(
            ImportMappingTemplate.account_id == user.account_id,
            (ImportMappingTemplate.legal_entity_id == legal_entity_id) | (ImportMappingTemplate.legal_entity_id.is_(None)),
        )
        .order_by(ImportMappingTemplate.name)
        .all()
    )


@router.post("/mapping-templates", response_model=ImportMappingTemplateOut, status_code=status.HTTP_201_CREATED)
def create_mapping_template(
    legal_entity_id: int,
    payload: ImportMappingTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ACCOUNTANT)),
):
    template = ImportMappingTemplate(account_id=user.account_id, **payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
