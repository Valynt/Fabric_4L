from __future__ import annotations

"""Tenant-validated Neo4j query helpers for Layer 4 services.

Layer 4 services must not execute tenant-owned Cypher directly through
``session.run``.  This module is the shared execution seam that validates the
caller's tenant context, injects the canonical tenant parameters, and keeps
result materialization inside the Neo4j session context.
"""


import re
from typing import Any


class TenantCypherValidationError(ValueError):
    """Raised when a Layer 4 Cypher query violates tenant-isolation rules."""


_TENANT_PARAM_KEYS = ("tenant_id", "_tenant_id")
_TENANT_PARAM_PATTERN = re.compile(r"\$(?:tenant_id|_tenant_id)\b")
_TENANT_PREDICATE_PATTERN = re.compile(
    r"(?i)(?:\{[^}]*\btenant_id\s*:\s*\$(?:tenant_id|_tenant_id)\b[^}]*\}|"
    r"\b[A-Za-z_][A-Za-z0-9_]*\.tenant_id\s*(?:=|IN)\s*\$(?:tenant_id|_tenant_id)\b)"
)


def _validated_tenant_params(
    *,
    tenant_id: str,
    params: dict[str, Any] | None,
    operation: str,
) -> dict[str, Any]:
    """Return parameters after enforcing tenant context as source of truth."""
    if not tenant_id:
        raise TenantCypherValidationError(f"{operation}: tenant_id is required")

    validated = dict(params or {})
    for key in _TENANT_PARAM_KEYS:
        existing = validated.get(key)
        if existing is not None and str(existing) != str(tenant_id):
            raise TenantCypherValidationError(
                f"{operation}: query parameter {key!r} does not match tenant context"
            )

    # Context tenant always wins and both canonical spellings are supplied so
    # existing Layer 4 queries and shared TenantScopedCypher-style queries can
    # use the same execution seam safely.
    validated["tenant_id"] = tenant_id
    validated["_tenant_id"] = tenant_id
    return validated


def _validate_tenant_query(*, query: str, operation: str) -> None:
    """Fail closed for tenant-facing Cypher missing explicit tenant scope."""
    if not _TENANT_PARAM_PATTERN.search(query):
        raise TenantCypherValidationError(f"{operation}: query must reference a tenant parameter")
    if not _TENANT_PREDICATE_PATTERN.search(query):
        raise TenantCypherValidationError(
            f"{operation}: query must include an explicit tenant_id predicate"
        )


async def fetch_tenant_validated_records(
    *,
    driver: Any,
    query: str,
    params: dict[str, Any] | None,
    tenant_id: str,
    operation: str,
) -> list[Any]:
    """Execute tenant-scoped Cypher and materialize all records safely."""
    _validate_tenant_query(query=query, operation=operation)
    validated_params = _validated_tenant_params(
        tenant_id=tenant_id,
        params=params,
        operation=operation,
    )

    async with driver.session() as session:
        result = await session.run(query, validated_params)
        return [record async for record in result]


async def fetch_tenant_validated_single(
    *,
    driver: Any,
    query: str,
    params: dict[str, Any] | None,
    tenant_id: str,
    operation: str,
) -> Any | None:
    """Execute tenant-scoped Cypher and return one record safely."""
    _validate_tenant_query(query=query, operation=operation)
    validated_params = _validated_tenant_params(
        tenant_id=tenant_id,
        params=params,
        operation=operation,
    )

    async with driver.session() as session:
        result = await session.run(query, validated_params)
        return await result.single()
