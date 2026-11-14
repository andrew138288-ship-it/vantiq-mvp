from app.db import Base
from app import models  # noqa: F401


def test_core_tables_are_registered():
    expected = {
        "tenants",
        "users",
        "tenant_memberships",
        "customers",
        "conversations",
        "messages",
        "customer_memories",
    }
    assert expected.issubset(set(Base.metadata.tables))


def test_tenant_owned_records_have_tenant_id():
    for table_name in ("customers", "conversations", "messages", "customer_memories"):
        assert "tenant_id" in Base.metadata.tables[table_name].columns
