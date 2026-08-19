# Kodland Finance System

Multi-entity, multi-currency accounting system: primary journal entries across
several legal entities in one account, with automatic P&L / Cash Flow (direct
method) / Balance Sheet reporting on IFRS-adjacent principles (IAS 21 FX
translation), currency toggle (local ↔ USD), and Excel/PDF export.

## Stack

- **Backend**: Python / FastAPI / SQLAlchemy 2.0 / Alembic, deployed as a
  single Vercel Python serverless function (`api/index.py` → `backend/app`).
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind, TanStack Query
  for data fetching, TanStack Table primitives for the journal grid.
- **Database**: PostgreSQL on Supabase (pooled/transaction-mode connection
  string, required for serverless — see below).
- **FX rates**: pluggable providers — [CBR](https://www.cbr.ru) for RUB
  pairs, [Frankfurter](https://www.frankfurter.dev) (ECB) for most other
  historical pairs, [open.er-api.com](https://www.exchangerate-api.com/) as a
  latest-only last resort. All keyless. Rates are cached in `fx_rates` and
  editable by an admin.

## Repository layout

```
backend/          FastAPI app, Alembic migrations, seed script, pytest suite
  app/
    models/        SQLAlchemy models
    schemas/        Pydantic request/response models
    api/routes/     REST endpoints
    services/       FX providers, journal posting, report engine, import wizard, exports
  alembic/          Migrations (run against the Supabase Postgres instance)
  scripts/seed.py   Demo data: 3 legal entities, 3 currencies, ~60 journal entries
  tests/            pytest, in-memory SQLite — never touches the real database
api/index.py       Vercel Python function entrypoint (imports backend/app/main:app)
requirements.txt   Points Vercel's Python builder at backend/requirements.txt
src/               Next.js app (App Router), at the repo root so Vercel's
                   zero-config Next.js detection picks it up directly
vercel.json        Function config + daily FX-refresh cron job
docker-compose.yml Local dev only: Postgres + backend container
```

The frontend lives at the repo root (not `/frontend`) and the API under
`/api` on purpose: this is the zero-config layout Vercel expects for a
Next.js app with Python serverless functions in the same project, so no
custom "Root Directory" setting is needed in the Vercel dashboard.

## Local development

### Backend (Docker Compose)

```bash
docker compose up --build
```

This starts a local Postgres and the FastAPI backend on `:8000` from
scratch: migrations and the demo-data seed both run automatically on
container start (`scripts/seed.py` is idempotent — it's a no-op on later
restarts once the demo tenant already exists).

### Backend (without Docker)

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env     # point DATABASE_URL at your Postgres (local or Supabase)
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

Run tests (pure SQLite in-memory, no external DB needed):

```bash
cd backend && pytest
```

### Frontend

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run dev
```

Open `http://localhost:3000` and sign in with one of the seeded demo users
(see "Demo data" below).

## Demo data

`scripts/seed.py` creates one tenant account ("Kodland Demo") with:

- **3 legal entities**, one per functional currency: Kodland LLC (RUB),
  Kodland Games Inc (USD), Kodland Europe s.r.o. (EUR) — each with its own
  17-account chart of accounts and ~20 journal entries spanning Jan–Mar 2025.
- Opening balances as of **2025-01-01** for each entity (cash + share capital).
- **3 users**, one per role:
  - `admin@demo.kodland-finance.app` / `Admin12345!`
  - `accountant@demo.kodland-finance.app` / `Accountant12345!`
  - `viewer@demo.kodland-finance.app` / `Viewer12345!`

The seed script fetches real historical FX rates on first run (live calls to
CBR/Frankfurter), so it needs network access; it's idempotent — re-running it
after the demo account already exists is a no-op.

## Deployment (Vercel + Supabase)

The repo is connected to Vercel for auto-deploy on every push to `main`
(production URL) and on every PR/branch (preview URL).

**Environment variables to set in the Vercel project** (Project Settings →
Environment Variables):

| Variable | Value |
|---|---|
| `DATABASE_URL` | Supabase **transaction pooler** connection string, `postgresql+psycopg://...:6543/postgres` — must use the pooler (port 6543), not the direct connection, or concurrent serverless invocations will exhaust Postgres connections |
| `JWT_SECRET` | a long random secret (rotate the local dev value) |
| `FX_CRON_SECRET` | a long random secret; also set it as the `CRON_SECRET` env var so Vercel's Cron Jobs authenticate automatically via `Authorization: Bearer <value>` |
| `CORS_ORIGINS` | your production domain(s), comma-separated (or `*` while iterating) |

Migrations do not run automatically on Vercel (serverless functions have no
persistent process to run them from). After a schema change, apply migrations
from a machine with `DATABASE_URL` pointed at Supabase:

```bash
cd backend && alembic upgrade head
```

### Known deployment constraints (see also CLAUDE.md §12)

- Vercel functions time out (default ~10s on Hobby, up to 60s configured in
  `vercel.json`) — the import wizard commits are synchronous per request;
  very large registers (thousands of rows) should be split into smaller
  files until batching is added.
- PDF export uses **reportlab** (not weasyprint) specifically because
  weasyprint's system dependencies (Pango/Cairo) don't run in Vercel's
  serverless environment.
- FX rate refresh runs via a Vercel Cron Job (`vercel.json` → `crons`,
  `GET /api/fx-rates/refresh` once daily) rather than an in-process
  scheduler, since serverless functions don't keep a background process alive.
- Functions are stateless with no persistent disk: the import wizard's
  upload → mapping → validate → commit steps stage the parsed file as JSON
  on the `import_batches` row itself (cleared on commit) rather than on
  local disk between requests.

## Roles

| Role | Permissions |
|---|---|
| **admin** | legal entities, chart of accounts, users, reference data, FX rate corrections |
| **accountant** | enter/edit journal entries (incl. bulk edit), upload registers |
| **viewer** | read-only across reports and the journal |

A role is set globally per user and can optionally be restricted to a subset
of legal entities (`user_entity_roles`); with no restriction rows, the global
role applies account-wide.

## Roadmap (Phase 2 — not implemented yet)

- Entry approval workflow (draft → reviewed → approved statuses) and locking
  closed periods.
- Full consolidation with elimination of intercompany transactions, mutual
  balances, and unrealized profit (the current group report is a simple sum
  across entities, with no elimination, per the MVP scope).
