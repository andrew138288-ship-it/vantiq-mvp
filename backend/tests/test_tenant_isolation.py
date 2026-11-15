from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, settings
from app.dependencies import get_db
from app.main import app
from app.models import Tenant, User, TenantMembership, Customer, Conversation, Message
from app.security import hash_password, create_access_token


TEST_PASSWORD = "Vantiq-Test-Password-2026!"


@pytest.fixture()
def isolated_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    tenant_a = Tenant(name="Workspace A", slug="workspace-a")
    tenant_b = Tenant(name="Workspace B", slug="workspace-b")
    tenant_c = Tenant(name="Workspace C", slug="workspace-c")
    user_a = User(
        email="a@example.com",
        display_name="User A",
        password_hash=hash_password(TEST_PASSWORD),
    )
    user_b = User(
        email="b@example.com",
        display_name="User B",
        password_hash=hash_password(TEST_PASSWORD),
    )
    db.add_all([tenant_a, tenant_b, tenant_c, user_a, user_b])
    db.flush()
    membership_a = TenantMembership(tenant_id=tenant_a.id, user_id=user_a.id, role="owner")
    membership_b = TenantMembership(tenant_id=tenant_b.id, user_id=user_b.id, role="owner")
    membership_c = TenantMembership(tenant_id=tenant_c.id, user_id=user_a.id, role="admin")
    db.add_all([membership_a, membership_b, membership_c])
    customer_a = Customer(tenant_id=tenant_a.id, display_name="Customer A")
    customer_b = Customer(tenant_id=tenant_b.id, display_name="Customer B")
    db.add_all([customer_a, customer_b])
    db.flush()
    conversation_b = Conversation(
        tenant_id=tenant_b.id,
        customer_id=customer_b.id,
        channel="whatsapp",
        context_authorized_at=None,
    )
    db.add(conversation_b)
    db.flush()
    db.add(Message(
        tenant_id=tenant_b.id,
        conversation_id=conversation_b.id,
        direction="inbound",
        body="Private message from workspace B",
    ))
    db.commit()

    token_a = create_access_token(
        user_id=str(user_a.id), tenant_id=str(tenant_a.id), role="owner"
    )
    ids = {
        "user_a": str(user_a.id),
        "tenant_a": str(tenant_a.id),
        "tenant_b": str(tenant_b.id),
        "tenant_c": str(tenant_c.id),
        "customer_a": str(customer_a.id),
        "customer_b": str(customer_b.id),
        "conversation_b": str(conversation_b.id),
    }
    db.close()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, token_a, ids, TestingSession

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_customer_list_is_scoped_to_current_workspace(isolated_client):
    client, token, ids, _ = isolated_client
    response = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.json()}
    assert ids["customer_a"] in returned_ids
    assert ids["customer_b"] not in returned_ids


def test_customer_cannot_be_read_or_updated_across_workspaces(isolated_client):
    client, token, ids, _ = isolated_client
    headers = {"Authorization": f"Bearer {token}"}
    read_response = client.get(f"/api/v1/customers/{ids['customer_b']}", headers=headers)
    update_response = client.patch(
        f"/api/v1/customers/{ids['customer_b']}",
        headers=headers,
        json={"display_name": "Unauthorized change"},
    )
    assert read_response.status_code == 404
    assert update_response.status_code == 404


def test_conversation_and_messages_cannot_be_accessed_across_workspaces(isolated_client):
    client, token, ids, _ = isolated_client
    headers = {"Authorization": f"Bearer {token}"}
    authorize_response = client.post(
        f"/api/v1/conversations/{ids['conversation_b']}/authorize-context",
        headers=headers,
    )
    messages_response = client.get(
        f"/api/v1/conversations/{ids['conversation_b']}/messages",
        headers=headers,
    )
    assert authorize_response.status_code == 404
    assert messages_response.status_code == 404


def test_cannot_create_conversation_for_another_workspaces_customer(isolated_client):
    client, token, ids, _ = isolated_client
    response = client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": ids["customer_b"], "channel": "whatsapp"},
    )
    assert response.status_code == 404


def test_login_requires_workspace_selection_and_issues_selected_workspace_token(isolated_client):
    client, _, ids, _ = isolated_client
    credentials = {"email": " A@EXAMPLE.COM ", "password": TEST_PASSWORD}

    ambiguous = client.post("/api/v1/auth/login", json=credentials)
    assert ambiguous.status_code == 409
    assert ambiguous.json()["detail"]["code"] == "workspace_selection_required"
    available_ids = {
        workspace["tenant_id"]
        for workspace in ambiguous.json()["detail"]["workspaces"]
    }
    assert available_ids == {ids["tenant_a"], ids["tenant_c"]}

    selected = client.post(
        "/api/v1/auth/login",
        json={**credentials, "tenant_id": ids["tenant_c"]},
    )
    assert selected.status_code == 200
    assert selected.json()["user"]["tenant_id"] == ids["tenant_c"]

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {selected.json()['access_token']}"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["tenant_id"] == ids["tenant_c"]
    assert current_user.json()["role"] == "admin"


def test_login_rejects_workspace_without_membership(isolated_client):
    client, _, ids, _ = isolated_client
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "a@example.com",
            "password": TEST_PASSWORD,
            "tenant_id": ids["tenant_b"],
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize("token_kind", ["malformed", "expired", "wrong_signature"])
def test_authentication_rejects_invalid_tokens(isolated_client, token_kind):
    client, _, ids, _ = isolated_client
    if token_kind == "malformed":
        token = "not-a-jwt"
    else:
        claims = {
            "sub": ids["user_a"],
            "tenant_id": ids["tenant_a"],
            "role": "owner",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
        secret = "incorrect-test-secret-key-with-32-bytes-minimum" if token_kind == "wrong_signature" else settings.jwt_secret
        token = jwt.encode(claims, secret, algorithm="HS256")

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_authenticated_endpoints_require_bearer_token(isolated_client):
    client, _, _, _ = isolated_client
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_deactivated_user_cannot_reuse_existing_token(isolated_client):
    client, token, ids, session_factory = isolated_client
    db = session_factory()
    try:
        user = db.get(User, uuid.UUID(ids["user_a"]))
        user.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_login_endpoint_enforces_ip_rate_limit(isolated_client):
    from app.rate_limit import limiter

    client, _, _, _ = isolated_client
    limiter.reset()
    try:
        for _ in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "missing@example.com", "password": "incorrect-password"},
            )
            assert response.status_code == 401
        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "incorrect-password"},
        )
        assert limited.status_code == 429
    finally:
        limiter.reset()
