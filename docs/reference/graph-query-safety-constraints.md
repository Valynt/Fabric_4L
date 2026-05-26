# Layer 3 Graph Query Safety Constraints

Layer 3 query paths must reuse one centralized guard module:

- `services/layer3-knowledge/src/graph/query_guards.py`

## Centralized defaults

- `DEFAULT_MAX_QUERY_DEPTH = 10`
- `DEFAULT_QUERY_TIMEOUT_SECONDS = 30.0`

## Required guard usage

All graph query entrypoints (API routes, internal services, background/analytics helpers) must:

1. Sanitize traversal depth with `sanitize_query_depth(...)`.
2. Sanitize timeout values with `sanitize_query_timeout_seconds(...)`.
3. Apply tenant query validation via `TenantQueryExecutor` / `run_tenant_query` where applicable.

## Fail-closed behavior

- Missing/invalid depth values fall back to a safe default.
- Missing/invalid timeout values fall back to a safe default.
- Depth values over policy are clamped to max unless a strict rejection mode is explicitly requested.
- Query execution still enforces hard traversal policy in `TenantQueryExecutor` and raises
  `CypherDepthLimitExceeded` when a Cypher pattern exceeds the max policy.
