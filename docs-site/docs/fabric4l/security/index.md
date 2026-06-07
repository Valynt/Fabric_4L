---
owner: security-team
status: active
last_reviewed: 2026-06-07
---

# Security

This section documents the security architecture, invariants, and operational controls for the Value Fabric platform. Every layer of the six-layer pipeline enforces security by default: authentication boundaries, tenant isolation, secret management, input validation, rate limiting, and audit logging are first-class concerns, not afterthoughts.

## Security Principles

| Principle | Description | Enforcement |
|---|---|---|
| **Fail closed by default** | Any behavior not explicitly intended is denied. | `ProductionSafetyValidator`, default-deny middleware, RBAC |
| **Tenant isolation is invariant** | Every data read and write is scoped by authenticated tenant context. | RLS policies, graph query filters, repository audit |
| **Never trust the network** | All service-to-service calls are authenticated and authorized. | JWT validation, mTLS where applicable, OIDC |
| **Secrets are never committed** | Real secrets live in Infisical; `.env.example` is the only committed reference. | `gitleaks`, pre-commit hooks, CI scanning |
| **Behavior is the contract** | Security-critical behavior is encoded in tests before it is trusted. | `pytest tests/security/`, hostile tenant matrices, OWASP coverage |
| **Observability enables response** | Security events are logged, correlated, and auditable. | Structured logs, request tracing, immutable audit tables |

## What This Section Covers

- **Authentication & Authorization** — How users and services prove identity, how tokens are validated, and how role-based access control is enforced per layer.
- **Tenant Isolation** — The architectural guarantee that no tenant can read or mutate another tenant's data, from PostgreSQL RLS to Neo4j graph boundaries.
- **Secret Management** — How credentials, API keys, and signing secrets are stored, injected, rotated, and protected from leakage.
- **Threat Model** — The platform's structured threat model covering OWASP Top 10, adversarial inputs, injection vectors, and data-exposure risks.
- **Readiness Gates** — The mandatory production-readiness gate (`make production-readiness-gate`) and the four-stage behavior-readiness ladder that blocks unsafe deployments.

## Security by Layer

| Layer | Port | Primary Security Responsibility |
|---|---|---|
| Layer 1 — Ingestion | 8001 | Crawler SSRF protection, job tenant scoping, source provenance |
| Layer 2 — Extraction | 8002 | Pydantic v2 validation, ontology-guided schema enforcement, provenance |
| Layer 3 — Knowledge Graph | 8003 | Neo4j tenant query filters, Cypher injection prevention, pgvector isolation |
| Layer 4 — Agents | 8004 | Workflow auth boundaries, checkpoint integrity, provider-agnostic output contracts |
| Layer 5 — Ground Truth | 8005 | TruthObject immutability, maturity-ladder audit, claim evidence |
| Layer 6 — Benchmarks | 8006 | Dataset lineage, peer-comparison isolation, statistical-validation integrity |
| API Gateway | — | Shared auth enforcement, rate limiting, governance middleware, tenant context resolution |

## Quick Reference: Security Commands

```bash
# Run the full security suite
pytest tests/security/

# Tenant-isolation focused gate
pnpm test:isolation

# Hostile tenant regression tests
pnpm test:security:hostile

# Production-readiness gate (includes security)
make production-readiness-gate

# Static behavior contract check
make check-behavior-contract

# Rate-limit safety (Redis fail-closed / fallback)
pytest tests/security/test_rate_limit_safety.py
```

## Navigation

- [Authentication Boundaries](./auth-boundaries.md) — OIDC/Keycloak integration, token validation, service-to-service auth, dev bypass warnings.
- [Tenant Isolation](./tenant-isolation.md) — Tenant context propagation, database and graph filtering, cross-tenant prevention, audit checklist.
- [Secret Management](./secret-management.md) — Infisical, CI/CD injection, Kubernetes Operator, pre-commit hooks, rotation.
- [Threat Model](./threat-model.md) — OWASP Top 10 coverage, injection prevention, input validation, rate limiting, audit logging.
- [Readiness Gates](./readiness-gates.md) — Production-readiness gate, `ProductionSafetyValidator`, behavior-readiness audit stages, what blocks deploy.

!!! danger "Non-Negotiables"
    - Do not bypass tenant isolation.
    - Do not weaken auth, RBAC, rate limiting, or audit logging.
    - Do not commit secrets.
    - Do not hardcode provider-specific logic into core orchestration.
    - Do not remove tests just to pass CI.
