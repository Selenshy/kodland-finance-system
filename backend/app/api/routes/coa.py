from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_entity_role
from app.models.coa import ChartOfAccount
from app.models.enums import Role
from app.models.legal_entity import LegalEntity
from app.models.tenant import User
from app.schemas.coa import ChartOfAccountCreate, ChartOfAccountOut, ChartOfAccountUpdate, CoaImportResult
from app.services import audit_service
from app.services.import_service import parse_file

router = APIRouter(prefix="/api/legal-entities/{legal_entity_id}/accounts", tags=["chart-of-accounts"])


def _get_entity(db: Session, legal_entity_id: int, account_id: int) -> LegalEntity:
    entity = db.query(LegalEntity).filter(
        LegalEntity.id == legal_entity_id, LegalEntity.account_id == account_id
    ).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal entity not found")
    return entity


@router.get("", response_model=list[ChartOfAccountOut])
def list_accounts(
    legal_entity_id: int, db: Session = Depends(get_db), user: User = Depends(require_entity_role(Role.VIEWER))
):
    _get_entity(db, legal_entity_id, user.account_id)
    return (
        db.query(ChartOfAccount)
        .filter(ChartOfAccount.legal_entity_id == legal_entity_id)
        .order_by(ChartOfAccount.code)
        .all()
    )


@router.post("", response_model=ChartOfAccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    legal_entity_id: int,
    payload: ChartOfAccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ADMIN)),
):
    _get_entity(db, legal_entity_id, user.account_id)
    if db.query(ChartOfAccount).filter(
        ChartOfAccount.legal_entity_id == legal_entity_id, ChartOfAccount.code == payload.code
    ).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Account code '{payload.code}' already exists")

    account = ChartOfAccount(legal_entity_id=legal_entity_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=ChartOfAccountOut)
def update_account(
    legal_entity_id: int,
    account_id: int,
    payload: ChartOfAccountUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ADMIN)),
):
    _get_entity(db, legal_entity_id, user.account_id)
    account = db.query(ChartOfAccount).filter(
        ChartOfAccount.id == account_id, ChartOfAccount.legal_entity_id == legal_entity_id
    ).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        old_value = getattr(account, field)
        if old_value != value:
            audit_service.log_change(db, "chart_of_accounts", account.id, field, old_value, value, user.id)
            setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.post("/import", response_model=CoaImportResult)
async def import_accounts(
    legal_entity_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_entity_role(Role.ADMIN)),
):
    """Import/upsert a chart of accounts from CSV/Excel. Expected columns
    (case-insensitive): code, name, parent_code, account_type, report_line,
    is_cash. Existing codes are updated in place; unknown ones are created,
    preserving the codes/hierarchy from the source file (e.g. a 1C export).
    """
    _get_entity(db, legal_entity_id, user.account_id)
    content = await file.read()
    _columns, rows = parse_file(file.filename, content)

    normalized_rows = []
    errors: list[str] = []
    for i, row in enumerate(rows, start=1):
        lower_row = {str(k).strip().lower(): v for k, v in row.items()}
        code = str(lower_row.get("code") or "").strip()
        name = str(lower_row.get("name") or "").strip()
        account_type = str(lower_row.get("account_type") or "").strip().lower()
        if not code or not name or account_type not in {"asset", "liability", "equity", "income", "expense"}:
            errors.append(f"row {i}: missing code/name or invalid account_type '{account_type}'")
            continue
        normalized_rows.append(
            {
                "code": code,
                "name": name,
                "parent_code": str(lower_row.get("parent_code") or "").strip() or None,
                "account_type": account_type,
                "report_line": str(lower_row.get("report_line") or "").strip(),
                "is_cash": str(lower_row.get("is_cash") or "").strip().lower() in {"1", "true", "yes", "y"},
            }
        )

    existing = {a.code: a for a in db.query(ChartOfAccount).filter(ChartOfAccount.legal_entity_id == legal_entity_id)}
    created = 0
    updated = 0

    for r in normalized_rows:
        account = existing.get(r["code"])
        if account is None:
            account = ChartOfAccount(legal_entity_id=legal_entity_id, code=r["code"], account_type=r["account_type"])
            db.add(account)
            existing[r["code"]] = account
            created += 1
        else:
            updated += 1
        account.name = r["name"]
        account.account_type = r["account_type"]
        account.report_line = r["report_line"]
        account.is_cash = r["is_cash"]
    db.flush()

    for r in normalized_rows:
        if r["parent_code"]:
            parent = existing.get(r["parent_code"])
            if parent is None:
                errors.append(f"account '{r['code']}': parent_code '{r['parent_code']}' not found")
                continue
            existing[r["code"]].parent_id = parent.id

    db.commit()
    return CoaImportResult(created=created, updated=updated, errors=errors)
