from pydantic import ValidationError
import pytest

from app.schemas import MessageCreate, RegisterRequest
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_is_hashed_and_verifiable():
    password = "Vantiq-Test-Password-2026!"
    encoded = hash_password(password)
    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_contains_user_and_tenant_claims():
    token = create_access_token(
        user_id="4c2c45a4-9b45-4e1b-b30c-13eaa36d3c1a",
        tenant_id="3c2c45a4-9b45-4e1b-b30c-13eaa36d3c1a",
        role="owner",
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "4c2c45a4-9b45-4e1b-b30c-13eaa36d3c1a"
    assert claims["tenant_id"] == "3c2c45a4-9b45-4e1b-b30c-13eaa36d3c1a"
    assert claims["role"] == "owner"
    assert "exp" in claims


def test_registration_normalizes_email():
    payload = RegisterRequest(
        email="  SALES@EXAMPLE.COM ",
        password="Vantiq-Test-Password-2026!",
        display_name="Pilot User",
        tenant_name="Pilot Workspace",
    )
    assert payload.email == "sales@example.com"


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="sales@example.com",
            password="short",
            display_name="Pilot User",
            tenant_name="Pilot Workspace",
        )


def test_message_direction_is_restricted():
    with pytest.raises(ValidationError):
        MessageCreate(direction="system", body="This direction is not allowed")
