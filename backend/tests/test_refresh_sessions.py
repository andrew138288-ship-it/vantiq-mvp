import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models import Tenant, User, TenantMembership, RefreshSession
from app.security import hash_password
from app.rate_limit import limiter


PASSWORD = "Session-Test-Password-123!"


@pytest.fixture()
def session_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    tenant = Tenant(name="Session Workspace", slug="session-workspace")
    user = User(email="sessions@example.com", display_name="Session User", password_hash=hash_password(PASSWORD))
    db.add_all([tenant, user])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    limiter.reset()
    with TestClient(app) as client:
        yield client, TestingSession
    app.dependency_overrides.clear()
    limiter.reset()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def login(client):
    response = client.post("/api/v1/auth/login", json={"email": "sessions@example.com", "password": PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_login_stores_only_refresh_token_digest(session_client):
    client, factory = session_client
    result = login(client)
    assert result["refresh_token"]
    db = factory()
    try:
        rows = list(db.scalars(select(RefreshSession)).all())
        assert len(rows) == 1
        assert rows[0].token_hash != result["refresh_token"]
        assert len(rows[0].token_hash) == 64
    finally:
        db.close()


def test_refresh_rotates_token_and_rejects_previous_token(session_client):
    client, factory = session_client
    initial = login(client)
    renewed = client.post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert renewed.status_code == 200
    rotated = renewed.json()
    assert rotated["access_token"] != initial["access_token"]
    assert rotated["refresh_token"] != initial["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert reused.status_code == 401
    latest = client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert latest.status_code == 401

    db = factory()
    try:
        assert all(row.revoked_at is not None for row in db.scalars(select(RefreshSession)).all())
    finally:
        db.close()


def test_session_listing_and_single_session_revocation(session_client):
    client, _ = session_client
    first = login(client)
    second = login(client)
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    listed = client.get("/api/v1/auth/sessions", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    target = listed.json()[0]["session_id"]

    revoked = client.delete(f"/api/v1/auth/sessions/{target}", headers=headers)
    assert revoked.status_code == 200
    after = client.get("/api/v1/auth/sessions", headers=headers)
    assert after.status_code == 200
    assert len(after.json()) == 1


def test_logout_all_revokes_sessions_and_access_tokens(session_client):
    client, _ = session_client
    first = login(client)
    second = login(client)
    headers = {"Authorization": f"Bearer {first['access_token']}"}
    response = client.post("/api/v1/auth/logout-all", headers=headers)
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401



def test_expired_refresh_token_is_rejected_and_revoked(session_client):
    client, factory = session_client
    initial = login(client)
    db = factory()
    try:
        row = db.scalar(select(RefreshSession))
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert response.status_code == 401

    db = factory()
    try:
        row = db.scalar(select(RefreshSession))
        assert row.revoked_at is not None
    finally:
        db.close()


def test_logout_is_idempotent_and_revokes_refresh_token(session_client):
    client, factory = session_client
    initial = login(client)
    payload = {"refresh_token": initial["refresh_token"]}
    first = client.post("/api/v1/auth/logout", json=payload)
    second = client.post("/api/v1/auth/logout", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert client.post("/api/v1/auth/refresh", json=payload).status_code == 401

    db = factory()
    try:
        row = db.scalar(select(RefreshSession))
        assert row.revoked_at is not None
    finally:
        db.close()
