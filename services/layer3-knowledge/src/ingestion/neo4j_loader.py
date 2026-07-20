"""Compatibility shim: Neo4jLoader has moved to src.ingestion.neo4j."""

from src.ingestion.neo4j import (
    Neo4jLoader,
    RDFLoadError,
    TenantValidationError,
    validate_ingestion_tenant_id,
)

__all__ = [
    "Neo4jLoader",
    "RDFLoadError",
    "TenantValidationError",
    "validate_ingestion_tenant_id",
]
