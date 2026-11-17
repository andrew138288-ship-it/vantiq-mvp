import uuid
from app.models import CustomerMemory, CustomerMemoryRevision, CustomerMemoryUpdateEvent
from test_tenant_isolation import isolated_client


def test_verified_identity_resolves_to_one_customer(isolated_client):
    client, token, _, _ = isolated_client
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "channel": "whatsapp",
        "external_ref": "wa-contact-15551234567",
        "display_name": "New WhatsApp Customer",
    }
    first = client.post("/api/v1/customers/resolve", headers=headers, json=payload)
    second = client.post("/api/v1/customers/resolve", headers=headers, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["customer"]["id"] == second.json()["customer"]["id"]


def test_ambiguous_or_blank_identity_is_rejected(isolated_client):
    client, token, _, _ = isolated_client
    response = client.post(
        "/api/v1/customers/resolve",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": "whatsapp", "external_ref": "   "},
    )
    assert response.status_code == 422


def test_customer_memory_requires_version_and_is_idempotent(isolated_client):
    client, token, ids, session_factory = isolated_client
    headers = {"Authorization": f"Bearer {token}"}
    customer_id = ids["customer_a"]
    payload = {
        "summary": "Customer is evaluating options and asked about delivery.",
        "structured_data": {"needs": ["delivery information"]},
        "provenance": [{"field": "needs", "source": "current_chat", "confidence": 0.9}],
        "idempotency_key": "whatsapp-context-v1-event-0001",
        "expected_version": 0,
    }
    first = client.post(f"/api/v1/customers/{customer_id}/memory", headers=headers, json=payload)
    retry = client.post(f"/api/v1/customers/{customer_id}/memory", headers=headers, json=payload)
    assert first.status_code == 200
    assert retry.status_code == 200
    assert first.json()["version"] == 1
    assert retry.json()["version"] == 1

    stale = client.post(
        f"/api/v1/customers/{customer_id}/memory",
        headers=headers,
        json={**payload, "idempotency_key": "whatsapp-context-v1-event-0002"},
    )
    assert stale.status_code == 409

    current = client.get(f"/api/v1/customers/{customer_id}/memory", headers=headers)
    history = client.get(f"/api/v1/customers/{customer_id}/memory/revisions", headers=headers)
    assert current.status_code == 200
    assert current.json()["summary"] == payload["summary"]
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["version"] == 1
    assert history.json()[0]["provenance"] == payload["provenance"]

    db = session_factory()
    try:
        assert db.query(CustomerMemory).filter_by(customer_id=uuid.UUID(customer_id)).count() == 1
        assert db.query(CustomerMemoryRevision).filter_by(customer_id=uuid.UUID(customer_id)).count() == 1
        assert db.query(CustomerMemoryUpdateEvent).filter_by(customer_id=uuid.UUID(customer_id)).count() == 1
    finally:
        db.close()


def test_customer_memory_is_tenant_scoped(isolated_client):
    client, token, ids, _ = isolated_client
    response = client.post(
        f"/api/v1/customers/{ids['customer_b']}/memory",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "summary": "should not be saved",
            "structured_data": {},
            "provenance": [],
            "idempotency_key": "tenant-bound-event-001",
            "expected_version": 0,
        },
    )
    assert response.status_code == 404
