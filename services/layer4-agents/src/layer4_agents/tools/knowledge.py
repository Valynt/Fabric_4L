from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import AuthenticationError

"""
Knowledge graph tools with tenant isolation.

All tools enforce tenant boundaries and audit tool invocations.
"""


import logging
import os
from typing import Any
from uuid import UUID

from neo4j import AsyncGraphDatabase
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext, get_request_context
from value_fabric.shared.identity.policy_registry import authorize_action

from layer4_agents.config.settings import get_settings

logger = logging.getLogger(__name__)


class ConfigurationError(ValueError):
    """Raised when a tool is misconfigured (e.g. missing a required secret)."""


_NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
_NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
_NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or get_settings().neo4j_password
_NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "valuefabric")
_DRIVER = None


def _resolve_password() -> str:
    """Resolve Neo4j password from environment or settings; fail closed if missing."""
    password = os.environ.get("NEO4J_PASSWORD") or get_settings().neo4j_password
    if not password:
        raise ConfigurationError(
            "Neo4j password is required; set NEO4J_PASSWORD or LAYER4_NEO4J_PASSWORD"
        )
    return password


def _get_driver():
    """Lazy initialize Neo4j driver."""
    global _DRIVER
    if _DRIVER is None:
        password = _resolve_password()
        _DRIVER = AsyncGraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, password))
    return _DRIVER


def _require_tool_context(context: RequestContext | None = None) -> RequestContext:
    """Resolve the explicit or ambient request context and fail closed otherwise."""
    ctx = context or get_request_context()
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Tenant-scoped tool execution requires authenticated context")
    return ctx


def _tenant_uuid_or_none(tenant_id: str) -> UUID | None:
    try:
        return UUID(tenant_id)
    except (TypeError, ValueError):
        return None


def _build_entity_dict(node: Any, labels: list[str]) -> dict[str, Any]:
    entity = dict(node)
    entity["entity_type"] = labels[0] if labels else "Unknown"
    return entity


async def get_entity(
    entity_id: str,
    context: RequestContext | None = None
) -> dict | None:
    """Get entity by ID with tenant scoping."""
    context = authorize_action("layer4.tool.knowledge.read_entity", _require_tool_context(context))
    tenant_id = str(context.tenant_id)

    if "'" in entity_id or "--" in entity_id or "OR" in entity_id.upper():
        logger.warning("Invalid characters in entity_id: %s", entity_id)
        return None

    outcome = AuditOutcome.FAILURE
    reason = "not_found"

    try:
        driver = _get_driver()
        async with driver.session(database=_NEO4J_DATABASE) as session:
            result = await session.run(
                """
                MATCH (n {id: $entity_id, tenant_id: $tenant_id})
                RETURN n, labels(n) AS labels
                LIMIT 1
                """,
                {"entity_id": entity_id, "tenant_id": tenant_id},
            )
            record = await result.single()

            if not record:
                return None

            outcome = AuditOutcome.SUCCESS
            reason = "ok"
            return _build_entity_dict(record["n"], record["labels"])
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("get_entity failed for tenant=%s, entity=%s: %s", tenant_id, entity_id, exc)
        reason = "error"
        return None
    finally:
        emit_audit_event(
            action=AuditAction.KG_NODE_UPDATED,
            outcome=outcome,
            resource_type="entity",
            resource_id=entity_id,
            tenant_id=_tenant_uuid_or_none(tenant_id),
            details={"operation": "get_entity", "reason": reason},
        )


async def update_entity(
    entity_id: str,
    updates: dict,
    context: RequestContext | None = None
) -> dict | None:
    """Update entity with tenant scoping."""
    context = authorize_action("layer4.tool.knowledge.update_entity", _require_tool_context(context))
    tenant_id = str(context.tenant_id)

    safe_updates = {k: v for k, v in updates.items() if k not in {"id", "tenant_id"}}
    outcome = AuditOutcome.FAILURE
    reason = "not_found"

    try:
        driver = _get_driver()
        async with driver.session(database=_NEO4J_DATABASE) as session:
            result = await session.run(
                """
                MATCH (n {id: $entity_id, tenant_id: $tenant_id})
                SET n += $updates
                RETURN n, labels(n) AS labels
                LIMIT 1
                """,
                {"entity_id": entity_id, "tenant_id": tenant_id, "updates": safe_updates},
            )
            record = await result.single()
            if not record:
                return None

            outcome = AuditOutcome.SUCCESS
            reason = "ok"
            return _build_entity_dict(record["n"], record["labels"])
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("update_entity failed for tenant=%s, entity=%s: %s", tenant_id, entity_id, exc)
        reason = "error"
        return None
    finally:
        emit_audit_event(
            action=AuditAction.KG_NODE_UPDATED,
            outcome=outcome,
            resource_type="entity",
            resource_id=entity_id,
            tenant_id=_tenant_uuid_or_none(tenant_id),
            details={"operation": "update_entity", "reason": reason},
        )


async def delete_entity(
    entity_id: str,
    context: RequestContext | None = None
) -> bool:
    """Delete entity with tenant scoping."""
    context = authorize_action("layer4.tool.knowledge.delete_entity", _require_tool_context(context))
    tenant_id = str(context.tenant_id)

    outcome = AuditOutcome.FAILURE
    reason = "not_found"

    try:
        driver = _get_driver()
        async with driver.session(database=_NEO4J_DATABASE) as session:
            result = await session.run(
                """
                MATCH (n {id: $entity_id, tenant_id: $tenant_id})
                WITH n LIMIT 1
                DETACH DELETE n
                RETURN 1 AS deleted
                """,
                {"entity_id": entity_id, "tenant_id": tenant_id},
            )
            record = await result.single()
            deleted = bool(record and record.get("deleted") == 1)
            if deleted:
                outcome = AuditOutcome.SUCCESS
                reason = "ok"
            return deleted
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("delete_entity failed for tenant=%s, entity=%s: %s", tenant_id, entity_id, exc)
        reason = "error"
        return False
    finally:
        emit_audit_event(
            action=AuditAction.KG_NODE_DELETED,
            outcome=outcome,
            resource_type="entity",
            resource_id=entity_id,
            tenant_id=_tenant_uuid_or_none(tenant_id),
            details={"operation": "delete_entity", "reason": reason},
        )


async def search_entities(
    query: str,
    context: RequestContext | None = None
) -> list[dict]:
    """Search entities with tenant scoping."""
    context = authorize_action("layer4.tool.knowledge.read_entity", _require_tool_context(context))
    tenant_id = str(context.tenant_id)

    if len(query) > 10000:
        logger.warning("Query too large: %s characters (max 10000)", len(query))
        return []

    try:
        driver = _get_driver()
        async with driver.session(database=_NEO4J_DATABASE) as session:
            result = await session.run(
                """
                MATCH (n {tenant_id: $tenant_id})
                WHERE toLower(coalesce(n.name, "")) CONTAINS toLower($query)
                   OR toLower(coalesce(n.id, "")) CONTAINS toLower($query)
                   OR toLower(coalesce(n.description, "")) CONTAINS toLower($query)
                RETURN n, labels(n) AS labels
                ORDER BY coalesce(n.name, n.id)
                LIMIT 50
                """,
                {"tenant_id": tenant_id, "query": query.strip()},
            )

            entities: list[dict] = []
            async for record in result:
                entities.append(_build_entity_dict(record["n"], record["labels"]))
            return entities
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("search_entities failed for tenant=%s query=%s: %s", tenant_id, query, exc)
        return []


async def list_entities(
    context: RequestContext | None = None
) -> list[dict]:
    """List entities with tenant scoping."""
    context = authorize_action("layer4.tool.knowledge.read_entity", _require_tool_context(context))
    tenant_id = str(context.tenant_id)
    try:
        driver = _get_driver()
        async with driver.session(database=_NEO4J_DATABASE) as session:
            result = await session.run(
                """
                MATCH (n {tenant_id: $tenant_id})
                RETURN n, labels(n) AS labels
                ORDER BY coalesce(n.name, n.id)
                LIMIT 100
                """,
                {"tenant_id": tenant_id},
            )

            entities: list[dict] = []
            async for record in result:
                entities.append(_build_entity_dict(record["n"], record["labels"]))
            return entities
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("list_entities failed for tenant=%s: %s", tenant_id, exc)
        return []
