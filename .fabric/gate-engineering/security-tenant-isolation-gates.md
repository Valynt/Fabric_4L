# Security and Tenant-Isolation Gates

## Invariants

The following are release-blocking invariants:

- A principal may access only authorized tenant resources.
- Tenant identifier is derived from the JWT or trusted context, never from the request body.
- Graph, vector, object storage, and database queries are tenant-scoped.
- Authentication bypass flags are rejected in production-like environments.
- Audit events are complete for governed actions.

## Required gates

| Gate | Scope | Enforcement | Owner |
|---|---|---|---|
| `security.p0_auth_boundaries` | Merge + Release | `tests/security/test_auth_boundaries.py` | security-leads |
| `pre_production.tenant_isolation` | Release candidate | `scripts/ci/tenant_isolation_readiness_gate.sh` | security-leads |
| `tenant_isolation.hostile_endpoint_family` | Merge | `tests/security/test_hostile_tenant_endpoint_family_contracts.py` | security-leads |
| `tenant_isolation.cross_layer_matrix` | Release candidate | `tests/security/test_cross_layer_tenant_isolation_matrix.py` | security-leads |
| `security.jwt_config` | Merge | `tests/security/test_jwt_config_validation.py` | security-leads |
| `security.cross_tenant_write` | Merge | `tests/security/test_cross_tenant_write.py` | security-leads |
| `security.privileged_access_audit` | Merge | `tests/security/test_privileged_audit.py` | security-leads |
| `security.rate_limit_safety` | Merge | `tests/security/test_rate_limit_safety.py` | security-leads |
| `security.api_key_rejection` | Merge | `tests/security/test_p0_5_api_key_rejection.py` | security-leads |

## Static enforcement

- `scripts/ci/check_layer3_legacy_tenant_dependency_imports.py`
- `scripts/ci/check_layer3_tenant_scoped_similarity_roi.py`
- `scripts/ci/check_tenant_enforcement_opt_in.py`
- `scripts/ci/check_route_tenant_propagation.py`
- `scripts/ci/check_unscoped_tenant_match.py`

## Forbidden patterns

- Raw `HTTPException` in routers (`check_no_raw_httpexception_in_routers.py`)
- Unscoped Neo4j Cypher (`check_l3_cypher_tenant_inventory.py`)
- Dynamic Cypher construction (`.semgrep/cypher-dynamic-guard.yml`)
- Direct header-based tenant access (legacy `X-Tenant-ID` from body)

## Failure behavior

- FAIL: any gate listed above fails → block release.
- INCONCLUSIVE: infra unavailable → block release until evidence is produced.
- No exception is permitted for tenant-isolation violations.

## Evidence

Tenant-isolation evidence is retained in `artifacts/security/tenant-isolation/` for one year and includes JUnit XML, bundle JSON, and commit SHA binding.
