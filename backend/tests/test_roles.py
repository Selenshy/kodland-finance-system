from app.models.enums import Role


def _login(client, role: Role) -> str:
    resp = client.post("/api/auth/login", json={"email": f"{role.value}@test.example", "password": "Password123!"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_viewer_cannot_create_journal_entry(client, seed_basic):
    entity_id = seed_basic["entity"].id
    token = _login(client, Role.VIEWER)

    resp = client.post(
        f"/api/legal-entities/{entity_id}/journal-entries",
        headers=_auth(token),
        json={"legal_entity_id": entity_id, "entry_date": "2025-01-01", "description": "x", "lines": []},
    )
    assert resp.status_code == 403


def test_viewer_can_read_journal_entries(client, seed_basic):
    entity_id = seed_basic["entity"].id
    token = _login(client, Role.VIEWER)

    resp = client.get(f"/api/legal-entities/{entity_id}/journal-entries", headers=_auth(token))
    assert resp.status_code == 200


def test_accountant_cannot_create_legal_entity(client, seed_basic):
    token = _login(client, Role.ACCOUNTANT)

    resp = client.post(
        "/api/legal-entities",
        headers=_auth(token),
        json={"name": "New Co", "country": "US", "functional_currency": "USD"},
    )
    assert resp.status_code == 403


def test_admin_can_create_legal_entity(client, seed_basic):
    token = _login(client, Role.ADMIN)

    resp = client.post(
        "/api/legal-entities",
        headers=_auth(token),
        json={"name": "New Co", "country": "US", "functional_currency": "USD"},
    )
    assert resp.status_code == 201


def test_accountant_can_create_balanced_journal_entry(client, seed_basic, db_session):
    from app.models.coa import ChartOfAccount
    from app.models.enums import AccountType

    entity = seed_basic["entity"]
    bank = ChartOfAccount(legal_entity_id=entity.id, code="1010", name="Bank", account_type=AccountType.ASSET)
    revenue = ChartOfAccount(legal_entity_id=entity.id, code="4000", name="Revenue", account_type=AccountType.INCOME)
    db_session.add_all([bank, revenue])
    db_session.commit()

    token = _login(client, Role.ACCOUNTANT)
    resp = client.post(
        f"/api/legal-entities/{entity.id}/journal-entries",
        headers=_auth(token),
        json={
            "legal_entity_id": entity.id,
            "entry_date": "2025-01-05",
            "description": "Cash sale",
            "lines": [
                {"account_id": bank.id, "direction": "debit", "transaction_currency": "USD", "transaction_amount": 100},
                {"account_id": revenue.id, "direction": "credit", "transaction_currency": "USD", "transaction_amount": 100},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    assert len(resp.json()["lines"]) == 2


def test_invalid_login_rejected(client, seed_basic):
    resp = client.post("/api/auth/login", json={"email": "admin@test.example", "password": "wrong"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client, seed_basic):
    entity_id = seed_basic["entity"].id
    resp = client.get(f"/api/legal-entities/{entity_id}/journal-entries")
    assert resp.status_code == 401
