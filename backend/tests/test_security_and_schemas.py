from pydantic import ValidationError
import pytest

from app.schemas import MessageCreate, RegisterRequest, LoginRequest, CustomerUpdate
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
    )
    assert payload.email == "sales@example.com"
    assert payload.display_name == "Pilot User"


def test_registration_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="sales@example.com",
            password="short",
            display_name="Pilot User",
        )


def test_login_normalizes_email_and_accepts_optional_workspace():
    tenant_id = "3c2c45a4-9b45-4e1b-b30c-13eaa36d3c1a"
    payload = LoginRequest(
        email=" SALES@EXAMPLE.COM ",
        password="example-password",
        tenant_id=tenant_id,
    )
    assert payload.email == "sales@example.com"
    assert str(payload.tenant_id) == tenant_id


def test_login_workspace_is_optional_for_single_workspace_compatibility():
    payload = LoginRequest(email="sales@example.com", password="example-password")
    assert payload.tenant_id is None


def test_customer_update_allows_omitted_display_name():
    payload = CustomerUpdate(notes="Follow up next week")
    assert payload.model_fields_set == {"notes"}
    assert payload.display_name is None


def test_customer_update_rejects_explicit_null_display_name():
    with pytest.raises(ValidationError, match="display_name cannot be null"):
        CustomerUpdate(display_name=None)


def test_customer_update_accepts_valid_display_name():
    payload = CustomerUpdate(display_name="Updated customer")
    assert payload.display_name == "Updated customer"


def test_message_direction_is_restricted():
    with pytest.raises(ValidationError):
        MessageCreate(direction="system", body="This direction is not allowed")


def test_alembic_revision_ids_fit_version_column_and_form_single_chain():
    from pathlib import Path
    import ast

    migration_dir = Path("migrations/versions")
    revisions = {}
    for migration_file in sorted(migration_dir.glob("*.py")):
        if migration_file.name == "__init__.py":
            continue
        tree = ast.parse(migration_file.read_text(encoding="utf-8"))
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in {"revision", "down_revision"}:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
        revision = values.get("revision")
        assert isinstance(revision, str) and len(revision) <= 32, f"{migration_file.name}: invalid Alembic revision"
        assert revision not in revisions, f"duplicate revision: {revision}"
        revisions[revision] = values.get("down_revision")

    assert revisions, "no Alembic migrations found"
    roots = [revision for revision, parent in revisions.items() if parent is None]
    assert len(roots) == 1, f"expected one migration root, got {roots}"
    for revision, parent in revisions.items():
        if parent is not None:
            assert parent in revisions, f"{revision} references missing parent {parent}"


def test_production_settings_reject_default_jwt_secret():
    from app.db import Settings

    with pytest.raises(ValidationError, match="Production requires JWT_SECRET"):
        Settings(app_env="production")


def test_production_settings_reject_short_jwt_secret():
    from app.db import Settings

    with pytest.raises(ValidationError, match="Production requires JWT_SECRET"):
        Settings(app_env="production", jwt_secret="too-short-secret")


def test_production_settings_accept_strong_explicit_jwt_secret():
    from app.db import Settings

    configured = Settings(
        app_env="production",
        jwt_secret="a-secure-test-secret-with-more-than-32-characters",
    )
    assert configured.app_env == "production"
