# Value Fabric Documentation

> **Organization Version:** 2.0  
> **Last Updated:** 2026-05-28  
> **Pattern:** Diátaxis Framework (Tutorial-HowTo-Reference-Explanation)

---

## Quick Navigation

| I need to... | Go to |
|--------------|-------|
| Get started quickly | [`/getting-started/quickstart.md`](./getting-started/quickstart.md) |
| Route an issue to implementation and validation | [`development/DISCOVERY_MAP.md`](./development/DISCOVERY_MAP.md) |
| Find local commands and gates | [`development/COMMANDS.md`](./development/COMMANDS.md) |
| Find CI workflow ownership and local validation | [`../.github/workflows/WORKFLOW_REGISTRY.md`](../.github/workflows/WORKFLOW_REGISTRY.md) |
| Understand the architecture | [`core-concepts/architecture.md`](./core-concepts/architecture.md) |
| Look up an API | [`reference/api-overview.md`](./reference/api-overview.md) |
| Solve a specific problem | [`/how-to-guides/`](./how-to-guides/) |
| Run / operate the platform | [`how-to-guides/operators.md`](./how-to-guides/operators.md) |
| Respond to incidents and runbooks | [`operations/runbooks/README.md`](./operations/runbooks/README.md) |
| Look up API/config details | [`/reference/`](./reference/) |
| Frontend query / state rules | [`reference/frontend-query-patterns.md`](./reference/frontend-query-patterns.md) |
| Testing strategy | [`reference/testing-strategy.md`](./reference/testing-strategy.md) |
| Find test inventory and quality posture | [`testing/test-inventory.md`](./testing/test-inventory.md) |
| Find validation and release evidence | [`validation/master_workflow_traceability_matrix.md`](./validation/master_workflow_traceability_matrix.md) |
| Where new code must live | [`reference/layer-runtime-path-governance.md`](./reference/layer-runtime-path-governance.md) |
| Review governance policy | [`governance.md`](./governance.md) |
| Review repository discoverability coverage | [`governance/repository-discoverability-audit.md`](./governance/repository-discoverability-audit.md) |
| Review security policy | [`security/multi-tenancy.md`](./security/multi-tenancy.md) |
| Review supply chain policy | [`supply-chain/SUPPLY_CHAIN_SECURITY.md`](./supply-chain/SUPPLY_CHAIN_SECURITY.md) |
| Fix something that's broken | [`/troubleshooting/`](./troubleshooting/) |
| Understand design decisions | [`/explanations/adr/`](./explanations/adr/) |
| Contribute to the project | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Find a historical report | [`archive/INDEX.md`](./archive/INDEX.md) |

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
│  Supporting: core-concepts · troubleshooting · contributing         │
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
last-reviewed: "2026-04-19"
freshness: "current"
related: ["../README", "getting-started/quickstart", "core-concepts/architecture", "reference/api-overview", "troubleshooting/index", "priority-update-log", "archive/archive-registry"]
---
```

### Cross-Linking Requirement

Every document must link to 2-3 related documents:

```markdown
## Related Documentation

- [Prerequisites](./prerequisites.md) — Required setup before this guide
- [Architecture Overview](../core-concepts/architecture.md) — Understanding the system
- [API Reference](../../API_REFERENCE.md) — Endpoint details
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

See [Archive Registry](./archive/archive-registry.md) for complete history.

Historical root-level quality reports are archived under [`/archive/quality-reports/`](./archive/quality-reports/).

---

## Success Metrics

| Metric | Target | Current | Notes |
|--------|--------|---------|-------|
| P0 Docs Updated | 100% | 100% | ✅ Root cleanup completed 2026-05-28 |
| Docs with Diagrams | 80% | 30% | 🔄 In progress |
| Broken Links | 0 | 0 | ✅ All links verified |
| Root-level Files | <10 | 6 | ✅ Target achieved (removed canonical-paths-policy.md, spec-round2-followup.md) |
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

### Recent Changes (2026-05-28)

- Archived 30+ temporal audit/assessment documents to `docs/archive/2026-05-28/`
- Moved 5 JSON baselines to `config/baselines/`
- Deleted duplicate `THREAT_MODEL.md` in docs/security/
- Updated root README.md with simplified structure
- Updated docs/README.md with new governance/security/operations sections
- Root-level docs reduced from 24 to 8 files

## Contributor Pathing Reference

- [Layer Runtime Path Governance Matrix](./reference/layer-runtime-path-governance.md) — Canonical vs legacy layer paths for contributors
