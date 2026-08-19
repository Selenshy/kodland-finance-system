from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Supabase's pooler runs in pgbouncer transaction mode, which does not
# support server-side prepared statements. psycopg3 must not try to
# prepare statements on that connection, otherwise queries fail
# intermittently once the pool reuses a physical connection for a
# different session.
_connect_args = {"prepare_threshold": None} if "psycopg" in settings.database_url else {}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
