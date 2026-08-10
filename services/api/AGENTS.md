# AGENTS — services/api (API Gateway)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

Shared auth enforcement and request routing for all layers: JWT/API-key
validation, tenant context extraction and propagation, rate limiting, and
routing to upstream L1–L6 services. No dedicated public port; deployed as a
sidecar or ingress component.

## Single-writer surface

Auth and tenant-resolution middleware are **single-writer surfaces**
(`release/v1/launch-contract.yaml` concurrency_rules): do not modify them
concurrently with another task, and never weaken auth, RBAC, rate limiting,
or governance middleware.

## Layer rules

- Tenant identity is resolved here from authenticated context and propagated
  downstream; request-body tenant IDs never override it.
- Missing, invalid, or conflicting tenant context fails closed (401/403 with
  structured errors), never falls through to a default tenant.
- Preserve trace IDs, tenant IDs, and audit metadata on every proxied request.
- Dev auth bypass flags (`DEV_AUTH_BYPASS` etc.) must never reach
  production-like configs; see SECURITY.md and `ProductionSafetyValidator`.

## Validation

```bash
pytest services/api/tests
pytest tests/tenancy -q
pytest tests/security -q
make check-behavior-contract
```
