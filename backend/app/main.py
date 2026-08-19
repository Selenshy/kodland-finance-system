from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import analytics, audit, auth, coa, currencies, imports, journal, legal_entities, opening_balances, reports, users
from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

app = FastAPI(title="Kodland Finance System API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(legal_entities.router)
app.include_router(coa.router)
app.include_router(analytics.cost_center_router)
app.include_router(analytics.counterparty_router)
app.include_router(analytics.project_router)
app.include_router(currencies.router)
app.include_router(journal.router)
app.include_router(opening_balances.router)
app.include_router(imports.router)
app.include_router(reports.router)
app.include_router(audit.router)


@app.get("/api/health")
def health():
    """Liveness only -- confirms the function booted and imports resolved,
    independent of the database. See /api/health/db for connectivity."""
    return {"status": "ok"}


@app.get("/api/health/db")
def health_db(db: Session = Depends(get_db)):
    """Confirms DATABASE_URL actually connects. Split from /api/health so
    a misconfigured DB doesn't make the whole deployment look dead, and
    so this specific failure mode (env var missing/wrong) is diagnosable
    without needing a full login attempt -- a bad connection is exactly
    what surfaces to end users as a generic 500 on every DB-backed route."""
    try:
        db.execute(text("select 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001 - deliberately broad: this endpoint's entire job is to report any connectivity failure
        return {"status": "error", "database": "unreachable", "error_type": type(exc).__name__}
