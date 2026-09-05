---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Fabric4L Operations

This section contains the canonical operational reference for running, deploying,
monitoring, and recovering the Value Fabric platform in production and
pre-production environments.

## What Operators Will Find Here

| Page | Purpose | Audience |
|---|---|---|
| [Deployment](./deployment.md) | Environment topology, Docker Compose local stack, Kubernetes production manifests, secret management, database migrations, and rolling deployment procedures | SRE, Platform Engineers, Release Engineers |
| [Monitoring](./monitoring.md) | Health checks, metrics endpoints, alerting thresholds, dashboard references, and infrastructure-specific observability (Neo4j, PostgreSQL, Redis, Keycloak) | SRE, On-Call Engineers, Platform Teams |
| [Incident Response](./incident-response.md) | Severity classification, on-call responsibilities, initial response playbook, escalation paths, and post-incident review process | On-Call Engineers, Incident Commanders, Engineering Managers |
| [Runbooks](./runbooks.md) | Step-by-step operational procedures for common scenarios: database backup/restore, cache clearing, queue retry, service restarts, tenant isolation verification, and identity management | SRE, Platform Engineers, Security Engineers |

## Platform Topology at a Glance

Value Fabric is a six-layer pipeline plus a React frontend and shared API gateway:

```text
Frontend (React/Vite)  →  Port 3001
Layer 1 Ingestion      →  Port 8001  (Playwright, Celery, Redis queues)
Layer 2 Extraction     →  Port 8002  (Pydantic v2, RDF/OWL, LLM extraction)
Layer 3 Knowledge      →  Port 8003  (Neo4j, GraphRAG, pgvector)
Layer 4 Agents         →  Port 8004  (LangGraph, checkpoints, orchestration)
Layer 5 Ground Truth   →  Port 8005  (TruthObject validation, maturity ladder)
Layer 6 Benchmarks     →  Port 8006  (Peer comparison, statistical validation)
API Gateway            →  Auth enforcement, routing, rate limiting
```

Infrastructure dependencies:

- **PostgreSQL** — relational state for L1, L2, L4, L5, L6, L7 billing
- **Neo4j** — knowledge graph and semantic retrieval for L3 and L4
- **Redis** — caching, pub/sub, and Celery broker/result backend
- **Keycloak** — OIDC/SAML identity broker (dev) / Clerk (production IdP)
- **MinIO** — S3-compatible object storage (local dev)

!!! note "Environment-specific defaults"
    Local development uses `docker-compose.dev.yml` with Infisical-generated
    environment files. Production deployments use Kubernetes manifests under
    `k8s/deployments/` with External Secrets Operator or Infisical.

## Quick Reference Commands

```bash
# Start the local development stack
pnpm env:dev && docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# Run all database migrations
make migrate

# Validate production readiness before a release
make production-readiness-gate

# Check migration heads (exactly one Alembic head per service)
make check-migration-heads

# Full platform verification
make verify
```

## Operational Invariants

The following invariants are non-negotiable during any operational procedure:

1. **Tenant isolation** — Every data read or write must be scoped by authenticated
   tenant context. Never trust request-body tenant IDs.
2. **Fail closed** — If behavior is not explicitly intended, it fails closed by
   default. Do not weaken auth, RBAC, or tenant checks to restore availability.
3. **Audit preservation** — Preserve logs, query samples, migration output, backup
   IDs, and tenant-scoped audit records before destructive remediation.
4. **Contract alignment** — Do not silently change API response shapes. If a
   backend response changes, update OpenAPI contracts, JSON schemas, TypeScript
   types, and tests.
5. **Secret hygiene** — Never commit real secrets. Use Infisical, External Secrets
   Operator, or Vault in all non-local environments.

## Validation

Operational documentation is validated by CI:

```bash
# Lint runbooks for completeness and link health
pnpm ops:runbooks:lint

# Validate incident workflow structure and severity coverage
pnpm ops:incident:check
```

## Related Documentation

- `docs/development/BUILD_SYSTEM.md` — Build system hierarchy and command precedence
- `docs/development/COMMANDS.md` — Full command inventory for local contributors and CI
- `AGENTS.md` — Agent entry point and links to architecture, security, and layer guidance
- `k8s/README.md` — Kubernetes deployment guide and security hardening
- `ops/incident/README.md` — Incident response workflow source of truth
