"""Phase 4: Entity Scope Classification.

Defines entity scope classification for authorization:
- TENANT_WIDE: Entities shared across all accounts in a tenant
- ACCOUNT_SCOPED: Entities restricted to specific accounts
- GLOBAL: System-wide entities (e.g., ontologies, schemas)
"""

from enum import Enum


class EntityScope(str, Enum):
    """Scope classification for entity types."""

    TENANT_WIDE = "tenant_wide"
    """Entities shared across all accounts in a tenant (e.g., Products, ValueDrivers)."""

    ACCOUNT_SCOPED = "account_scoped"
    """Entities restricted to specific accounts (e.g., PainSignals, custom Evidence)."""

    GLOBAL = "global"
    """System-wide entities (e.g., ontologies, schemas, sync metadata)."""


# Entity type to scope mapping
ENTITY_SCOPE_MAPPING: dict[str, EntityScope] = {
    # Tenant-wide entities (shared across accounts)
    "Product": EntityScope.TENANT_WIDE,
    "ValueDriver": EntityScope.TENANT_WIDE,
    "Capability": EntityScope.TENANT_WIDE,
    "UseCase": EntityScope.TENANT_WIDE,
    "Persona": EntityScope.TENANT_WIDE,
    "Formula": EntityScope.TENANT_WIDE,
    "BenchmarkDataset": EntityScope.TENANT_WIDE,
    "ValuePack": EntityScope.TENANT_WIDE,
    
    # Account-scoped entities (restricted to specific accounts)
    "PainSignal": EntityScope.ACCOUNT_SCOPED,
    "Account": EntityScope.ACCOUNT_SCOPED,
    "Evidence": EntityScope.ACCOUNT_SCOPED,  # Case studies may be account-specific
    
    # Global entities (system-wide)
    "SyncMetadata": EntityScope.GLOBAL,
    "Ontology": EntityScope.GLOBAL,
    "Schema": EntityScope.GLOBAL,
    "Constraint": EntityScope.GLOBAL,
}


def get_entity_scope(entity_type: str) -> EntityScope:
    """Get the scope classification for an entity type.

    Args:
        entity_type: The entity type to classify

    Returns:
        EntityScope classification

    Raises:
        ValueError: If entity type is unknown
    """
    scope = ENTITY_SCOPE_MAPPING.get(entity_type)
    if scope is None:
        # Default to tenant-wide for unknown types (fail-safe)
        return EntityScope.TENANT_WIDE
    return scope


def is_account_scoped(entity_type: str) -> bool:
    """Check if an entity type is account-scoped.

    Args:
        entity_type: The entity type to check

    Returns:
        True if account-scoped, False otherwise
    """
    return get_entity_scope(entity_type) == EntityScope.ACCOUNT_SCOPED


def is_tenant_wide(entity_type: str) -> bool:
    """Check if an entity type is tenant-wide.

    Args:
        entity_type: The entity type to check

    Returns:
        True if tenant-wide, False otherwise
    """
    return get_entity_scope(entity_type) == EntityScope.TENANT_WIDE


def is_global(entity_type: str) -> bool:
    """Check if an entity type is global.

    Args:
        entity_type: The entity type to check

    Returns:
        True if global, False otherwise
    """
    return get_entity_scope(entity_type) == EntityScope.GLOBAL


def get_account_scoped_entity_types() -> set[str]:
    """Get all account-scoped entity types.

    Returns:
        Set of account-scoped entity type names
    """
    return {
        entity_type
        for entity_type, scope in ENTITY_SCOPE_MAPPING.items()
        if scope == EntityScope.ACCOUNT_SCOPED
    }


def get_tenant_wide_entity_types() -> set[str]:
    """Get all tenant-wide entity types.

    Returns:
        Set of tenant-wide entity type names
    """
    return {
        entity_type
        for entity_type, scope in ENTITY_SCOPE_MAPPING.items()
        if scope == EntityScope.TENANT_WIDE
    }


def get_global_entity_types() -> set[str]:
    """Get all global entity types.

    Returns:
        Set of global entity type names
    """
    return {
        entity_type
        for entity_type, scope in ENTITY_SCOPE_MAPPING.items()
        if scope == EntityScope.GLOBAL
    }
