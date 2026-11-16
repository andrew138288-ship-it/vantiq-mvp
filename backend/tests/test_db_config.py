from app.db import normalize_database_url


def test_normalizes_legacy_postgres_url():
    assert normalize_database_url("postgres://user:pass@host:5432/db") == (
        "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_normalizes_postgresql_url():
    assert normalize_database_url("postgresql://user:pass@host:5432/db") == (
        "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_preserves_psycopg_url():
    url = "postgresql+psycopg://user:pass@host:5432/db"
    assert normalize_database_url(url) == url


def test_production_rejects_mock_ai_provider():
    import pytest
    from pydantic import ValidationError
    from app.db import Settings

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="x" * 48,
            ai_provider="mock",
        )


def test_production_requires_openai_key_when_openai_selected():
    import pytest
    from pydantic import ValidationError
    from app.db import Settings

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="x" * 48,
            ai_provider="openai",
            openai_api_key=None,
        )
