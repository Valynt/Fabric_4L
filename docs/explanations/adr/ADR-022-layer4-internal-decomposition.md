<!-- ADR-022: Layer 4 Internal Decomposition -->

# ADR-022: Layer 4 Internal Decomposition

**Status:** Proposed
**Date:** May 22, 2026
**Authors:** Platform Architecture
**Reviewers:** Platform Architecture Committee

---

## Context

Layer 4 (`services/layer4-agents/`) has grown to **263 Python files** across 14 top-level modules (routes, services, models, harness, engine, tools, workflows, tenants, integration, registry, messaging, provenance, feature_flags). All modules share:

- One FastAPI app
- One PostgreSQL schema
- One Alembic migration chain
- Direct intra-module imports

This creates:
- **Deployment blast radius:** A billing Stripe API change or tenant provisioning change requires redeploying the entire agent workflow engine.
- **Scaling mismatch:** Billing/usage is stable CPU-light logic; agent workflows are LangGraph-heavy. They scale differently.
- **Team coordination:** The architecture docs explicitly warn that "a monolithic service that requires coordination between five teams to deploy" is a problematic boundary. L4 currently fits that description.
- **Empty canonical runtime:** `value_fabric/layer4/` contains only a path shim `__init__.py`. There is no canonical runtime extraction.

We needed to decide whether to:
1. Keep L4 as a single monolith with internal modular directories
2. Decompose L4 into standalone services with their own deployable units

## Decision

We will **decompose Layer 4 incrementally**, starting with **Billing** as the pilot extraction, following the pattern established by ADR-014 and the canonical runtime path governance (`docs/reference/layer-runtime-path-governance.md`).

### Principles

1. **Domain boundary over file count:** A module becomes a service candidate when it has independent change velocity, distinct scaling needs, or external API boundaries (e.g., Stripe).
2. **Canonical runtime first:** New domain logic lives in `value_fabric/layer4/<domain>/` before a service wrapper is created.
3. **Shared DB initially, split later:** Extracted services begin on the same PostgreSQL instance to avoid migration-chain complexity. A future ADR will govern DB splitting.
4. **Backward compatibility:** Existing routes remain as proxies during migration. No breaking changes to frontend or service-to-service callers.
5. **Tenant isolation invariant:** Every extracted service must preserve tenant-scoped queries and auth middleware.

### Pilot: Billing & Usage Service

**Rationale for pilot:**
- Clear external API boundary with Stripe
- Isolated models (`models/billing.py`), schemas, routes, and services already exist
- Changes quarterly (compliance, new providers) while agent workflows change daily
- Lowest risk: billing is not on the critical path for agent workflow execution

**Extraction plan:**

```text
Phase 1 — Canonical runtime
  value_fabric/layer4/billing/__init__.py
  value_fabric/layer4/billing/models.py          ← from models/billing.py
  value_fabric/layer4/billing/schemas.py         ← from api/schemas/billing.py
  value_fabric/layer4/billing/services/          ← interfaces + re-exports

Phase 2 — Service wrapper (superseded 2026-06-05)
  services/layer7-billing/src/layer7_billing/api/  ← canonical deployable billing API
  services/layer7-billing/Dockerfile
  services/layer7-billing/pyproject.toml
  docker-compose.full.yml                         ← port 8008

Phase 3 — Proxy migration
  services/layer4-agents/src/layer4_agents/api/routes/billing.py
    → becomes a thin proxy to services/layer7-billing/ via HTTP client
  → Remove after all callers migrate (target: 2026-10-31)

Compatibility note:
  services/billing/ remains non-deployable historical Stripe compatibility code only.
```

### Future Candidates (ordered by priority)

| Rank | Domain | Rationale |
|---|---|---|
| 2 | Tenant & Identity | Cross-cutting concern; L1–L6 all consume it; has internal route modularity |
| 3 | Harness / Workflow Governance | Deterministic state machine, checkpoints, gates; documented as separate conceptually |
| 4 | Engine / Checkpoint & Dispatch | Infrastructure that could serve multiple workflow runtimes |
| 5 | Business Case & Value Quantification | User-facing analytic products; change independently from core orchestration |
| 6 | Tool Registry | Schema-first tool definitions; would enable L2/L3/L5 to discover tools without L4 coupling |

## Rationale

### Why Decompose Now?

| Concern | Monolithic L4 Impact | Decomposed Impact |
|---------|---------------------|-------------------|
| Deployment blast radius | Billing change → redeploy agent engine | Billing deploys independently |
| Scaling mismatch | All of L4 scales with LangGraph CPU | Billing scales on stable CPU; workflows scale on GPU/CPU mix |
| Team autonomy | 5 teams coordinate on one deploy | Teams own services independently |
| Test cycle time | Full L4 test suite on every PR | Service-level test gates run in parallel |
| On-call load | Any L4 issue pages all L4 owners | Domain-specific on-call rotation |

### Why Billing as Pilot?

- **External boundary:** Stripe integration is already a well-defined API surface
- **Low coupling:** Billing routes are not called by LangGraph workflows during execution
- **Rollback safety:** Billing outages do not block business case generation
- **Proves the pattern:** Success with billing gives confidence for higher-coupling extractions (harness, engine)

## Trade-offs

### Positive
- Reduced deployment blast radius
- Independent scaling per domain
- Team autonomy with service ownership
- Faster test and build cycles per service

### Negative
- Operational complexity (more containers, more health checks)
- Network latency between L4 sub-services
- Shared DB initially means shared fate for DB migrations
- Proxy overhead during migration period

## Mitigations

| Risk | Mitigation |
|---|---|
| Operational complexity | Start with Docker Compose; K8s manifests follow after pilot proves stable |
| Network latency | Keep services in same VPC / cluster; use connection pooling |
| Shared DB fate | Alembic migrations remain coordinated; tag migrations with service owner |
| Proxy overhead | Proxies are temporary; removal target 2026-09-30 per compatibility registry |
| Contract drift | OpenAPI spec lives in `contracts/openapi/billing.yaml`; drift gate in CI |

## Implementation

### Canonical Runtime Path Policy

```python
# Correct — canonical runtime
from value_fabric.layer4.billing.models import BillingCustomer

# Deprecated — service-local path (allowed during migration)
from services.layer4-agents.src.models.billing import BillingCustomer

# Blocked — never use
from value_fabric.layer4_agents.src.models.billing import BillingCustomer
```

### Compatibility Debt Registry

- **COMPAT-L4-002:** Billing canonical runtime extraction (removal target: 2026-09-30)
- **COMPAT-L4-003:** Billing service wrapper migration (removal target: 2026-10-31)

### Tenant Isolation Checklist for Extracted Services

- [ ] `tenant_id` extracted from authenticated context (JWT / API key)
- [ ] All repository queries filter by `tenant_id`
- [ ] Writes persist `tenant_id`
- [ ] Cross-tenant hostile tests included in service test suite
- [ ] Rate limiting applied per tenant

## Consequences

### Accepted
- Higher operational complexity than monolithic L4
- Temporary proxy routes during migration
- Shared PostgreSQL instance until a future DB-split ADR

### Mitigated
- Contract drift via OpenAPI drift gate and shared canonical runtime
- Tenant isolation via cross-tenant hostile tests in every extracted service
- Proxy accumulation via compatibility debt registry with removal dates

## Related Decisions

- ADR-014: Multi-Layer Architecture vs Monolith
- ADR-019: Replayability, Event Envelope, and Layer 4 Replay Harness
- `docs/reference/layer-runtime-path-governance.md`
- `docs/governance/compatibility-debt-registry.md`

---

**Last Updated:** May 22, 2026
