from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models import User, EmailVerificationToken
from app.routers import auth as auth_router
from app.rate_limit import limiter
from app.security import verify_password


PASSWORD = "Vantiq-Registration-Password-2026!"


@pytest.fixture()
def verification_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

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


def test_registration_requires_email_verification_before_login(verification_client, monkeypatch):
    client, session_factory = verification_client
    sent = []
    monkeypatch.setattr(
        auth_router,
        "send_email_verification",
        lambda email, token: sent.append((email, token)),
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "  NEW@EXAMPLE.COM ",
            "password": PASSWORD,
            "display_name": "New User",
        },
    )
    assert response.status_code == 202
    assert "access_token" not in response.json()
    assert len(sent) == 1
    assert sent[0][0] == "new@example.com"

    db = session_factory()
    try:
        user = db.scalar(select(User).where(User.email == "new@example.com"))
        token_row = db.scalar(select(EmailVerificationToken))
        assert user is not None
        assert user.is_active is True
        assert user.is_email_verified is False
        assert user.account_status == "pending_verification"
        assert token_row is not None
        assert token_row.token_hash != sent[0][1]
        assert verify_password(PASSWORD, user.password_hash)
    finally:
        db.close()

    login_before = client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": PASSWORD},
    )
    assert login_before.status_code == 403
    assert login_before.json()["detail"]["code"] == "email_not_verified"

    verified = client.post(
        "/api/v1/auth/verify-email",
        json={"token": sent[0][1]},
    )
    assert verified.status_code == 200
    assert "free VANTIQ account is now active" in verified.json()["message"]
    db = session_factory()
    try:
        activated = db.scalar(select(User).where(User.email == "new@example.com"))
        assert activated.account_status == "free_active"
    finally:
        db.close()

    login_after = client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": PASSWORD},
    )
    assert login_after.status_code == 200
    assert login_after.json()["access_token"]


def test_registration_response_does_not_disclose_existing_email(verification_client, monkeypatch):
    client, _ = verification_client
    sent = []
    monkeypatch.setattr(
        auth_router,
        "send_email_verification",
        lambda email, token: sent.append((email, token)),
    )
    payload = {
        "email": "same@example.com",
        "password": PASSWORD,
        "display_name": "Same User",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert len(sent) == 1


def test_resend_verification_invalidates_previous_token(verification_client, monkeypatch):
    client, session_factory = verification_client
    sent = []
    monkeypatch.setattr(
        auth_router,
        "send_email_verification",
        lambda email, token: sent.append((email, token)),
    )
    payload = {
        "email": "resend@example.com",
        "password": PASSWORD,
        "display_name": "Resend User",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 202
    first_token = sent[-1][1]

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert response.status_code == 202
    second_token = sent[-1][1]
    assert second_token != first_token

    stale = client.post("/api/v1/auth/verify-email", json={"token": first_token})
    assert stale.status_code == 400
    valid = client.post("/api/v1/auth/verify-email", json={"token": second_token})
    assert valid.status_code == 200

    db = session_factory()
    try:
        rows = list(db.scalars(select(EmailVerificationToken)).all())
        assert len(rows) == 2
        assert all(row.used_at is not None for row in rows)
    finally:
        db.close()


def test_verification_rejects_expired_token(verification_client, monkeypatch):
    client, session_factory = verification_client
    sent = []
    monkeypatch.setattr(
        auth_router,
        "send_email_verification",
        lambda email, token: sent.append((email, token)),
    )
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "expired@example.com",
            "password": PASSWORD,
            "display_name": "Expired User",
        },
    )

    db = session_factory()
    try:
        row = db.scalar(select(EmailVerificationToken))
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    response = client.post("/api/v1/auth/verify-email", json={"token": sent[0][1]})
    assert response.status_code == 400
