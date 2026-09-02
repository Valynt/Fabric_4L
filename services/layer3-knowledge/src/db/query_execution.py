from __future__ import annotations

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


import asyncio
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery

from src.graph.query_guards import (
    DEFAULT_MAX_QUERY_DEPTH,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    sanitize_query_depth,
    sanitize_query_timeout_seconds,
)
from src.utils.cypher_security import TENANT_OWNED_LABELS

try:
    from metrics.prometheus_metrics import get_metrics
except Exception:
    get_metrics = None  # type: ignore[assignment]

SYSTEM_SCOPES = {
    QueryScope.SYSTEM,
    QueryScope.SCHEMA,
    QueryScope.MIGRATION,
    QueryScope.BACKUP,
}

# Backward-compatible aliases for existing imports.
MAX_QUERY_DEPTH = DEFAULT_MAX_QUERY_DEPTH
QUERY_TIMEOUT_SECONDS = DEFAULT_QUERY_TIMEOUT_SECONDS


class TenantQueryValidationError(ValueError):
    """Raised when Cypher execution violates tenant isolation requirements."""

    def __init__(
        self, message: str, *, code: str = "TENANT_QUERY_VALIDATION_ERROR"
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class CypherDepthLimitExceeded(TenantQueryValidationError):
    """Raised when a Cypher query exceeds the maximum allowed traversal depth."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DEPTH_LIMIT_EXCEEDED")


class CypherInjectionDetected(TenantQueryValidationError):
    """Raised when unsafe Cypher injection or statement chaining is detected."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CYPHER_INJECTION_DETECTED")


class TenantParameterMismatchError(TenantQueryValidationError):
    """Raised when parameters contradict the authenticated tenant execution context."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="TENANT_PARAM_MISMATCH")


class UnscopedTenantLabelError(TenantQueryValidationError):
    """Raised when a tenant-owned label lacks proper tenant filtering."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="UNSCOPED_TENANT_LABEL")


class DirectMutationProhibitedError(TenantQueryValidationError):
    """Raised when direct CREATE/MERGE/DELETE is attempted on tenant-owned labels."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DIRECT_MUTATION_PROHIBITED")


class DangerousProcedureBlockedError(TenantQueryValidationError):
    """Raised when dangerous/admin Neo4j or APOC procedures are called."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DANGEROUS_PROCEDURE_BLOCKED")


class MissingTenantContextError(TenantQueryValidationError):
    """Raised when tenant context is required but missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="MISSING_TENANT_CONTEXT")


_CLAUSE_KEYWORD_PATTERN = re.compile(
    r"\b(MATCH|OPTIONAL\s+MATCH|MERGE|CREATE)\b", re.IGNORECASE
)
# Matches variable-length path patterns like [*1..4], [*..5], [*1..], [*3], [*$depth], [*1..$max_depth]
_VAR_LENGTH_PATH_PATTERN = re.compile(
    r"\[\s*(?:[:!]?\s*[A-Za-z_][A-Za-z0-9_]*\s*\|?\s*)*\*\s*([^]]*?)\s*\]",
    re.IGNORECASE,
)
_TENANT_LABEL_PATTERN = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_][A-Za-z0-9_]*)?\s*:\s*"
    r"(?P<label>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*:\s*[A-Za-z_][A-Za-z0-9_]*)*\s*"
    r"(?P<props>\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*)?",
    re.DOTALL,
)
_TENANT_PREDICATE_PATTERN = re.compile(
    r"(?i)\b(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\.tenant_id\s*(?:=|IN)\s*(?P<param>\$[A-Za-z_][A-Za-z0-9_]*)?"
)
_CLAUSE_PATTERN = re.compile(
    r"\b(MATCH|OPTIONAL\s+MATCH|CALL\s*\{|UNION(?:\s+ALL)?|WITH)\b", re.IGNORECASE
)
_DANGEROUS_PROCEDURE_PATTERN = re.compile(
    r"(?is)\bCALL\s+(?:dbms\.|apoc\.(?:export|import|load|custom|system|util\.sleep|config))\b"
)
# Literal patterns used on the tenant-owned query hot path; hoisted to module
# constants so they are compiled once instead of per-query.
_TENANT_ID_REFERENCE_PATTERN = re.compile(r"(?i)\btenant_id\b")
_TENANT_MUTATION_KEYWORD_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH\s+DELETE)\b", re.IGNORECASE
)
_ANONYMOUS_CALL_PATTERN = re.compile(r"(?is)\bCALL\s*\{")


def _skip_quoted(query: str, i: int, n: int, quote: str, allow_escape: bool) -> int:
    """Consume a quoted body starting just after the opening quote.

    Returns the index just past the closing quote (or the end of the string).
    """
    i += 1
    while i < n:
        c = query[i]
        if allow_escape and c == "\\" and i + 1 < n:
            i += 2
            continue
        i += 1
        if c == quote:
            break
    return i


def _skip_line_comment(query: str, i: int, n: int) -> int:
    """Skip a line comment, returning just past the newline (or end of query)."""
    while i < n and query[i] != "\n":
        i += 1
    if i < n:
        i += 1
    return i


def _skip_block_comment(query: str, i: int, n: int) -> int:
    """Skip a block comment, returning just past the closing ``*/``."""
    while i < n:
        if query[i] == "*" and i + 1 < n and query[i + 1] == "/":
            return i + 2
        i += 1
    return i


def _has_trailing_content(query: str, start: int) -> bool:
    """True when a semicolon is followed by a second statement, not just comments."""
    rest = query[start:]
    cleaned = re.sub(r"//[^\n]*", "", rest)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace(";", "").strip()
    return bool(cleaned)


def _has_multiple_statements(query: str) -> bool:
    """Return True if query contains unquoted semicolons separating multiple statements."""
    i = 0
    n = len(query)
    while i < n:
        c = query[i]
        if c == "'":
            i = _skip_quoted(query, i, n, "'", True)
            continue
        if c == '"':
            i = _skip_quoted(query, i, n, '"', True)
            continue
        if c == "`":
            i = _skip_quoted(query, i, n, "`", False)
            continue
        if c == "/" and i + 1 < n:
            if query[i + 1] == "/":
                i = _skip_line_comment(query, i + 2, n)
                continue
            if query[i + 1] == "*":
                i = _skip_block_comment(query, i + 2, n)
                continue
        if c == ";":
            if _has_trailing_content(query, i + 1):
                return True
        i += 1
    return False


def _tenant_scoped_aliases(query: str) -> set[str]:
    return {match.group("alias") for match in _TENANT_PREDICATE_PATTERN.finditer(query)}


def _parameter_map_has_tenant_id(
    prop_token: str,
    params: Mapping[str, Any],
    context_tenant_id: str | None = None,
) -> bool:
    """Return True when a dynamic Cypher property map parameter carries tenant_id."""

    param_name = prop_token[1:]
    value = params.get(param_name)
    if not isinstance(value, Mapping) or "tenant_id" not in value:
        return False
    if context_tenant_id and str(value.get("tenant_id")) != context_tenant_id:
        raise TenantParameterMismatchError(
            f"Property map parameter ${param_name} carries tenant_id {value.get('tenant_id')!r} "
            f"which contradicts execution tenant {context_tenant_id!r}"
        )
    return True


def _structural_tenant_scope_errors(
    query: str,
    params: Mapping[str, Any],
    context_tenant_id: str | None = None,
) -> list[str]:
    scoped_aliases = _tenant_scoped_aliases(query)
    errors: list[str] = []

    for match in _TENANT_LABEL_PATTERN.finditer(query):
        label = match.group("label")
        if label not in TENANT_OWNED_LABELS:
            continue

        alias = (match.group("alias") or "").strip()
        prop_token = (match.group("props") or "").strip()
        has_tenant_in_props = bool(_TENANT_ID_REFERENCE_PATTERN.search(prop_token))
        has_tenant_param_map = prop_token.startswith(
            "$"
        ) and _parameter_map_has_tenant_id(prop_token, params, context_tenant_id)
        has_tenant_predicate = bool(alias) and alias in scoped_aliases

        if not (has_tenant_in_props or has_tenant_param_map or has_tenant_predicate):
            errors.append(f"{label}({alias or '?'})")

    return errors


def _touches_tenant_owned_label(query: str) -> bool:
    return any(
        match.group("label") in TENANT_OWNED_LABELS
        for match in _TENANT_LABEL_PATTERN.finditer(query)
    )


@dataclass(frozen=True)
class TenantExecutionContext:
    tenant_id: str | None
    is_bypass: bool = False
    allow_system_query: bool = False
    allow_multi_clause_tenant_query: bool = False


class TenantQueryExecutor:
    """Single query execution wrapper for tenant-scoped Cypher."""

    @classmethod
    def _extract_max_depth(cls, query: str, params: Mapping[str, Any]) -> int | None:
        """Return the largest explicit depth bound found in variable-length paths."""
        max_depth: int | None = None
        for match in _VAR_LENGTH_PATH_PATTERN.finditer(query):
            inner = match.group(1)
            if not inner:
                continue
            # Parse patterns like: "1..4", "..5", "1..", "3", "$depth", "1..$max_depth"
            parts = inner.split("..")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                depth: int | None = None
                if part.startswith("$"):
                    param_name = part[1:]
                    raw = params.get(param_name)
                    if isinstance(raw, int):
                        depth = raw
                else:
                    try:
                        depth = int(part)
                    except ValueError:
                        continue
                if depth is not None and (max_depth is None or depth > max_depth):
                    max_depth = depth
        return max_depth

    @classmethod
    def _record_query_metrics(cls, elapsed: float, result: object) -> None:
        """Record execution metrics, result size, and slow query buckets."""
        metrics = get_metrics() if get_metrics else None
        if not metrics:
            return

        try:
            size = len(result)
        except Exception:
            try:
                size = len(result.records)
            except Exception:
                size = 0
        metrics.observe_graph_result_size(
            size=size, endpoint="tenant_query_executor", operation="run"
        )

        if elapsed > 10.0:
            metrics.increment_graph_slow_queries(
                operation="run", threshold_bucket=">10s"
            )
        elif elapsed > 5.0:
            metrics.increment_graph_slow_queries(
                operation="run", threshold_bucket=">5s"
            )
        elif elapsed > 1.0:
            metrics.increment_graph_slow_queries(
                operation="run", threshold_bucket=">1s"
            )

    @classmethod
    async def _execute_with_timeout(
        cls,
        run_callable,
        query: str,
        params: dict[str, object],
    ) -> tuple[object, float]:
        """Execute query coroutine wrapped in timeout with failure metrics."""
        import time

        start = time.monotonic()
        coro = run_callable(query, params)
        try:
            result = await asyncio.wait_for(
                coro, timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS)
            )
        except TimeoutError:
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_graph_query_failure(
                    category="timeout", operation="run", route="tenant_query_executor"
                )
            raise
        except Exception:
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_graph_query_failure(
                    category="execution_error",
                    operation="run",
                    route="tenant_query_executor",
                )
            raise

        elapsed = time.monotonic() - start
        return result, elapsed

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

        result, elapsed = await cls._execute_with_timeout(run_callable, query, params)
        cls._record_query_metrics(elapsed, result)
        return result

    @classmethod
    def _validate(
        cls, query: str, params: Mapping[str, Any], context: TenantExecutionContext
    ) -> None:
        if context.is_bypass:
            return
        cls._guard_injection(query, context)
        cls._guard_direct_mutation(query, context)
        cls._guard_depth_limit(query, cls._extract_max_depth(query, params), context)
        cls._guard_tenant_context(query, context)
        cls._guard_parameters(query, params, context)
        cls._guard_structural_scoping(
            query,
            (
                _structural_tenant_scope_errors(query, params, context.tenant_id)
                if _touches_tenant_owned_label(query)
                else []
            ),
            context,
        )
        cls._guard_multi_clause(query, context)

    @classmethod
    def _guard_injection(cls, query: str, context: TenantExecutionContext) -> None:
        """Reject statement splitting/chaining and dangerous unapproved procedures."""
        if _has_multiple_statements(query):
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_tenant_isolation_violation(
                    component="query_execution", violation_type="cypher_injection"
                )
            raise CypherInjectionDetected(
                "Multiple Cypher statements or unquoted semicolons detected in a single execution call"
            )

        if (
            _DANGEROUS_PROCEDURE_PATTERN.search(query)
            and not context.allow_system_query
        ):
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_tenant_isolation_violation(
                    component="query_execution", violation_type="restricted_procedure"
                )
            raise DangerousProcedureBlockedError(
                "Execution of restricted Neo4j/APOC system procedures is blocked"
            )

    @classmethod
    def _guard_parameters(
        cls, query: str, params: Mapping[str, Any], context: TenantExecutionContext
    ) -> None:
        """Validate that all tenant-related parameters match the authenticated execution tenant."""
        if not context.tenant_id:
            return

        expected_tenant = context.tenant_id

        def _check_nested(obj: Any, path: str = "") -> None:
            if isinstance(obj, Mapping):
                for k, v in obj.items():
                    current_path = f"{path}.{k}" if path else str(k)
                    if k in {"tenant_id", "tenantId", "_tenant_id"}:
                        if isinstance(v, (list, tuple, set)):
                            if not all(str(item) == expected_tenant for item in v):
                                raise TenantParameterMismatchError(
                                    f"Parameter '{current_path}' contains tenant IDs outside execution context {expected_tenant!r}"
                                )
                        elif v is not None and str(v) != expected_tenant:
                            raise TenantParameterMismatchError(
                                f"Parameter '{current_path}' value {v!r} does not match execution tenant {expected_tenant!r}"
                            )
                    _check_nested(v, current_path)
            elif isinstance(obj, (list, tuple, set)):
                for idx, item in enumerate(obj):
                    _check_nested(item, f"{path}[{idx}]")

        _check_nested(params)

        for match in _TENANT_PREDICATE_PATTERN.finditer(query):
            param_token = match.group("param")
            if param_token and param_token.startswith("$"):
                param_name = param_token[1:]
                if param_name in params:
                    val = params[param_name]
                    if isinstance(val, (list, tuple, set)):
                        if not all(str(item) == expected_tenant for item in val):
                            raise TenantParameterMismatchError(
                                f"Tenant predicate parameter '${param_name}' contains values outside execution tenant {expected_tenant!r}"
                            )
                    elif val is not None and str(val) != expected_tenant:
                        raise TenantParameterMismatchError(
                            f"Tenant predicate parameter '${param_name}' value {val!r} does not match execution tenant {expected_tenant!r}"
                        )

    @classmethod
    def _guard_direct_mutation(
        cls, query: str, context: TenantExecutionContext
    ) -> None:
        """Phase 1 hardening: block direct CREATE/MERGE/DELETE on tenant-owned labels.  # cypher-mutation-safe: docstring

        These must go through AuditedGraphMutation for audit trail.
        """
        if _TENANT_MUTATION_KEYWORD_PATTERN.search(
            query
        ) and _touches_tenant_owned_label(query):
            if not context.allow_system_query:
                metrics = get_metrics() if get_metrics else None
                if metrics:
                    metrics.increment_tenant_isolation_violation(
                        component="query_execution",
                        violation_type="direct_mutation_bypass",
                    )
                    metrics.increment_unauthorized_traversal(
                        category="mutation_bypass",
                        route="tenant_query_executor",
                        violation_type="direct_mutation_bypass",
                    )
                raise DirectMutationProhibitedError(
                    "Direct CREATE/MERGE/DELETE on tenant-owned labels is prohibited. "  # cypher-mutation-safe: error message
                    "Use AuditedGraphMutation.write_relationship(), write_node(), delete_relationship(), or delete_node() instead. "
                    "This ensures audit trail and metrics collection for all graph mutations."
                )

    @classmethod
    def _guard_depth_limit(
        cls, query: str, max_depth: int | None, context: TenantExecutionContext
    ) -> None:
        """Enforce the traversal depth limit (PERF-001)."""
        safe_max_depth = sanitize_query_depth(
            MAX_QUERY_DEPTH, default_depth=MAX_QUERY_DEPTH
        )
        if max_depth is not None and max_depth > safe_max_depth:
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.observe_graph_traversal_depth(
                    depth=max_depth,
                    endpoint="tenant_query_executor",
                    operation="validate",
                )
                metrics.increment_unauthorized_traversal(
                    category="depth_limit",
                    route="tenant_query_executor",
                    violation_type="depth_exceeded",
                )
            raise CypherDepthLimitExceeded(
                f"Query exceeds maximum depth of {safe_max_depth} (found {max_depth})"
            )

    @classmethod
    def _guard_tenant_context(cls, query: str, context: TenantExecutionContext) -> None:
        """Require a tenant id whenever a tenant-owned label is touched."""
        if (
            _touches_tenant_owned_label(query)
            and not context.tenant_id
            and not context.allow_system_query
        ):
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_tenant_isolation_violation(
                    component="query_execution", violation_type="missing_tenant_context"
                )
                metrics.increment_unauthorized_traversal(
                    category="tenant_boundary",
                    route="tenant_query_executor",
                    violation_type="missing_tenant_context",
                )
            raise MissingTenantContextError(
                "Tenant context is required for tenant-owned Cypher execution"
            )

    @classmethod
    def _guard_structural_scoping(
        cls, query: str, structural_errors: list[str], context: TenantExecutionContext
    ) -> None:
        """Reject tenant-owned label queries missing explicit tenant predicates."""
        if structural_errors and not context.allow_system_query:
            metrics = get_metrics() if get_metrics else None
            if metrics:
                metrics.increment_tenant_isolation_violation(
                    component="query_execution", violation_type="structural_scope"
                )
            details = ", ".join(structural_errors)
            raise UnscopedTenantLabelError(
                f"Denied Cypher query due to missing tenant scoping in tenant-owned path: {details}"
            )

    @classmethod
    def _guard_multi_clause(cls, query: str, context: TenantExecutionContext) -> None:
        """Reject ambiguous/multi-clause tenant-owned Cypher outside allowlisted wrappers."""
        if not _CLAUSE_KEYWORD_PATTERN.search(query):
            return
        clause_tokens = [m.group(1).upper() for m in _CLAUSE_PATTERN.finditer(query)]
        ambiguous = (
            clause_tokens.count("MATCH") + clause_tokens.count("OPTIONAL MATCH") > 1
            or any(token.startswith("UNION") for token in clause_tokens)
            or bool(_ANONYMOUS_CALL_PATTERN.search(query))
        )
        if ambiguous and not context.allow_system_query:
            if context.allow_multi_clause_tenant_query:
                # Legacy high-risk modules may execute multi-clause templates only
                # after every tenant-labeled query has an explicit tenant predicate.
                return
            raise TenantQueryValidationError(
                "Denied ambiguous or multi-clause Cypher; only allowlisted system queries or "
                "validated legacy runtime wrappers may opt in",
                code="AMBIGUOUS_QUERY_BLOCKED",
            )


def _resolve_runner(session_or_run_callable):
    if callable(session_or_run_callable) and not hasattr(
        session_or_run_callable, "run"
    ):
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

    tenant_id = (
        scoped_query.tenant_id.strip()
        if isinstance(scoped_query.tenant_id, str) and scoped_query.tenant_id.strip()
        else None
    )

    if scoped_query.scope == QueryScope.TENANT and not tenant_id and not is_bypass:
        raise MissingTenantContextError(
            "Tenant context is required for tenant-scoped Cypher execution"
        )

    allow_system_query = scoped_query.scope != QueryScope.TENANT
    context = TenantExecutionContext(
        tenant_id=tenant_id,
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
    require_explicit_tenant_id: bool = True,
    **kwargs: Any,
) -> Any:
    """Execute legacy Cypher through fail-closed tenant validation.

    This compatibility wrapper is the approved temporary surface for migrated
    high-risk runtime modules that still hold raw Cypher strings. It merges
    positional and keyword parameters, derives the tenant from the explicit
    authenticated ``tenant_id`` argument, and rejects any tenant-owned label
    query missing explicit tenant predicates before delegating to the Neo4j
    session.

    ``require_explicit_tenant_id`` is retained as an explicit migration marker
    for call sites that have been audited. Parameter-derived tenant context is
    not accepted.
    """

    params = dict(parameters or {})
    params.update(kwargs)
    clean_tenant_id = (
        str(tenant_id).strip()
        if tenant_id is not None and str(tenant_id).strip()
        else None
    )
    context = TenantExecutionContext(
        tenant_id=clean_tenant_id,
        is_bypass=is_bypass,
        allow_system_query=allow_system_query,
        allow_multi_clause_tenant_query=True,
    )
    try:
        return await TenantQueryExecutor.run(
            _resolve_runner(session_or_run_callable), query, params, context=context
        )
    except TenantQueryValidationError as exc:
        name = f" '{query_name}'" if query_name else ""
        if isinstance(
            exc,
            (
                CypherDepthLimitExceeded,
                CypherInjectionDetected,
                TenantParameterMismatchError,
                UnscopedTenantLabelError,
                DirectMutationProhibitedError,
                DangerousProcedureBlockedError,
                MissingTenantContextError,
            ),
        ):
            raise
        raise TenantQueryValidationError(
            f"Denied Cypher query{name}: {exc}",
            code=getattr(exc, "code", "TENANT_QUERY_VALIDATION_ERROR"),
        ) from exc


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
