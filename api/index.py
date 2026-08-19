"""Vercel Python function entrypoint.

Vercel's Python runtime auto-detects an ASGI `app` object exported from
a file under /api and serves it directly -- no adapter needed for
FastAPI. The actual application lives in /backend (developed and tested
as a standalone project with its own venv/requirements/alembic/tests);
this file only wires it onto Vercel's expected entrypoint path, adding
/backend to sys.path so its internal `from app...` imports resolve
exactly as they do when the backend is run/tested on its own.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402
