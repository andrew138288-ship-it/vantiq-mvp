import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.dependencies import get_db
from app.main import app
from app.models import Tenant, User, TenantMembership, Customer, Conversation, Message
from app.security import hash_password, create_access_token


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
    user_a = User(
        email="a@example.com",
        display_name="User A",
        password_hash=hash_password("Vantiq-Test-Password-2026!"),
    )
    user_b = User(
        email="b@example.com",
        display_name="User B",
        password_hash=hash_password("Vantiq-Test-Password-2026!"),
    )
    db.add_all([tenant_a, tenant_b, user_a, user_b])
    db.flush()
    db.add_all([
        TenantMembership(tenant_id=tenant_a.id, user_id=user_a.id, role="owner"),
        TenantMembership(tenant_id=tenant_b.id, user_id=user_b.id, role="owner"),
    ])
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
        yield client, token_a, ids

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_customer_list_is_scoped_to_current_workspace(isolated_client):
    client, token, ids = isolated_client
    response = client.get(
        "/api/v1/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.json()}
    assert ids["customer_a"] in returned_ids
    assert ids["customer_b"] not in returned_ids


def test_customer_cannot_be_read_or_updated_across_workspaces(isolated_client):
    client, token, ids = isolated_client
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
    client, token, ids = isolated_client
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
    client, token, ids = isolated_client
    response = client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"customer_id": ids["customer_b"], "channel": "whatsapp"},
    )
    assert response.status_code == 404
