
from layer4_agents.api.tenants import _TENANT_ENTITY_TABLES


def test_tenant_entity_tables_are_allow_listed():
    # Unknown table names must not be accepted.
    assert "users" not in _TENANT_ENTITY_TABLES
    assert "tenants" in _TENANT_ENTITY_TABLES or len(_TENANT_ENTITY_TABLES) > 0
