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
