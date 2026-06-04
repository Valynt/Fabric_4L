# Centralized Security Test Suite

`tests/security/` is the repository-owned aggregation point for production-readiness security validation.  Layer-specific security tests may still live beside the code they protect, but this directory documents the canonical categories and contains thin manifest tests that reference those focused suites without copying their assertions.

## Canonical commands

```bash
pytest tests/security/
pnpm test:security
```

`pnpm test:security` delegates directly to `pytest tests/security/` and accepts additional pytest arguments after `--`.

## Aggregation files

| Aggregator | Category | What it references |
| --- | --- | --- |
| `test_auth_guards.py` | Authentication and authorization guards | JWT validation, RBAC, default-deny auth, service accounts, WebSocket auth, session hijacking, and dev-bypass guardrails. |
| `test_tenant_isolation.py` | Tenant isolation and cross-tenant boundaries | Direct tenant isolation tests plus cross-layer, graph/RLS, repository-filter, and hostile-tenant regression coverage. |
| `test_secret_handling.py` | Secret handling and sensitive data controls | Secret scanning, API-key rejection, PII-at-rest controls, audit coverage, hardcoded demo-data prevention, and sensitive-route audit tests. |
| `test_security_headers.py` | Security headers and browser-facing hardening | HTTP security headers, security middleware, CSRF, request tracing, correlation logging, and production bypass checks. |
| `test_dependency_policy.py` | Dependency and supply-chain policy | pnpm/package-manager policy, lockfile integrity, SBOM/SLSA posture, dependency governance scripts, and mandatory security gate checks. |
| `test_container_policy.py` | Container and deployment policy | Dockerfile reproducibility, Kubernetes hardening policy, service startup validation, and security workflow policy. |

The category manifest lives in `security_suite_manifest.py`.  The manifest is metadata-only; do not import existing test modules from aggregators because that would duplicate collection and can trigger layer-specific import side effects.

## Coverage by category

### Authentication and authorization guards

Backed by focused tests including:

- `tests/security/test_auth_boundaries.py`
- `tests/security/test_auth_default_deny.py`
- `tests/security/test_auth_governance.py`
- `tests/security/test_jwt_validation.py`
- `tests/security/test_rbac.py`
- `tests/security/test_websocket_auth.py`
- `services/api/app/tests/test_impersonation_security.py`
- `services/api/app/tests/test_bcrypt_security.py`

### Tenant isolation and cross-tenant boundaries

Backed by focused tests including:

- `tests/security/test_tenant_isolation.py`
- `tests/security/test_tenant_boundary_fails_closed.py`
- `tests/security/test_cross_tenant_api.py`
- `tests/security/test_cross_tenant_write.py`
- `tests/security/test_cross_layer_tenant_isolation_matrix.py`
- `tests/backend_integrated/test_tenant_isolation_security_persistence.py`
- `tests/layer1/test_layer1_security_invariants.py` through `tests/layer6/test_layer6_security_invariants.py`

### Secret handling and sensitive data controls

Backed by focused tests including:

- `tests/security/test_secrets_protection.py`
- `tests/security/test_p0_5_api_key_rejection.py`
- `tests/security/test_pii_encryption_at_rest.py`
- `tests/security/test_hardcoded_demo_data_removal.py`
- `tests/security/test_sensitive_route_audit_coverage.py`
- `tests/security/test_audit_event_emission.py`

### Security headers and browser-facing hardening

Backed by focused tests including:

- `tests/security/test_security_headers.py`
- `tests/security/test_security_misconfiguration.py`
- `tests/security/test_shared_security_middleware.py`
- `tests/security/test_p1_14_security_middleware.py`
- `tests/security/test_csrf_comprehensive.py`
- `tests/security/test_request_tracing.py`

### Dependency and supply-chain policy

Backed by focused tests and governance checks including:

- `tests/security/test_supply_chain.py`
- `tests/security/test_dockerfile_lockfile_fix.py`
- `tests/security/test_mandatory_security_regression_gate.py`
- `tests/ci/test_mandatory_security_regression_gate.py`
- `scripts/ci/check_package_manager_policy.mjs`
- `scripts/ci/validate_dependabot_coverage.py`

### Container and deployment policy

Backed by focused tests and policy artifacts including:

- `tests/security/test_dockerfile_lockfile_fix.py`
- `tests/security/test_h03_service_startup_validation.py`
- `tests/security/test_startup_bypass_nonzero_exit.py`
- `tests/k8s/test_security_policies.py`
- `k8s/policy/security-hardening.rego`
- `.github/workflows/security-gates.yml`

## CI summary artifact

The security validation workflow generates `artifacts/security/security-test-summary.md` and `artifacts/security/security-test-summary.json` from the same manifest and uploads them as the `security-test-summary` artifact.  This keeps PR/release evidence aligned with the centralized category map.

## Maintenance rules

- Add new security tests to their closest layer when they need layer-local fixtures, then add a manifest reference here when they satisfy a central category.
- Keep aggregators thin: they should validate that referenced coverage exists, not reimplement security assertions.
- Prefer markers (`security`, `tenant_boundary`, `contract_static`) for selection; do not duplicate tests via imports.
- Update this README and `security_suite_manifest.py` whenever a category changes.
