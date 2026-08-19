import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.currency import Currency
from app.models.enums import Role
from app.models.legal_entity import LegalEntity
from app.models.tenant import TenantAccount, User

# In-memory SQLite for fast, isolated tests -- never touches the real
# Supabase database. A single StaticPool connection is shared so that
# in-memory tables survive across the session/engine boundary.
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_basic(db_session):
    """A tenant with one legal entity (USD) and one admin/accountant/viewer user each."""
    for code, name in (("USD", "US Dollar"), ("RUB", "Russian Ruble"), ("EUR", "Euro")):
        db_session.add(Currency(code=code, name=name))

    tenant = TenantAccount(name="Test Tenant")
    db_session.add(tenant)
    db_session.flush()

    entity = LegalEntity(account_id=tenant.id, name="Test Co", country="US", functional_currency="USD")
    db_session.add(entity)
    db_session.flush()

    users = {}
    for role in (Role.ADMIN, Role.ACCOUNTANT, Role.VIEWER):
        user = User(
            account_id=tenant.id,
            email=f"{role.value}@test.example",
            hashed_password=hash_password("Password123!"),
            full_name=role.value,
            global_role=role,
        )
        db_session.add(user)
        users[role] = user
    db_session.flush()
    db_session.commit()

    return {"tenant": tenant, "entity": entity, "users": users}
