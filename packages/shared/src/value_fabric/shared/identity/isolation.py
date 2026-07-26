"""Tenant isolation helpers for relational and graph data stores.

Provides:
- TenantScopedMixin: SQLAlchemy mixin that adds a tenant_id column and
  automatically filters queries to the current tenant.
- TenantScopedCypher: Neo4j Cypher query builder that prepends mandatory
  tenant_id predicates to prevent cross-tenant data leakage.
- ScopedQuery/SystemCypher: explicit query metadata objects for strict
  builder enforcement and audited global/system operations.
- tenant_cache_key: Namespaced Redis cache key helper.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy mixin
# ---------------------------------------------------------------------------


class TenantScopedMixin:
    """Add ``tenant_id`` to an ORM model and supply a scoping helper.

    Inherit from this mixin **before** ``Base`` in your model definition::

        class MyModel(TenantScopedMixin, Base):
            __tablename__ = "my_table"
            ...

    Then use :meth:`scoped_query` to build pre-filtered selects::

        stmt = MyModel.scoped_query(tenant_id).where(MyModel.name == "Acme")
        result = await session.execute(stmt)
    """

    from sqlalchemy import Column
    from sqlalchemy.dialects.postgresql import UUID as _PGUUID

    __abstract__ = True

    @classmethod
    def scoped_query(cls, tenant_id: UUID):
        """Return a SELECT statement pre-filtered to ``tenant_id``."""
        from sqlalchemy import select

        return select(cls).where(cls.tenant_id == tenant_id)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Neo4j strict builder enforcement primitives
# ---------------------------------------------------------------------------


class QueryScope(str, Enum):
    """Explicit execution scope for Neo4j Cypher queries."""

    TENANT = "tenant"
    SYSTEM = "system"
    MIGRATION = "migration"
    HEALTH = "health"
    SCHEMA = "schema"
    BACKUP = "backup"


@dataclass(frozen=True)
class ScopedQuery:
    """A Cypher query with explicit scope metadata.

    ``ScopedQuery`` is the canonical object passed through strict Layer 3 graph
    execution seams. Tenant-facing code should construct these through
    ``TenantScopedCypher`` rather than passing raw strings to Neo4j sessions.
    """

    cypher: str
    params: Dict[str, Any] = field(default_factory=dict)
    scope: QueryScope = QueryScope.TENANT
    tenant_id: str | None = None
    operation: str = "query"
    labels: tuple[str, ...] = ()
    reason: str | None = None
    allowlist_key: str | None = None

    def as_tuple(self) -> Tuple[str, Dict[str, Any]]:
        """Return legacy ``(cypher, params)`` representation."""
        return self.cypher, dict(self.params)


@dataclass(frozen=True)
class TenantLabelPolicy:
    """Policy registry for labels that must be tenant-scoped.

    The registry intentionally errs on the side of treating business-domain
    labels as tenant-owned. Operational metadata labels can be added to
    ``global_labels`` only when a reviewed system-scope path owns them.
    """

    tenant_labels: frozenset[str] = frozenset(
        {
            "Account",
            "Battlecard",
            "Benchmark",
            "BenchmarkDataset",
            "BusinessCase",
            "Capability",
            "CaseStudy",
            "Chunk",
            "Community",
            "Company",
            "Competitor",
            "Contact",
            "Customer",
            "Document",
            "Entity",
            "Evidence",
            "Formula",
            "FormulaVersion",
            "Industry",
            "Insight",
            "Model",
            "Opportunity",
            "PainSignal",
            "Persona",
            "Product",
            "Prospect",
            "ROICalculation",
            "ROITemplate",
            "Segment",
            "Signal",
            "Source",
            "Stakeholder",
            "UseCase",
            "ValueDriver",
            "ValueLever",
            "ValueModel",
            "ValuePack",
            "ValueTree",
            "Variable",
        }
    )
    tenant_relationship_types: frozenset[str] = frozenset(
        {
            "ADDRESSES",
            "BELONGS_TO",
            "CONTAINS",
            "DEPENDS_ON",
            "EXHIBITS",
            "HAS_CHUNK",
            "HAS_EVIDENCE",
            "HAS_FORMULA",
            "HAS_SIGNAL",
            "HAS_VALUE_DRIVER",
            "IMPACTS",
            "MAPS_TO",
            "OWNS",
            "RELATES_TO",
            "SUPPORTED_BY",
            "USES",
        }
    )
    global_labels: frozenset[str] = frozenset({"Migration", "SchemaVersion", "SystemMetadata"})
    tenant_property: str = "tenant_id"
    compatible_tenant_properties: tuple[str, ...] = ("tenant_id", "tenantId")

    def is_tenant_owned(self, label: str | None) -> bool:
        """Return whether ``label`` is treated as tenant-owned."""
        return bool(label) and label in self.tenant_labels

    def requires_scope(self, labels: Iterable[str]) -> bool:
        """Return whether any label in ``labels`` is tenant-owned."""
        return any(self.is_tenant_owned(label) for label in labels)

    def is_tenant_relationship(self, relationship_type: str | None) -> bool:
        """Return whether a relationship type is treated as tenant-owned."""
        return bool(relationship_type) and relationship_type in self.tenant_relationship_types


DEFAULT_TENANT_LABEL_POLICY = TenantLabelPolicy()


class SystemCypher:
    """Factory for audited global/system Cypher queries.

    System-scope queries are an explicit escape hatch for health checks,
    schema/index operations, migrations, and backups. They should not be used
    from tenant-facing request handlers to access tenant-owned data.
    """

    _SAFE_HEALTH_PATTERNS = (
        re.compile(r"^\s*RETURN\s+1\s+AS\s+\w+\s*$", re.IGNORECASE),
        re.compile(r"^\s*CALL\s+dbms\.components\s*\(\s*\)\s*YIELD\s+", re.IGNORECASE),
    )

    @staticmethod
    def _build(
        cypher: str,
        *,
        params: Mapping[str, Any] | None = None,
        scope: QueryScope,
        operation: str,
        reason: str,
        allowlist_key: str,
    ) -> ScopedQuery:
        if not reason.strip():
            raise ValueError("system-scope queries require a non-empty reason")
        if not allowlist_key.strip():
            raise ValueError("system-scope queries require an allowlist_key")
        return ScopedQuery(
            cypher=cypher,
            params=dict(params or {}),
            scope=scope,
            operation=operation,
            reason=reason,
            allowlist_key=allowlist_key,
        )

    @classmethod
    def health_check(
        cls,
        cypher: str = "RETURN 1 AS ok",
        *,
        params: Mapping[str, Any] | None = None,
        reason: str = "Neo4j health check",
        allowlist_key: str = "system.health_check",
    ) -> ScopedQuery:
        """Create an explicitly global health-check query."""
        if not any(pattern.search(cypher) for pattern in cls._SAFE_HEALTH_PATTERNS):
            raise ValueError("health_check only allows constant-return or DBMS metadata queries")
        return cls._build(
            cypher,
            params=params,
            scope=QueryScope.HEALTH,
            operation="health_check",
            reason=reason,
            allowlist_key=allowlist_key,
        )

    @classmethod
    def schema_operation(
        cls,
        cypher: str,
        *,
        params: Mapping[str, Any] | None = None,
        reason: str,
        allowlist_key: str,
    ) -> ScopedQuery:
        """Create an explicitly global schema/index operation query."""
        return cls._build(
            cypher,
            params=params,
            scope=QueryScope.SCHEMA,
            operation="schema_operation",
            reason=reason,
            allowlist_key=allowlist_key,
        )

    @classmethod
    def migration(
        cls,
        cypher: str,
        *,
        params: Mapping[str, Any] | None = None,
        reason: str,
        allowlist_key: str,
    ) -> ScopedQuery:
        """Create an explicitly global migration query."""
        return cls._build(
            cypher,
            params=params,
            scope=QueryScope.MIGRATION,
            operation="migration",
            reason=reason,
            allowlist_key=allowlist_key,
        )

    @classmethod
    def backup(
        cls,
        cypher: str,
        *,
        params: Mapping[str, Any] | None = None,
        reason: str,
        allowlist_key: str,
    ) -> ScopedQuery:
        """Create an explicitly global backup/restore query."""
        return cls._build(
            cypher,
            params=params,
            scope=QueryScope.BACKUP,
            operation="backup",
            reason=reason,
            allowlist_key=allowlist_key,
        )


class TenantScopedCypher:
    """Build Cypher queries that always include tenant predicates.

    The class preserves the historical tuple-return methods while adding
    ``ScopedQuery``-returning methods for Strict Builder Enforcement. New code
    should prefer the ``*_query`` methods and execute them through a scoped
    session seam.
    """

    def __init__(
        self,
        tenant_id: UUID | str,
        *,
        tenant_property: str = "tenant_id",
        policy: TenantLabelPolicy = DEFAULT_TENANT_LABEL_POLICY,
    ) -> None:
        self._tenant_id = str(tenant_id)
        self._tenant_property = tenant_property
        self._policy = policy

    @property
    def tenant_id(self) -> str:
        """Return the tenant id carried by this builder."""
        return self._tenant_id

    @property
    def tenant_property(self) -> str:
        """Return the tenant property name used by this builder."""
        return self._tenant_property

    def _params(self, extra_params: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"_tenant_id": self._tenant_id}
        if extra_params:
            for key, value in extra_params.items():
                if key not in ("_tenant_id", "tenant_id"):
                    params[key] = value
        return params

    def _tenant_predicate(self, alias: str) -> str:
        return f"{alias}.{self._tenant_property} = $_tenant_id"

    def tenant_scoped_where(
        self,
        alias: str,
        *extra_predicates: str | None,
    ) -> str:
        """Return deterministic WHERE clause predicates with tenant check first.

        Dynamic Cypher builders should use this helper so tenant filtering order
        is stable across wrappers and canonical modules.
        """
        predicates = [self._tenant_predicate(alias)]
        predicates.extend(f"({predicate})" for predicate in extra_predicates if predicate and predicate.strip())
        return " AND ".join(predicates)

    def _query(
        self,
        cypher: str,
        params: Mapping[str, Any],
        *,
        operation: str,
        labels: Sequence[str] = (),
    ) -> ScopedQuery:
        return ScopedQuery(
            cypher=cypher,
            params=dict(params),
            scope=QueryScope.TENANT,
            tenant_id=self._tenant_id,
            operation=operation,
            labels=tuple(labels),
        )

    # -- Node queries --------------------------------------------------------

    def match_node_query(
        self,
        alias: str,
        label: str,
        *,
        extra_where: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        return_clause: Optional[str] = None,
        optional: bool = False,
    ) -> ScopedQuery:
        """Build a tenant-scoped node ``MATCH`` or ``OPTIONAL MATCH`` query."""
        params = self._params(extra_params)
        ret = return_clause or alias
        match_keyword = "OPTIONAL MATCH" if optional else "MATCH"
        cypher = (
            f"{match_keyword} ({alias}:{label})\n"
            f"WHERE {self.tenant_scoped_where(alias, extra_where)}\n"
            f"RETURN {ret}"
        )
        return self._query(cypher, params, operation="match_node", labels=(label,))

    def match_node(
        self,
        alias: str,
        label: str,
        *,
        extra_where: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        return_clause: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """MATCH a node filtered by tenant_id.

        Returns legacy ``(cypher_string, params_dict)``.
        """
        return self.match_node_query(
            alias,
            label,
            extra_where=extra_where,
            extra_params=extra_params,
            return_clause=return_clause,
        ).as_tuple()

    def optional_match_node(
        self,
        alias: str,
        label: str,
        *,
        extra_where: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        return_clause: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """OPTIONAL MATCH a tenant-scoped node and return legacy tuple form."""
        return self.match_node_query(
            alias,
            label,
            extra_where=extra_where,
            extra_params=extra_params,
            return_clause=return_clause,
            optional=True,
        ).as_tuple()

    def create_node_query(
        self,
        alias: str,
        label: str,
        properties: Dict[str, Any],
        *,
        return_clause: Optional[str] = None,
    ) -> ScopedQuery:
        """Build a ``CREATE`` query with tenant id automatically injected."""
        props = dict(properties)
        props[self._tenant_property] = self._tenant_id

        param_keys = {f"_{alias}_{k}": v for k, v in props.items()}
        prop_str = ", ".join(
            f"{k}: ${pk}" for (k, _), pk in zip(props.items(), param_keys.keys())
        )
        ret = return_clause or alias
        cypher = f"CREATE ({alias}:{label} {{{prop_str}}})\nRETURN {ret}"
        return self._query(cypher, param_keys, operation="create_node", labels=(label,))

    def create_node(
        self,
        alias: str,
        label: str,
        properties: Dict[str, Any],
        *,
        return_clause: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """CREATE a node with tenant_id automatically injected."""
        return self.create_node_query(alias, label, properties, return_clause=return_clause).as_tuple()

    def merge_node_query(
        self,
        alias: str,
        label: str,
        identity: Mapping[str, Any],
        *,
        set_props: Mapping[str, Any] | None = None,
        on_create_props: Mapping[str, Any] | None = None,
        return_clause: Optional[str] = None,
    ) -> ScopedQuery:
        """Build a tenant-scoped node ``MERGE`` query.

        ``tenant_id`` is always part of the merge identity so same-id records in
        different tenants cannot collapse into the same node.
        """
        identity_props = dict(identity)
        identity_props[self._tenant_property] = self._tenant_id
        params: Dict[str, Any] = {}
        identity_pairs = []
        for key, value in identity_props.items():
            param_key = f"_{alias}_identity_{key}"
            params[param_key] = value
            identity_pairs.append(f"{key}: ${param_key}")

        lines = [f"MERGE ({alias}:{label} {{{', '.join(identity_pairs)}}})"]
        if on_create_props:
            create_parts = []
            for key, value in on_create_props.items():
                param_key = f"_{alias}_create_{key}"
                params[param_key] = value
                create_parts.append(f"{alias}.{key} = ${param_key}")
            lines.append(f"ON CREATE SET {', '.join(create_parts)}")
        if set_props:
            set_parts = []
            for key, value in set_props.items():
                param_key = f"_{alias}_set_{key}"
                params[param_key] = value
                set_parts.append(f"{alias}.{key} = ${param_key}")
            lines.append(f"SET {', '.join(set_parts)}")
        lines.append(f"RETURN {return_clause or alias}")
        return self._query("\n".join(lines), params, operation="merge_node", labels=(label,))

    def update_node_query(
        self,
        alias: str,
        label: str,
        identity_where: str,
        set_props: Mapping[str, Any],
        *,
        extra_params: Mapping[str, Any] | None = None,
        return_clause: Optional[str] = None,
    ) -> ScopedQuery:
        """Build a tenant-scoped node update query."""
        params = self._params(extra_params)
        set_parts = []
        for key, value in set_props.items():
            param_key = f"_{alias}_set_{key}"
            params[param_key] = value
            set_parts.append(f"{alias}.{key} = ${param_key}")
        cypher = (
            f"MATCH ({alias}:{label})\n"
            f"WHERE {self._tenant_predicate(alias)} AND ({identity_where})\n"
            f"SET {', '.join(set_parts)}\n"
            f"RETURN {return_clause or alias}"
        )
        return self._query(cypher, params, operation="update_node", labels=(label,))

    def delete_node_query(
        self,
        alias: str,
        label: str,
        identity_where: str,
        *,
        extra_params: Mapping[str, Any] | None = None,
        detach: bool = False,
    ) -> ScopedQuery:
        """Build a tenant-scoped node delete query."""
        params = self._params(extra_params)
        delete_keyword = "DETACH DELETE" if detach else "DELETE"
        cypher = (
            f"MATCH ({alias}:{label})\n"
            f"WHERE {self._tenant_predicate(alias)} AND ({identity_where})\n"
            f"{delete_keyword} {alias}"
        )
        return self._query(cypher, params, operation="delete_node", labels=(label,))

    # -- Relationship queries ------------------------------------------------

    def match_relationship_query(
        self,
        from_alias: str,
        from_label: str,
        rel_type: str,
        to_alias: str,
        to_label: str,
        *,
        rel_alias: str | None = None,
        extra_where: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        return_clause: Optional[str] = None,
        optional: bool = False,
        direction: str = "out",
    ) -> ScopedQuery:
        """Build a relationship match where both endpoints belong to tenant."""
        params = self._params(extra_params)
        rel = f"[{rel_alias or ''}:{rel_type}]"
        if direction == "in":
            pattern = f"({from_alias}:{from_label})<-{rel}-({to_alias}:{to_label})"
        elif direction == "both":
            pattern = f"({from_alias}:{from_label})-{rel}-({to_alias}:{to_label})"
        else:
            pattern = f"({from_alias}:{from_label})-{rel}->({to_alias}:{to_label})"
        match_keyword = "OPTIONAL MATCH" if optional else "MATCH"
        ret = return_clause or f"{from_alias}, {to_alias}"
        cypher = (
            f"{match_keyword} {pattern}\n"
            f"WHERE {self.tenant_scoped_where(from_alias)} AND {self.tenant_scoped_where(to_alias, extra_where)}\n"
            f"RETURN {ret}"
        )
        return self._query(
            cypher,
            params,
            operation="match_relationship",
            labels=(from_label, to_label),
        )

    def match_relationship(
        self,
        from_alias: str,
        from_label: str,
        rel_type: str,
        to_alias: str,
        to_label: str,
        *,
        extra_where: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        return_clause: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """MATCH a relationship where both endpoints belong to the tenant."""
        return self.match_relationship_query(
            from_alias,
            from_label,
            rel_type,
            to_alias,
            to_label,
            extra_where=extra_where,
            extra_params=extra_params,
            return_clause=return_clause,
        ).as_tuple()

    def merge_relationship_query(
        self,
        from_alias: str,
        from_label: str,
        from_identity_where: str,
        rel_type: str,
        to_alias: str,
        to_label: str,
        to_identity_where: str,
        *,
        rel_props: Mapping[str, Any] | None = None,
        extra_params: Mapping[str, Any] | None = None,
        return_clause: Optional[str] = None,
    ) -> ScopedQuery:
        """Build a tenant-scoped relationship ``MERGE`` query.

        Both endpoint matches are tenant-filtered before the relationship is
        merged, preventing cross-tenant relationship creation.
        """
        params = self._params(extra_params)
        prop_clause = ""
        if rel_props:
            rel_params = []
            for key, value in rel_props.items():
                param_key = f"_rel_{key}"
                params[param_key] = value
                rel_params.append(f"{key}: ${param_key}")
            prop_clause = " {" + ", ".join(rel_params) + "}"
        cypher = (
            f"MATCH ({from_alias}:{from_label})\n"
            f"WHERE {self._tenant_predicate(from_alias)} AND ({from_identity_where})\n"
            f"MATCH ({to_alias}:{to_label})\n"
            f"WHERE {self._tenant_predicate(to_alias)} AND ({to_identity_where})\n"
            f"MERGE ({from_alias})-[r:{rel_type}{prop_clause}]->({to_alias})\n"
            f"RETURN {return_clause or f'{from_alias}, r, {to_alias}'}"
        )
        return self._query(
            cypher,
            params,
            operation="merge_relationship",
            labels=(from_label, to_label),
        )

    # -- Custom scoped queries ------------------------------------------------

    def custom_tenant_query(
        self,
        cypher: str,
        *,
        params: Mapping[str, Any] | None = None,
        operation: str = "custom_tenant_query",
        labels: Sequence[str] = (),
        allowlist_key: str | None = None,
    ) -> ScopedQuery:
        """Wrap a complex tenant-scoped Cypher query with strict metadata.

        This is the escape hatch for analytical queries that are too complex for
        the small builder helpers above, but it remains fail-closed: the query
        must reference the canonical tenant parameter and must include an
        explicit tenant predicate compatible with the configured tenant property.
        """
        if "$_tenant_id" not in cypher and "$tenant_id" not in cypher:
            raise ValueError("custom tenant queries must reference a tenant parameter")
        tenant_predicate = f".{self._tenant_property}"
        if tenant_predicate not in cypher and ".tenantId" not in cypher:
            raise ValueError("custom tenant queries must include an explicit tenant predicate")
        # nosemgrep: python.fastapi.db.generic-sql-fastapi.generic-sql-fastapi
        # Cypher query wrapper: callers pass internally-controlled Cypher and tenant predicates are validated.
        scoped = self._query(
            cypher,
            self._params(params),
            operation=operation,
            labels=labels,
        )
        if allowlist_key is None:
            return scoped
        if not allowlist_key.strip():
            raise ValueError("tenant custom query allowlist_key must be non-empty when provided")
        return ScopedQuery(
            cypher=scoped.cypher,
            params=scoped.params,
            scope=scoped.scope,
            tenant_id=scoped.tenant_id,
            operation=scoped.operation,
            labels=scoped.labels,
            reason=scoped.reason,
            allowlist_key=allowlist_key,
        )

    # -- Procedure wrappers --------------------------------------------------

    def fulltext_query_nodes_query(
        self,
        index_name: str,
        query_param_name: str = "query",
        *,
        node_alias: str = "node",
        score_alias: str = "score",
        where: str | None = None,
        params: Mapping[str, Any] | None = None,
        return_clause: str | None = None,
        limit: int | None = None,
    ) -> ScopedQuery:
        """Build a tenant-post-filtered full-text index query."""
        all_params = self._params(params)
        all_params["_index_name"] = index_name
        lines = [
            f"CALL db.index.fulltext.queryNodes($_index_name, ${query_param_name}) "
            f"YIELD node AS {node_alias}, score AS {score_alias}",
            f"WHERE {self.tenant_scoped_where(node_alias, where)}",
            f"RETURN {return_clause or f'{node_alias}, {score_alias}'}",
        ]
        if limit is not None:
            all_params["_limit"] = limit
            lines.append("LIMIT $_limit")
        return self._query(
            "\n".join(lines),
            all_params,
            operation="fulltext_query_nodes",
            labels=("*",),
        )


# ---------------------------------------------------------------------------
# Redis cache key namespacing
# ---------------------------------------------------------------------------


def tenant_cache_key(tenant_id: UUID, *parts: str) -> str:
    """Return a Redis key prefixed with the tenant UUID.

    Example::

        key = tenant_cache_key(ctx.tenant_id, "search", query_hash)
        # → "tenant:3fa85f64-...:search:abc123"

    This ensures keys from different tenants never collide even if the
    underlying Redis instance is shared.
    """
    safe_parts = ":".join(p.replace(":", "_") for p in parts if p)
    return f"tenant:{tenant_id}:{safe_parts}"
