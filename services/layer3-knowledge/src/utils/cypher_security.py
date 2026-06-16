from __future__ import annotations

"""Centralised Cypher safety utilities for Layer 3 (GOV-L3-006).

Single source of truth for:

1. ``TENANT_OWNED_LABELS`` — the canonical set of Neo4j labels that carry
   tenant_id and must be filtered in every MATCH clause.

2. ``validate_tenant_scoped_cypher()`` — static regex validator used in tests
   and pre-execution checks to assert that a query template filters every
   tenant-owned label it touches.

3. ``ALLOWED_REL_TYPES`` / ``ALLOWED_TARGET_LABELS`` — allowlists for dynamic
   Cypher identifier interpolation in Value Pack relationship management.

4. ``validate_cypher_identifier()`` — runtime guard that rejects any label or
   relationship type not present in the supplied allowlist before it is
   interpolated into a Cypher string.

Import hierarchy
----------------
- ``db.query_execution`` imports ``TENANT_OWNED_LABELS`` from here as the
  canonical registry. No local fallback copy should be maintained.
- ``security.query_validator`` delegates static validation to
  ``validate_tenant_scoped_cypher`` and routes execution through
  ``db.query_execution.TenantQueryExecutor``.
- ``services.cypher_scope_guard`` re-exports ``validate_tenant_scoped_cypher``
  from here for backward compatibility.
- ``api.routes.value_packs`` imports the identifier allowlists from here.

Canonical execution path
------------------------
All tenant-owned Cypher must pass through ``db.query_execution.TenantQueryExecutor``
at runtime. This module provides the static validation and label registry that
``TenantQueryExecutor`` consumes.

Backward compatibility
----------------------
``services.cypher_scope_guard`` is preserved as a thin re-export shim so
existing callers (``product_service``, ``competitive_intel_service``) do not
need immediate updates. The shim will be removed once all callers are migrated.
"""


import re


class TenantCypherValidationError(ValueError):
    """Raised when a Cypher query fails tenant-scope validation."""


# ---------------------------------------------------------------------------
# Canonical tenant-owned label registry
# ---------------------------------------------------------------------------

TENANT_OWNED_LABELS: frozenset[str] = frozenset(
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
        "Contact",
        "Competitor",
        "Customer",
        "DecisionStep",
        "DecisionTrace",
        "Document",
        "Entity",
        "Evidence",
        "EconomicModel",
        "Feature",
        "Formula",
        "FormulaVersion",
        "Industry",
        "Insight",
        "Model",
        "Opportunity",
        "Outcome",
        "PackExecution",
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
        "SyncMetadata",
        "UseCase",
        "ValueDriver",
        "ValueLever",
        "ValueModel",
        "ValuePack",
        "ValueSignal",
        "ValueTree",
        "Variable",
        "Workflow",
    }
)

# ---------------------------------------------------------------------------
# Dynamic identifier allowlists (SEC-L3-CYPHER-003 / GOV-L3-006)
#
# These govern which Neo4j labels and relationship types may be interpolated
# directly into Cypher strings by approved audited mutation helpers.
# Labels and rel-types are not parameterisable in Cypher, so they must be
# validated against an explicit allowlist before interpolation.
#
# To add a new relationship: extend this set only after the relationship is
# accepted as a platform contract/schema type, and update the Semgrep rule
# comment in .semgrep/cypher-dynamic-guard.yml if its scope changes.
# ---------------------------------------------------------------------------

ALLOWED_REL_TYPES: frozenset[str] = frozenset(
    {
        "addresses",
        "belongsTo",
        "belongsToPack",
        "benefitsFrom",
        "contains",
        "delivers",
        "dependsOn",
        "drivenBy",
        "enables",
        "exhibits",
        "extractedFrom",
        "generatedBy",
        "HAS_DRIVER",
        "HAS_EXECUTION",
        "hasFeature",
        "hasDriver",
        "hasFormula",
        "hasBenchmark",
        "hasWorkflow",
        "HAS_FEATURE",
        "HAS_MODEL_TYPE",
        "HAS_USE_CASE",
        "implementedBy",
        "implements",
        "impacts",
        "involves",
        "mapsTo",
        "mapsToAPQC",
        "mapsToBIAN",
        "mapsToFIBO",
        "measuredBy",
        "measures",
        "operatesIn",
        "owns",
        "partOf",
        "performs",
        "provides",
        "quantifiedBy",
        "requires",
        "requiresFeature",
        "semanticallyEquivalent",
        "subTypeOf",
        "supportedBy",
        "SUPERSEDES",
        "supersedes",
        "usedIn",
        "validatedBy",
    }
)

ALLOWED_TARGET_LABELS: frozenset[str] = frozenset(
    {
        "ValueDriver",
        "Formula",
        "BenchmarkDataset",
        "Workflow",
    }
)


def validate_cypher_identifier(
    value: str,
    allowlist: frozenset[str],
    kind: str = "identifier",
) -> None:
    """Reject a Cypher label or relationship type not present in the allowlist.

    Args:
        value: The label or relationship type to validate.
        allowlist: The set of permitted values.
        kind: Human-readable name for the identifier type (used in the error).

    Raises:
        ValueError: If ``value`` is not in ``allowlist``.
    """
    if value not in allowlist:
        raise ValueError(
            f"Cypher injection guard: {kind} {value!r} is not in the allowlist. "
            f"Allowed: {sorted(allowlist)}"
        )


# ---------------------------------------------------------------------------
# Static query-template validator
# ---------------------------------------------------------------------------

_MATCH_CLAUSE_PATTERN = re.compile(
    r"(?is)\b(?:OPTIONAL\s+MATCH|MATCH)\b\s+"
    r"(.*?)(?=\bOPTIONAL\s+MATCH\b|\bMATCH\b|\bWITH\b|\bRETURN\b|\bUNWIND\b|\bCALL\b|\bORDER\s+BY\b|\bLIMIT\b|\bSKIP\b|$)"
)
_NODE_PATTERN = re.compile(
    r"\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*:\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s*:[^{)]+)?\s*(\{[^}]*)?"
)
_TENANT_PREDICATE_PATTERN = re.compile(
    r"(?i)\b(?P<alias>[A-Za-z_][A-Za-z0-9_]*)\.tenant_id\s*(?:=|IN)\s*[$A-Za-z_]"
)


def _tenant_scoped_aliases(query: str) -> set[str]:
    return {match.group("alias") for match in _TENANT_PREDICATE_PATTERN.finditer(query)}


def validate_tenant_scoped_cypher(
    query: str,
    *,
    tenant_owned_labels: set[str] | frozenset[str] | None = None,
    query_name: str = "query",
) -> None:
    """Reject MATCH templates that read tenant-owned labels without tenant_id scoping.

    The guard is intentionally static and conservative. It accepts tenant scope
    either inline in the node pattern, e.g. ``(p:Product {tenant_id: $tenant_id})``,
    or as a predicate elsewhere in the same query template, e.g.
    ``WHERE p.tenant_id = $tenant_id``.

    Args:
        query: Cypher query template string to validate.
        tenant_owned_labels: Labels to check. Defaults to ``TENANT_OWNED_LABELS``.
        query_name: Name used in the error message for diagnostics.

    Raises:
        ValueError: If any tenant-owned label is matched without a tenant_id filter.
    """
    labels = (
        tenant_owned_labels if tenant_owned_labels is not None else TENANT_OWNED_LABELS
    )
    scoped_aliases = _tenant_scoped_aliases(query)
    violations: list[str] = []

    for match_clause in _MATCH_CLAUSE_PATTERN.findall(query):
        for alias, label, props in _NODE_PATTERN.findall(match_clause):
            if label not in labels:
                continue

            prop_block = props or ""
            alias_name = alias.strip() if alias else ""
            has_tenant_in_props = bool(re.search(r"(?i)\btenant_id\b", prop_block))
            has_tenant_predicate = bool(alias_name) and alias_name in scoped_aliases

            if not has_tenant_in_props and not has_tenant_predicate:
                violations.append(f"{label}({alias_name or '?'})")

    if violations:
        raise TenantCypherValidationError(
            f"Tenant scope guard violation in {query_name}: missing tenant_id filter for "
            + ", ".join(violations)
        )
