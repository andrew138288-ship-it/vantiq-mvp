from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models import Tenant, User, TenantMembership, PasswordResetToken
from app.security import hash_password, verify_password
from app.routers import auth as auth_router
from app.rate_limit import limiter


OLD_PASSWORD = "Old-Password-123!"
NEW_PASSWORD = "New-Password-456!"


@pytest.fixture()
def reset_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    tenant = Tenant(name="Reset Workspace", slug="reset-workspace")
    user = User(email="reset@example.com", display_name="Reset User", password_hash=hash_password(OLD_PASSWORD))
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


def test_password_reset_request_is_generic_for_unknown_email(reset_client, monkeypatch):
    client, _ = reset_client
    sent = []
    monkeypatch.setattr(auth_router, "send_password_reset_email", lambda email, token: sent.append((email, token)))
    response = client.post("/api/v1/auth/password-reset/request", json={"email": "unknown@example.com"})
    assert response.status_code == 202
    assert response.json()["message"] == "If the account exists, password reset instructions will be sent."
    assert sent == []


def test_password_reset_changes_password_and_token_is_single_use(reset_client, monkeypatch):
    client, session_factory = reset_client
    sent = []
    monkeypatch.setattr(auth_router, "send_password_reset_email", lambda email, token: sent.append((email, token)))
    old_session = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": OLD_PASSWORD})
    assert old_session.status_code == 200

    requested = client.post("/api/v1/auth/password-reset/request", json={"email": "RESET@example.com"})
    assert requested.status_code == 202
    assert len(sent) == 1
    assert sent[0][0] == "reset@example.com"

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": sent[0][1], "new_password": NEW_PASSWORD},
    )
    assert confirmed.status_code == 200
    assert "Please sign in" in confirmed.json()["message"]

    login_new = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": NEW_PASSWORD})
    assert login_new.status_code == 200
    login_old = client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": OLD_PASSWORD})
    assert login_old.status_code == 401
    revoked_session = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_session.json()['access_token']}"},
    )
    assert revoked_session.status_code == 401

    reused = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": sent[0][1], "new_password": "Another-Password-789!"},
    )
    assert reused.status_code == 400

    db = session_factory()
    try:
        reset = db.scalar(select(PasswordResetToken))
        assert reset is not None and reset.used_at is not None
    finally:
        db.close()


def test_password_reset_rejects_invalid_token(reset_client):
    client, _ = reset_client
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "x" * 40, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400


def test_password_reset_requires_strong_password(reset_client):
    client, _ = reset_client
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "x" * 40, "new_password": "short"},
    )
    assert response.status_code == 422
