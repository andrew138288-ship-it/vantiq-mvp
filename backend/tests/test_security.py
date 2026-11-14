from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_not_plaintext_and_verifies():
    raw = "Vantiq-Test-Password-2026!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_contains_tenant_scope():
    token = create_access_token(
        user_id="11111111-1111-4111-8111-111111111111",
        tenant_id="22222222-2222-4222-8222-222222222222",
        role="owner",
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "11111111-1111-4111-8111-111111111111"
    assert claims["tenant_id"] == "22222222-2222-4222-8222-222222222222"
    assert claims["role"] == "owner"
