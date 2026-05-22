"""Layer 3 Neo4j database boundary exports.

Runtime modules must execute Cypher through the approved API surface from
``db.query_execution``:

* :func:`run_scoped_query` for ``ScopedQuery`` objects built from
  ``TenantScopedCypher`` / ``SystemCypher``.
* :func:`run_validated_query` for legacy raw-Cypher callsites that are still
  being migrated to strict scoped builders.

Direct ``session.run(...)`` calls are intentionally forbidden in high-risk
runtime folders (``api/routes``, ``services``, ``agents``, ``analytics``) and
are enforced by static guard tests and the Layer 3 Cypher-scope scanner.
System-scoped exceptions are limited to schema/bootstrap/migration code paths.
"""

from .query_execution import (
    TenantQueryValidationError,
    run_scoped_query,
    run_validated_query,
)

__all__ = ["TenantQueryValidationError", "run_scoped_query", "run_validated_query"]
