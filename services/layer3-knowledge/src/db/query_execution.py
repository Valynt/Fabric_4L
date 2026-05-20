"""Approved Neo4j execution surface for Layer 3 runtime modules.

Runtime code in ``services/layer3-knowledge/src`` must not call
``session.run(...)`` directly for tenant-owned graph data. All non-schema,
non-migration execution should enter Neo4j through one of these wrappers:

* ``run_scoped_query(session, scoped_query)`` for queries produced by
  ``TenantScopedCypher`` / ``SystemCypher``. Tenant scoped queries require a
  tenant id on the ``ScopedQuery`` and force it into both ``tenant_id`` and
  ``_tenant_id`` parameters before execution.
* ``run_validated_query(session, query, parameters, tenant_id=...)`` for legacy
  modules that are still migrating to strict ``ScopedQuery`` builders. This
  wrapper performs fail-closed structural validation for tenant-owned labels and
  force-assigns the provided execution tenant over caller-supplied parameters.

Only schema, bootstrap, and migration code paths may remain explicit
system-scoped allowlist entries; this execution module is the wrapper boundary.
High-risk runtime folders (``api/routes``, ``services``, ``agents``, and
``analytics``) are statically guarded so direct Neo4j ``run(...)`` calls fail CI
unless they are moved behind this boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery

SYSTEM_SCOPES = {QueryScope.SYSTEM, QueryScope.SCHEMA, QueryScope.MIGRATION, QueryScope.BACKUP}


class TenantQueryValidationError(ValueError):
    """Raised when Cypher execution violates tenant isolation requirements."""


_FALLBACK_TENANT_OWNED_LABELS = {
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
    "Contact",
    "Competitor",
    "Customer",
    "DecisionStep",
    "DecisionTrace",
    "Document",
    "Entity",
    "Evidence",
    "Feature",
    "Formula",
    "FormulaVersion",
    "Industry",
    "Insight",
    "Model",
    "Opportunity",
    "Outcome",
    "PROVEntity",
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


def _load_tenant_owned_labels() -> set[str]:
    """Load tenant-owned labels from the shared registry with a local fallback."""

    try:
        from value_fabric.shared.identity.isolation import DEFAULT_TENANT_LABEL_POLICY

        return set(DEFAULT_TENANT_LABEL_POLICY.tenant_labels)
    except Exception:
        return set(_FALLBACK_TENANT_OWNED_LABELS)


_TENANT_OWNED_LABELS = _load_tenant_owned_labels()
_CLAUSE_KEYWORD_PATTERN = re.compile(r"\b(MATCH|OPTIONAL\s+MATCH|MERGE|CREATE)\b", re.IGNORECASE)
_TENANT_LABEL_PATTERN = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_][A-Za-z0-9_]*)?\s*:\s*"
    r"(?P<label>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*:\s*[A-Za-z_][A-Za-z0-9_]*)*\s*"
    r"(?P<props>\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*)?",
    re.DOTALL,
)
_TENANT_PREDICATE_PATTERN = re.compile(
    r"(?i)\b(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\.tenant_id\s*(?:=|IN)\s*[$A-Za-z_]"
)
_CLAUSE_PATTERN = re.compile(r"\b(MATCH|OPTIONAL\s+MATCH|CALL\s*\{|UNION(?:\s+ALL)?|WITH)\b", re.IGNORECASE)


def _tenant_scoped_aliases(query: str) -> set[str]:
    return {match.group("alias") for match in _TENANT_PREDICATE_PATTERN.finditer(query)}


def _parameter_map_has_tenant_id(prop_token: str, params: Mapping[str, Any]) -> bool:
    """Return True when a dynamic Cypher property map parameter carries tenant_id."""

    param_name = prop_token[1:]
    value = params.get(param_name)
    return isinstance(value, Mapping) and "tenant_id" in value


def _structural_tenant_scope_errors(query: str, params: Mapping[str, Any]) -> list[str]:
    scoped_aliases = _tenant_scoped_aliases(query)
    errors: list[str] = []

    for match in _TENANT_LABEL_PATTERN.finditer(query):
        label = match.group("label")
        if label not in _TENANT_OWNED_LABELS:
            continue

        alias = (match.group("alias") or "").strip()
        prop_token = (match.group("props") or "").strip()
        has_tenant_in_props = bool(re.search(r"(?i)\btenant_id\b", prop_token))
        has_tenant_param_map = prop_token.startswith("$") and _parameter_map_has_tenant_id(prop_token, params)
        has_tenant_predicate = bool(alias) and alias in scoped_aliases

        if not (has_tenant_in_props or has_tenant_param_map or has_tenant_predicate):
            errors.append(f"{label}({alias or '?'})")

    return errors


def _touches_tenant_owned_label(query: str) -> bool:
    return any(match.group("label") in _TENANT_OWNED_LABELS for match in _TENANT_LABEL_PATTERN.finditer(query))


@dataclass(frozen=True)
class TenantExecutionContext:
    tenant_id: str | None
    is_bypass: bool = False
    allow_system_query: bool = False
    allow_multi_clause_tenant_query: bool = False


class TenantQueryExecutor:
    """Single query execution wrapper for tenant-scoped Cypher."""

    @classmethod
    async def run(
        cls,
        run_callable,
        query: str,
        parameters: dict[str, Any] | None,
        context: TenantExecutionContext,
    ) -> Any:
        params = dict(parameters or {})
        if context.tenant_id:
            params["tenant_id"] = context.tenant_id
            params["_tenant_id"] = context.tenant_id

        cls._validate(query=query, params=params, context=context)
        return await run_callable(query, params)

    @classmethod
    def _validate(cls, query: str, params: Mapping[str, Any], context: TenantExecutionContext) -> None:
        if context.is_bypass:
            return

        touches_tenant_data = _touches_tenant_owned_label(query)
        if touches_tenant_data and not context.tenant_id and not context.allow_system_query:
            raise TenantQueryValidationError("Tenant context is required for tenant-owned Cypher execution")

        structural_errors = _structural_tenant_scope_errors(query, params) if touches_tenant_data else []
        if structural_errors and not context.allow_system_query:
            details = ", ".join(structural_errors)
            raise TenantQueryValidationError(
                f"Denied Cypher query due to missing tenant scoping in tenant-owned path: {details}"
            )

        if _CLAUSE_KEYWORD_PATTERN.search(query):
            clause_tokens = [m.group(1).upper() for m in _CLAUSE_PATTERN.finditer(query)]
            ambiguous = (
                clause_tokens.count("MATCH") + clause_tokens.count("OPTIONAL MATCH") > 1
                or any(token.startswith("UNION") for token in clause_tokens)
                or bool(re.search(r"(?is)\bCALL\s*\{", query))
            )
            if ambiguous and not context.allow_system_query:
                if context.allow_multi_clause_tenant_query:
                    # Legacy high-risk modules may execute multi-clause templates only
                    # after every tenant-owned label has an explicit tenant predicate.
                    return
                raise TenantQueryValidationError(
                    "Denied ambiguous or multi-clause Cypher; only allowlisted system queries or "
                    "validated legacy runtime wrappers may opt in"
                )


def _resolve_runner(session_or_run_callable):
    if callable(session_or_run_callable) and not hasattr(session_or_run_callable, "run"):
        return session_or_run_callable
    runner = getattr(session_or_run_callable, "run", None)
    if runner is None:
        raise TypeError("Expected a Neo4j session-like object or async run callable")
    return runner


async def run_scoped_query(
    session_or_run_callable,
    scoped_query: ScopedQuery,
    *,
    is_bypass: bool = False,
) -> Any:
    """Execute a builder-produced ``ScopedQuery`` through the approved gateway.

    ``ScopedQuery`` is the preferred API for new Layer 3 code because its scope,
    tenant id, operation name, and touched labels are carried alongside the query
    text. Tenant scoped queries inject ``tenant_id`` / ``_tenant_id`` at runtime;
    system, schema, migration, backup, and health scopes may execute without a
    tenant only when their ``QueryScope`` explicitly declares that intent.
    """

    if scoped_query.scope == QueryScope.TENANT and not scoped_query.tenant_id and not is_bypass:
        raise TenantQueryValidationError("Tenant context is required for tenant-scoped Cypher execution")

    allow_system_query = scoped_query.scope != QueryScope.TENANT
    context = TenantExecutionContext(
        tenant_id=scoped_query.tenant_id,
        is_bypass=is_bypass,
        allow_system_query=allow_system_query,
    )
    return await TenantQueryExecutor.run(
        _resolve_runner(session_or_run_callable),
        scoped_query.cypher,
        scoped_query.params,
        context=context,
    )


async def run_validated_query(
    session_or_run_callable,
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    tenant_id: str | None = None,
    allow_system_query: bool = False,
    is_bypass: bool = False,
    query_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute legacy Cypher through fail-closed tenant validation.

    This compatibility wrapper is the approved temporary surface for migrated
    high-risk runtime modules that still hold raw Cypher strings. It merges
    positional and keyword parameters, derives the tenant from the explicit
    ``tenant_id`` argument or existing ``tenant_id`` / ``_tenant_id`` parameters,
    and rejects any tenant-owned label query missing explicit tenant predicates
    before delegating to the Neo4j session.
    """

    params = dict(parameters or {})
    params.update(kwargs)
    resolved_tenant_id = tenant_id or params.get("tenant_id") or params.get("_tenant_id")
    context = TenantExecutionContext(
        tenant_id=str(resolved_tenant_id) if resolved_tenant_id else None,
        is_bypass=is_bypass,
        allow_system_query=allow_system_query,
        allow_multi_clause_tenant_query=True,
    )
    try:
        return await TenantQueryExecutor.run(_resolve_runner(session_or_run_callable), query, params, context=context)
    except TenantQueryValidationError as exc:
        name = f" '{query_name}'" if query_name else ""
        raise TenantQueryValidationError(f"Denied Cypher query{name}: {exc}") from exc


async def run_tenant_query(
    session_or_run_callable,
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    tenant_id: str,
    is_bypass: bool = False,
    query_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an explicitly tenant-scoped ad-hoc Cypher query."""

    return await run_validated_query(
        session_or_run_callable,
        query,
        parameters,
        tenant_id=tenant_id,
        is_bypass=is_bypass,
        query_name=query_name,
        **kwargs,
    )


async def run_system_query(
    session_or_run_callable,
    query: str,
    parameters: dict[str, Any] | None = None,
    *,
    scope: QueryScope = QueryScope.SYSTEM,
    query_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an explicitly system-scoped Cypher query through the same gateway."""

    if scope not in SYSTEM_SCOPES:
        raise TenantQueryValidationError(f"Unsupported system scope: {scope}")

    return await run_validated_query(
        session_or_run_callable,
        query,
        parameters,
        allow_system_query=True,
        query_name=query_name,
        **kwargs,
    )
