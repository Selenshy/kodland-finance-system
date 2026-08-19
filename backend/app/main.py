from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, audit, auth, coa, currencies, imports, journal, legal_entities, opening_balances, reports, users
from app.core.config import get_settings

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
    return {"status": "ok"}
