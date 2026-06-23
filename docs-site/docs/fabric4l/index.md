---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Fabric4L Engineering

Welcome to the **Fabric4L Engineering** documentation — the technical source of truth for developers, operators, and security engineers working on the ValuePact platform.

!!! note "Audience"
    This section is intended for **platform engineers**, **SREs**, **security engineers**, and **technical contributors**. End-user product documentation lives in the other top-level sections (Getting Started, User Guides, Administration, etc.).

## What is Fabric4L?

**Fabric4L** is the internal engineering codename for the six-layer data and intelligence pipeline that powers ValuePact:

| Layer | Service | Port | Responsibility |
|-------|---------|------|----------------|
| **L1** | `layer1-ingestion` | 8001 | Playwright crawling, Celery jobs, Redis queues, compliance-aware ingestion |
| **L2** | `layer2-extraction` | 8002 | Pydantic v2 extraction, LLM extraction, RDF/OWL generation, provenance |
| **L3** | `layer3-knowledge` | 8003 | Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs |
| **L4** | `layer4-agents` | 8004 | LangGraph workflows, ROI calculator, business case generation, checkpoints |
| **L5** | `layer5-ground-truth` | 8005 | TruthObject validation, maturity ladder, evidence-backed claims |
| **L6** | `layer6-benchmarks` | 8006 | Peer comparison, statistical validation, datasets, benchmark policies |

The frontend (React + Vite) communicates with these layers through a shared API gateway and TanStack Query.

## Documentation Sections

### [Architecture](./architecture/index.md)
System design, data flow, service topology, auth architecture, tenancy model, and observability stack.

- [System Overview](./architecture/system-overview.md) — Six-layer pipeline and technology stack
- [Service Map](./architecture/service-map.md) — Ports, responsibilities, and runtime paths
- [Data Flow](./architecture/data-flow.md) — How requests flow through L1→L2→L3→L4→L5→L6
- [Authentication](./architecture/auth.md) — OIDC, RBAC, and service-to-service auth
- [Tenancy](./architecture/tenancy.md) — Multi-tenant isolation strategy
- [Observability](./architecture/observability.md) — Logging, metrics, traces, and alerting

### [Development](./development/index.md)
Setup instructions, contribution guidelines, coding standards, testing strategy, and repo organization.

- [Contribution Guide](./development/contribution-guide.md) — First-time setup, commits, PRs
- [Coding Standards](./development/coding-standards.md) — Python, TypeScript, and layer-boundary rules
- [Testing](./development/testing.md) — Behavior-first testing, markers, and coverage
- [Repo Strategy](./development/repo-strategy.md) — Monorepo structure and canonical paths

### [Operations](./operations/index.md)
Deployment procedures, monitoring, incident response, and operational runbooks.

- [Deployment](./operations/deployment.md) — Docker Compose, Kubernetes, and migrations
- [Monitoring](./operations/monitoring.md) — Health checks, logs, metrics, and dashboards
- [Incident Response](./operations/incident-response.md) — Severity levels and playbooks
- [Runbooks](./operations/runbooks.md) — Common operational procedures

### [Security](./security/index.md)
Auth boundaries, tenant isolation, secret management, threat model, and production-readiness gates.

- [Auth Boundaries](./security/auth-boundaries.md) — Token validation and RBAC
- [Tenant Isolation](./security/tenant-isolation.md) — Cross-tenant prevention patterns
- [Secret Management](./security/secret-management.md) — Infisical, CI/CD, and rotation
- [Threat Model](./security/threat-model.md) — OWASP coverage and controls
- [Readiness Gates](./security/readiness-gates.md) — What blocks production deployment

### [Behavior Contracts](./behavior-contracts/index.md)
Behavior-first testing philosophy, critical behaviors, test strategy, and readiness gates.

- [Critical Behaviors](./behavior-contracts/critical-behaviors.md) — What must be tested
- [Test Strategy](./behavior-contracts/test-strategy.md) — Test pyramid and markers
- [Gate Registry](./behavior-contracts/gate-registry.md) — Four-stage readiness ladder

### [ADRs](./adr/index.md)
Architecture Decision Records for major technical choices.

### [Reference](./reference/index.md)
Glossary, quick-reference links, and documentation standards.

## Quick Commands

```bash
# Full verification (run before every PR)
make verify

# Run all backend tests
make test

# Run contract tests
make contract-tests

# Check for conflict markers
make check-conflict-markers

# Check migration heads
make check-migration-heads

# Production readiness gate
make production-readiness-gate
```

## Core Principles

1. **Contract-first** — APIs, schemas, and agent outputs are the source of truth.
2. **Tenant-safe** — Every data operation is scoped by authenticated tenant context.
3. **Layered** — Logic stays in its layer; cross-layer calls use defined contracts.
4. **Auditable** — All critical actions emit structured audit events.
5. **Provider-agnostic** — Core orchestration has no hardcoded LLM vendor logic.
6. **Drift-resistant** — Contracts, types, and tests prevent silent architectural drift.

## Getting Help

- **Engineering questions**: `#engineering` Slack channel
- **Security incidents**: Follow the [Incident Response Playbook](./operations/incident-response.md)
- **On-call issues**: See [Runbooks](./operations/runbooks.md)
- **Documentation gaps**: File a ticket and add a `TODO(behavior-debt)` comment in code
