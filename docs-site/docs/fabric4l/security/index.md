---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Security

This section documents the security architecture, invariants, and operational controls for the Value Fabric platform. Every layer of the six-layer pipeline enforces security by default: authentication boundaries, tenant isolation, secret management, input validation, rate limiting, and audit logging are first-class concerns, not afterthoughts.

!!! danger "Security is invariant"
    Security properties are not negotiable. No PR may weaken auth, RBAC, tenant isolation, rate limiting, audit logging, governance middleware, contract validation, or production gates. If a change touches any of these surfaces, it must include hostile tests and pass the full security suite.

## Security Principles

| Principle | Description | Enforcement |
|---|---|---|
| **Fail closed by default** | Any behavior not explicitly intended is denied. Untested behavior is not production-ready. | `ProductionSafetyValidator`, default-deny middleware, RBAC, permission OR/AND logic |
| **Tenant isolation is invariant** | Every data read and write is scoped by authenticated tenant context. Never trust request body tenant IDs over authenticated context. | PostgreSQL RLS policies, Neo4j graph query filters, repository audit, hostile cross-tenant tests |
| **Never trust the network** | All service-to-service calls are authenticated and authorized. Token validation is strict and rejects algorithm confusion, `none` algorithm, and expired claims. | JWT validation (HS256/RS256/ES256 only), mTLS where applicable, OIDC via Keycloak |
| **Secrets are never committed** | Real secrets live in Infisical; `.env.example` is the only committed reference. | `gitleaks`, pre-commit hooks, CI scanning, `ProductionSafetyValidator` |
| **Behavior is the contract** | Security-critical behavior is encoded in tests before it is trusted. The test suite is the executable contract. | `pytest tests/security/`, hostile tenant matrices, OWASP Top 10 coverage, behavior-readiness audit |
| **Observability enables response** | Security events are logged, correlated, and auditable. Errors do not leak secrets, stack traces, or raw provider responses. | Structured logs with `sanitize_log_error()`, immutable audit tables, request tracing |

## What This Section Covers

- **Authentication & Authorization** — How users and services prove identity, how tokens are validated, how role-based access control is enforced per layer, and how dev auth bypass flags are blocked in production.
- **Tenant Isolation** — The architectural guarantee that no tenant can read or mutate another tenant's data, from PostgreSQL RLS to Neo4j graph boundaries, with common anti-patterns and audit checklists.
- **Secret Management** — How credentials, API keys, signing secrets, and connection strings are stored in Infisical, injected via GitHub OIDC, managed in Kubernetes, and protected from leakage by pre-commit hooks.
- **Threat Model** — The platform's structured threat model covering OWASP Top 10, adversarial inputs, injection vectors (SQL, Cypher, XXE, SSTI, LDAP), and data-exposure risks.
- **Readiness Gates** — The mandatory production-readiness gate (`make production-readiness-gate`) and the four-stage behavior-readiness ladder that blocks unsafe deployments.

## Security by Layer

| Layer | Port | Primary Security Responsibility |
|---|---|---|
| Layer 1 — Ingestion | 8001 | Crawler SSRF blocklists, job tenant scoping, source provenance, Celery queue isolation |
| Layer 2 — Extraction | 8002 | Pydantic v2 validation, ontology-guided schema enforcement, provenance tracking, batch ingest auth |
| Layer 3 — Knowledge Graph | 8003 | Neo4j tenant query filters, Cypher injection prevention (`cypher-dynamic-guard.yml`), pgvector isolation |
| Layer 4 — Agents | 8004 | Workflow auth boundaries, checkpoint integrity, provider-agnostic output contracts, stream tenant adversarial tests |
| Layer 5 — Ground Truth | 8005 | TruthObject immutability, maturity-ladder audit, claim evidence, audit mutation protection |
| Layer 6 — Benchmarks | 8006 | Dataset lineage, peer-comparison isolation, statistical-validation integrity, cross-tenant benchmark boundaries |
| API Gateway | — | Shared auth enforcement, rate limiting (`GovernanceMiddleware`), tenant context resolution, governance middleware stack |

## Quick Reference: Security Commands

```bash
# Run the full security suite (all layers, no live services required for static tests)
pytest tests/security/

# OWASP Top 10 focused tests
pytest tests/security/test_owasp_top10.py
pytest tests/security/test_owasp_top10_complete.py

# Tenant-isolation focused gate
pytest tests/security/test_tenant_isolation.py
pytest tests/security/test_cross_layer_tenant_isolation_matrix.py

# Hostile tenant regression tests
pytest tests/security/test_hostile_tenant_e2e_matrix.py
pytest tests/security/test_hostile_tenant_journey_contracts.py

# Authentication boundary tests
pytest tests/security/test_auth_boundaries.py
pytest tests/security/test_auth_guards.py
pytest tests/security/test_auth_default_deny.py

# Production-readiness gate (includes security, dev bypass detection, contract compliance)
make production-readiness-gate

# Static behavior contract check (Stage 1 of 4)
make check-behavior-contract

# Rate-limit safety (Redis fail-closed / fallback behavior)
pytest tests/security/test_rate_limit_safety.py
pytest tests/security/test_rate_limit_window.py

# Secret handling and bypass guardrails
pytest tests/security/test_secret_handling.py
pytest tests/security/test_production_bypass_guardrails.py
pytest tests/security/test_dev_bypass.py

# Semgrep security rules
semgrep --config .semgrep/ --error
```

## Related Governance Documents

| Document | Location | Purpose |
|---|---|---|
| Platform Contract | `docs/contract.md` | Canonical tenant context, middleware, auth flow, RLS, and error envelope specifications |
| Engineering Governance | `docs/governance.md` | Production gates, ADR policy, K8s `SecurityContext` standard, static tenant inference enforcement |
| Behavior-First Testing | `docs/governance/behavior-first-testing.md` | Readiness ladder, skip governance, behavior-debt policy |
| Compatibility Debt Registry | `docs/governance/compatibility-debt-registry.md` | Shim tracking and drift prevention |
| PR Template | `.github/pull_request_template.md` | Required security impact declarations |

## Navigation

- [Authentication Boundaries](./auth-boundaries.md) — OIDC/Keycloak integration, token validation, service-to-service auth, session management, dev bypass warnings.
- [Tenant Isolation](./tenant-isolation.md) — Tenant context propagation, database and graph filtering, cross-tenant prevention, common anti-patterns, audit checklist.
- [Secret Management](./secret-management.md) — Infisical, CI/CD injection via GitHub OIDC, Kubernetes Operator, pre-commit hooks, rotation procedures.
- [Threat Model](./threat-model.md) — OWASP Top 10 coverage, injection prevention, input validation, rate limiting, audit logging, adversarial inputs.
- [Readiness Gates](./readiness-gates.md) — Production-readiness gate, `ProductionSafetyValidator`, behavior-readiness audit stages, what blocks deployment.

!!! danger "Non-Negotiables"
    - Do not bypass tenant isolation.
    - Do not weaken auth, RBAC, rate limiting, or audit logging.
    - Do not commit secrets.
    - Do not hardcode provider-specific logic into core orchestration.
    - Do not remove tests just to pass CI.
    - Do not trust request body tenant IDs over authenticated context.
    - Do not expose secrets, stack traces, internal tokens, or raw provider responses in error messages.
