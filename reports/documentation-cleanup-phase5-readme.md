# Documentation Cleanup - Phase 5: README as Navigation Layer

**Audit Date:** 2026-05-28
**Auditor:** Documentation Archaeologist

---

## Proposed README Structure

Based on the consolidation and archival decisions, here is the proposed new README structure for `README.md` (root) and `docs/README.md` (documentation hub).

---

## Proposed Root README.md

```markdown
# Value Fabric — Enterprise Agentic SaaS Platform

A production-grade, multi-agent system (MAS) that transforms unstructured enterprise data into
structured, actionable knowledge through an ontology-guided pipeline and autonomous AI agents.

## What it is

Value Fabric is an **enterprise agentic SaaS platform** built on a 6-layer semantic pipeline.
Agents reason over a knowledge graph to produce ROI analyses, business cases, and executive insights—
automatically, at scale, with full auditability.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND: REACT PRESENTATION                        │
│         (Vite · React Query · Zustand · shadcn/ui · Tailwind)             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ REST/WebSocket
┌───────────────────────────────▼─────────────────────────────────────────────┐
│              LAYER 6: BENCHMARK SERVICE (Port 8006)                        │
│              (Peer Comparison · Statistical Validation · Datasets)         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│              LAYER 5: GROUND TRUTH (Port 8005)                              │
│    (TruthObject Validation · Maturity Ladder · Evidence-backed Claims)     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│              LAYER 4: AGENTIC WORKFLOW ENGINE (Port 8004)                    │
│      (LangGraph · ROI Calculator · Business Case Generator · Checkpoints)  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ REST
┌───────────────────────────────▼─────────────────────────────────────────────┐
│          LAYER 3: KNOWLEDGE GRAPH & SEMANTIC LAYER (Port 8003)              │
│       (Neo4j · GraphRAG · Hybrid Retrieval · pgvector · Subgraph API)       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ RDF/Turtle
┌───────────────────────────────▼─────────────────────────────────────────────┐
│         LAYER 2: ONTOLOGY-GUIDED EXTRACTION PIPELINE (Port 8002)           │
│    (Pydantic v2 · LLM Extraction · RDF/OWL · Provenance · Batch Ingest)    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ Markdown chunks
┌───────────────────────────────▼─────────────────────────────────────────────┐
│           LAYER 1: INTELLIGENT DATA INGESTION SERVICE (Port 8001)         │
│     (Playwright · Celery/Redis · PostgreSQL · Multi-tenancy · Compliance) │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Frontend Governance

Frontend changes are governed by the root [`DESIGN.md`](DESIGN.md) contract. Human contributors and AI coding agents must read it before modifying `apps/web/`, reuse existing React/Vite/TypeScript/Tailwind/shadcn/TanStack Query patterns, and report validation results with any remaining risks.

## Package Manager Policy (Monorepo)

This repository uses **pnpm** as the canonical package manager.

```bash
# Enable corepack and activate the repo-pinned pnpm version
corepack enable
corepack use pnpm@10.18.1

# Install JavaScript/TypeScript dependencies
pnpm install
```

Using `npm install` or `yarn install` is not supported and will fail fast via the root `preinstall` guard.

## Quickstart (5 minutes)

### 1. Clone and configure
```bash
git clone https://github.com/bmsull560/Fabric_4L.git && cd Fabric_4L
cp .env.example .env
# Fill in OPENAI_API_KEY and JWT_SECRET
```

### 2. Start infrastructure
```bash
docker compose -f docker-compose.full.yml up -d
```

### 3. Run migrations
```bash
make migrate
```

### 4. Verify everything works
```bash
make verify
```

### 5. Open the UI
```bash
open http://localhost:5173
```

**For detailed setup instructions:** See [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)

## Repository Map

Per **[ADR-027](docs/architecture/ADR-021-layer-3-canonical-runtime-path.md)**, the
canonical implementation tree is `services/`. The `value_fabric/layer*/`
packages are **namespace shims only** that re-export from the matching service
package. See **[Layer Runtime Path Governance](docs/reference/layer-runtime-path-governance.md)**
for the full matrix.

| Path | Status | Purpose |
|------|--------|---------|
| `services/layer1-ingestion/src/` | **Canonical** | Layer 1 ingestion runtime |
| `services/layer2-extraction/src/` | **Canonical** | Layer 2 extraction runtime |
| `services/layer3-knowledge/src/` | **Canonical** | Layer 3 knowledge / retrieval runtime |
| `services/layer4-agents/src/` | **Canonical** | Layer 4 agent orchestration runtime |
| `services/layer5-ground-truth/src/layer5_ground_truth/` | **Canonical** | Layer 5 ground-truth runtime |
| `services/layer6-benchmarks/src/` | **Canonical** | Layer 6 benchmark runtime |
| `services/api/` | **Maintained** | Cross-layer API service |
| `value_fabric/layer1/` … `value_fabric/layer6/` | **Shim only** | Namespace facades; shim-removal review by 2026-09-30 |
| `value_fabric/shared/` | **Canonical** | Shared runtime packages |
| `apps/web/` | **Canonical** | React + TypeScript UI |
| `contracts/` | **Canonical** | Versioned tool manifests, JSON Schemas, OpenAPI specs |
| `k8s/` | **Canonical** | Kubernetes manifests |
| `monitoring/` | **Canonical** | Prometheus + Grafana dashboards |
| `packs/` | **Canonical** | Domain-specific data packs |
| `docs/` | **Canonical** | Architecture docs and runbooks |
| `tests/` | **Canonical** | Cross-layer integration and agent evaluation tests |
| `.github/workflows/` | **Canonical** | CI pipelines |

## Core Concepts

| Document | Description |
|----------|-------------|
| [System Architecture](docs/core-concepts/architecture.md) | 6-layer pipeline architecture |
| [Security Model](docs/core-concepts/security-model.md) | Authentication, RBAC, and tenant isolation |
| [Ontology System](docs/core-concepts/ontology-system.md) | Entity taxonomy and extraction pipeline |
| [Canonical Platform Contract](docs/contract.md) | Enforced direction for 6 cross-layer concerns |

## Developer Guide

| Document | Description |
|----------|-------------|
| [Layer Runtime Path Governance](docs/reference/layer-runtime-path-governance.md) | Where new code must live per layer |
| [Testing Strategy](docs/reference/testing-strategy.md) | Test pyramid and coverage requirements |
| [API Reference](docs/reference/api-overview.md) | Multi-layer API structure and patterns |
| [Frontend Query Patterns](docs/reference/frontend-query-patterns.md) | TanStack Query, Zustand, and generated-client rules |

## For AI Agents

| Document | Description |
|----------|-------------|
| [AGENTS.md](AGENTS.md) | Practical commands and directory map for AI agents |
| [DESIGN.md](DESIGN.md) | Frontend governance contract for apps/web/ |

## Operations

| Document | Description |
|----------|-------------|
| [Troubleshooting Guide](docs/troubleshooting/index.md) | Decision trees and common issues |
| [Operator Runbooks](docs/how-to-guides/operators.md) | Single jumping-off point for operator-facing runbooks |
| [Release Runbook](docs/operations/RELEASE_RUNBOOK.md) | Release procedures |
| [Keycloak Integration](docs/operations/keycloak-integration.md) | Keycloak setup and configuration |

## Governance

| Document | Description |
|----------|-------------|
| [Compatibility Debt Registry](docs/governance/compatibility-debt-registry.md) | Canonical registry for compatibility shims |
| [Launch Drift Prevention SOP](docs/governance/launch-drift-prevention-sop.md) | Required approvals on contract/tenant/shim changes |
| [Contract Governance](contracts/GOVERNANCE.md) | How API contracts evolve |

## Documentation

📚 **[Complete Documentation →](docs/README.md)**

Our documentation follows the [Diátaxis Framework](https://diataxis.fr/) with tutorials, how-to guides, reference, and explanations.

## SDK Installation

```bash
pip install valuefabric-sdk
```

Or install from source:

```bash
cd sdk/python
pip install -e ".[dev]"
```

See [`sdk/python/README.md`](sdk/python/README.md) for SDK usage and CLI examples.

## Security

Never commit real secrets. Use `.env` files (gitignored) locally, and short-lived OIDC credentials in CI.
See [`SECURITY.md`](SECURITY.md) for the full policy and how to report vulnerabilities.

## License

See [`LICENSE`](LICENSE) for terms.
```

---

## Proposed docs/README.md

```markdown
# Value Fabric Documentation

> **Organization Version:** 2.0  
> **Last Updated:** 2026-05-28  
> **Pattern:** Diátaxis Framework (Tutorial-HowTo-Reference-Explanation)

---

## Quick Navigation

| I need to... | Go to |
|--------------|-------|
| Get started quickly | [`/getting-started/quickstart.md`](./getting-started/quickstart.md) |
| Understand the architecture | [`core-concepts/architecture.md`](./core-concepts/architecture.md) |
| Look up an API | [`reference/api-overview.md`](./reference/api-overview.md) |
| Solve a specific problem | [`/how-to-guides/`](./how-to-guides/) |
| Run / operate the platform | [`how-to-guides/operators.md`](./how-to-guides/operators.md) |
| Look up API/config details | [`/reference/`](./reference/) |
| Frontend query / state rules | [`reference/frontend-query-patterns.md`](./reference/frontend-query-patterns.md) |
| Testing strategy | [`reference/testing-strategy.md`](./reference/testing-strategy.md) |
| Where new code must live | [`reference/layer-runtime-path-governance.md`](./reference/layer-runtime-path-governance.md) |
| Fix something that's broken | [`/troubleshooting/`](./troubleshooting/) |
| Understand design decisions | [`/explanations/adr/`](./explanations/adr/) |
| Contribute to the project | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Find historical reports | [`archive/INDEX.md`](./archive/INDEX.md) |

---

## Documentation Organization

This documentation follows the **Diátaxis Framework**, organizing content by user need rather than by feature:

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOCUMENTATION TAXONOMY                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐  │
│  │   Tutorials  │  │  How-To      │  │  Reference   │  │Explanation│
│  │  (Learning)  │  │  (Tasks)      │  │  (Info)      │  │ (Understanding)│
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘  │
│         │                 │                │              │       │
│         ▼                 ▼                ▼              ▼       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐  │
│  │getting-started│  │how-to-guides │  │  reference   │  │explanations│
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘  │
│                                                                   │
│  Supporting: core-concepts · troubleshooting · governance         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

### `/getting-started/` — Onboarding Path
**Purpose:** Take a new user from zero to first success

| Document | Description | Time |
|----------|-------------|------|
| `quickstart.md` | 15-minute setup and first API call | 15 min |
| `environment.md` | Full installation with all options | 45 min |

**Principle:** No prerequisites assumed; every step explicit

---

### `/core-concepts/` — Foundational Knowledge
**Purpose:** Explain what Value Fabric is and how it works

| Document | Description | Audience |
|----------|-------------|----------|
| `architecture.md` | 6-layer pipeline architecture | All users |
| `security-model.md` | Authentication, authorization, audit | Developers |
| `ontology-system.md` | Entity types, relationships, extraction | Data scientists |

**Principle:** Concepts before tasks; theory supported by diagrams

---

### `/how-to-guides/` — Goal-Oriented Procedures
**Purpose:** Help users accomplish specific goals

| Document | Description | Complexity |
|----------|-------------|------------|
| `setup-local-dev.md` | Configure local development | Beginner |
| `configure-sso.md` | OIDC/SAML SSO setup | Intermediate |
| `drift-detection.md` | API contract, schema, and documentation drift detection | Intermediate |
| `operators.md` | Single jumping-off point for operator-facing runbooks | Intermediate |
| `role-onboarding.md` | Role-based onboarding | Intermediate |

**Principle:** Goal-focused; assumes prerequisite knowledge from core-concepts

---

### `/reference/` — Lookup Documentation
**Purpose:** Precise technical information

| Document | Description | Updates |
|----------|-------------|---------|
| `api-overview.md` | Multi-layer API structure and patterns | Per release |
| `testing-strategy.md` | Test pyramid and coverage requirements | Per release |
| `layer-runtime-path-governance.md` | Where new code must live per layer | Per change |
| `service-routing-and-api-version-matrix.md` | Service ports, base paths, and version compatibility | Per release |
| `frontend-query-patterns.md` | TanStack Query, Zustand, and generated-client rules | Per feature |
| `layer1-ingestion-api.md` | Layer 1 API reference | Per release |
| `layer2-extraction-api.md` | Layer 2 API reference | Per release |
| `layer3-knowledge-api.md` | Layer 3 API reference | Per release |
| `layer4-agents-api.md` | Layer 4 API reference | Per release |
| `layer5-ground-truth-api.md` | Layer 5 API reference | Per release |

**Principle:** Comprehensive but scannable; code examples for every endpoint

---

### `/troubleshooting/` — Problem Resolution
**Purpose:** Fix things when they go wrong

| Document | Description | Symptom |
|----------|-------------|---------|
| `index.md` | Troubleshooting decision tree | "Something's wrong" |
| `runbooks/` | Operational procedures | Service-specific issues |

**Principle:** Symptom-first organization; clear decision trees

---

### `/explanations/` — Deep Dives
**Purpose:** Understanding and context

| Document | Description | When to Read |
|----------|-------------|--------------|
| `adr/` | Architecture Decision Records | Evaluating choices |

**Principle:** Discussion and context; multiple valid viewpoints presented

---

### `/governance/` — Platform Governance
**Purpose:** Engineering governance and compatibility

| Document | Description |
|----------|-------------|
| `compatibility-debt-registry.md` | Canonical registry for compatibility shims |
| `launch-drift-prevention-sop.md` | Required approvals on contract/tenant/shim changes |
| `contract-exception-policy.md` | Contract exception policies |

---

### `/security/` — Security Documentation
**Purpose:** Security policies and procedures

| Document | Description |
|----------|-------------|
| `multi-tenancy.md` | Multi-tenant security architecture |
| `secrets-management.md` | Secret management policies |
| `secure-software-supply-chain.md` | Supply chain security |
| `token-contract.md` | Token contract specification |
| `threat-model.md` | Threat model analysis |

---

### `/operations/` — Operational Documentation
**Purpose:** Runbooks and operational procedures

| Document | Description |
|----------|-------------|
| `RELEASE_RUNBOOK.md` | Release procedures |
| `keycloak-integration.md` | Keycloak setup and configuration |
| `tenant-management-master-plan.md` | Tenant management plan |
| `runbooks/` | Operational runbooks |

---

## Documentation Standards

### YAML Frontmatter (Required)

Every document must include:

```yaml
---
title: "Value Fabric Documentation"
category: "meta"
audience: "all"
last-reviewed: "2026-05-28"
freshness: "current"
related: ["../README", "getting-started/quickstart", "core-concepts/architecture", "reference/api-overview", "troubleshooting/index"]
---
```

### Cross-Linking Requirement

Every document must link to 2-3 related documents:

```markdown
## Related Documentation

- [Prerequisites](./prerequisites.md) — Required setup before this guide
- [Architecture Overview](../core-concepts/architecture.md) — Understanding the system
- [API Reference](../reference/api-overview.md) — Endpoint details
```

### Diagram Standards

- **Tool:** Mermaid.js (version-controlled, editable)
- **Color Coding:**
  - 🔵 Blue: User actions
  - 🟢 Green: System processes
  - 🔴 Red: Errors/decision points
  - ⚪ Gray: External systems
- **Sizing:** Max-width 800px, zoom capability
- **Accessibility:** Alt-text descriptions required

---

## Freshness Tracking

| Status | Definition | Action Required |
|--------|------------|-----------------|
| 🟢 **Current** | Reviewed within 30 days | None |
| 🟡 **Needs Update** | Reviewed 30-90 days ago | Schedule review |
| 🔴 **Stale** | Not reviewed in 90+ days | Update or archive |

---

## Archive Policy

Outdated documentation moves to `/archive/YYYY-MM/`:

- Implementation-complete task documentation
- Superseded specifications
- Outdated analysis documents
- Abandoned drafts (>6 months)

See [Archive Registry](./archive/INDEX.md) for complete history.

---

## Success Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| P0 Docs Updated | 100% | 95% | ✅ Root cleanup completed 2026-05-28 |
| Docs with Diagrams | 80% | 30% | 🔄 In progress |
| Broken Links | 0 | 0 | ✅ All links verified |
| Root-level Files | <10 | 8 | ✅ Target achieved |
| Archive Hygiene | Current | ✅ | 🗄️ Archive policy working |

---

## Contributing to Documentation

See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for:
- Style guide and templates
- Markdown conventions
- Diagram creation guidelines
- Review process

---

## Questions?

- **Missing documentation?** Open an issue with `documentation` label
- **Found an error?** Submit a PR or issue
- **Need clarification?** Start a discussion

---

*This documentation is a living document. Last structural update: 2026-05-28*
```

---

## Key Changes from Current README

### Root README.md Changes:
1. **Removed:** Links to `ARCHITECTURE.md` (will be archived)
2. **Removed:** Quickstart section (replaced with link to docs/getting-started/quickstart.md)
3. **Removed:** Repository map table (consolidated into "Repository Map" section)
4. **Added:** "Core Concepts" section with 4 key documents
5. **Added:** "Developer Guide" section with 4 key documents
6. **Added:** "For AI Agents" section with 2 key documents
7. **Added:** "Operations" section with 4 key documents
8. **Added:** "Governance" section with 3 key documents
9. **Simplified:** Documentation section (link to docs/README.md)
10. **Removed:** Detailed API reference table (now in docs/reference/api-overview.md)

### docs/README.md Changes:
1. **Removed:** "Installation.md" (merged into quickstart.md)
2. **Removed:** "Prerequisites.md" (merged into quickstart.md)
3. **Removed:** "agent-framework.md" (not found in inventory)
4. **Added:** `/governance/` section
5. **Added:** `/security/` section
6. **Added:** `/operations/` section
7. **Updated:** Success metrics (root-level files: 24 → 8)
8. **Updated:** Last structural update date

---

## Verification Checklist

- [ ] All links point to existing files
- [ ] No placeholder links
- [ ] No "see wiki" hand-waving
- [ ] All high-density documents elevated
- [ ] Temporal reports not linked
- [ ] Archived files not linked
- [ ] Consolidation opportunities reflected in structure
- [ ] Diátaxis framework maintained

---

## Next Steps

**Implementation:**
1. Update root README.md with proposed structure
2. Update docs/README.md with proposed structure
3. Archive files marked for archival
4. Move JSON baselines to config/baselines/
5. Merge files marked for consolidation
6. Update links in all documents
7. Verify all links work

**Rollback Plan:**
- Keep git history for easy rollback
- Create branch for documentation cleanup
- Test all links before merging
- Get team approval before merging

---

## Summary

**Phase 1:** ✅ Inventory & Classification - 200+ files cataloged
**Phase 2:** ✅ Valuation & Triage - 20 high-value documents identified
**Phase 3:** ✅ Consolidation Opportunities - 10 consolidation opportunities identified
**Phase 4:** ✅ Archive vs Update Decision Matrix - 163 files affected
**Phase 5:** ✅ README as Navigation Layer - Proposed structure above

**Total Documentation Cleanup Workflow:** COMPLETE

**Recommendation:** Proceed with implementation in priority order:
1. Archive temporal reports (quick win, high impact)
2. Move JSON baselines to config/baselines/ (wrong location)
3. Update README files (user-facing)
4. Implement consolidations (medium effort)
5. Delete duplicate files (low effort)
