# Value Fabric Documentation

> **Organization Version:** 2.0  
> **Last Updated:** 2026-05-04  
> **Pattern:** Diátaxis Framework (Tutorial-HowTo-Reference-Explanation)

---

## Quick Navigation

| I need to... | Go to |
|--------------|-------|
| Get started quickly | [`/getting-started/`](./getting-started/) |
| Understand the architecture | [`core-concepts/architecture.md`](./core-concepts/architecture.md) |
| Look up an API | [`API_REFERENCE.md`](./API_REFERENCE.md) (human-readable) · [`/contracts/openapi/`](../contracts/openapi/) (authoritative) |
| Solve a specific problem | [`/how-to-guides/`](./how-to-guides/) |
| Run / operate the platform | [`how-to-guides/operators.md`](./how-to-guides/operators.md) |
| Look up API/config details | [`/reference/`](./reference/) |
| Frontend query / state rules | [`reference/frontend-query-patterns.md`](./reference/frontend-query-patterns.md) |
| Testing strategy | [`reference/testing-strategy.md`](./reference/testing-strategy.md) |
| Where new code must live | [`reference/layer-runtime-path-governance.md`](./reference/layer-runtime-path-governance.md) |
| Fix something that's broken | [`/troubleshooting/`](./troubleshooting/) |
| Understand design decisions | [`/explanations/`](./explanations/) · [`/explanations/adr/`](./explanations/adr/) |
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
| `installation.md` | Full installation with all options | 45 min |
| `prerequisites.md` | Required skills, tools, and accounts | 10 min |

**Principle:** No prerequisites assumed; every step explicit

---

### `/core-concepts/` — Foundational Knowledge
**Purpose:** Explain what Value Fabric is and how it works

| Document | Description | Audience |
|----------|-------------|----------|
| `architecture.md` | 6-layer pipeline architecture | All users |
| `security-model.md` | Authentication, authorization, audit | Developers |
| `ontology-system.md` | Entity types, relationships, extraction | Data scientists |
| `agent-framework.md` | How agents reason and orchestrate | AI engineers |

**Principle:** Concepts before tasks; theory supported by diagrams

---

### `/how-to-guides/` — Goal-Oriented Procedures
**Purpose:** Help users accomplish specific goals

| Document | Description | Complexity |
|----------|-------------|------------|
| `setup-local-dev.md` | Configure local development | Beginner |
| `deploy-to-k8s.md` | Production Kubernetes deployment | Advanced |
| `configure-sso.md` | OIDC/SAML SSO setup | Intermediate |
| `manage-secrets.md` | Vault and secret rotation | Intermediate |
| `author-value-pack.md` | Create domain-specific packs | Intermediate |

**Principle:** Goal-focused; assumes prerequisite knowledge from core-concepts

---

### `/reference/` — Lookup Documentation
**Purpose:** Precise technical information

| Document | Description | Updates |
|----------|-------------|---------|
| `api-reference.md` | Complete API endpoint docs | Per release |
| `cli-reference.md` | Command-line tools | Per release |
| `configuration.md` | Environment variables, config files | Per change |
| `frontend-navigation.md` | UI screen reference | Per feature |

**Principle:** Comprehensive but scannable; code examples for every endpoint

---

### `/troubleshooting/` — Problem Resolution
**Purpose:** Fix things when they go wrong

| Document | Description | Symptom |
|----------|-------------|---------|
| `index.md` | Troubleshooting decision tree | "Something's wrong" |
| `service-down.md` | Service unavailable recovery | 503 errors |
| `database-connection.md` | PostgreSQL/Neo4j issues | Connection timeouts |
| `authentication-errors.md` | JWT/API key problems | 401/403 errors |

**Principle:** Symptom-first organization; clear decision trees

---

### `/how-to-guides/` — Drift Detection
**Purpose:** Detect and prevent drift between code, contracts, and documentation

| Document | Description | When to Use |
|----------|-------------|-------------|
| `drift-detection.md` | API contract, schema, and documentation drift detection | After code changes, before releases |

**Principle:** Automated detection with clear remediation paths

---

### `/explanations/` — Deep Dives
**Purpose:** Understanding and context

| Document | Description | When to Read |
|----------|-------------|--------------|
| `adr/` | Architecture Decision Records | Evaluating choices |
| `why-knowledge-graph.md` | Graph vs relational tradeoffs | Database decisions |
| `security-threat-model.md` | Attack vectors and mitigations | Security reviews |
| `performance-characteristics.md` | Latency, throughput, scaling | Capacity planning |

**Principle:** Discussion and context; multiple valid viewpoints presented

---

### `/contributing/` — Contribution Guide
**Purpose:** Enable community contributions

| Document | Description | Audience |
|----------|-------------|----------|
| `guidelines.md` | How to contribute code/docs | External devs |
| `style-guide.md` | Code and documentation standards | All contributors |
| `local-setup.md` | Development environment | New contributors |

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
- [API Reference](../reference/api-reference.md) — Endpoint details
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
| P0 Docs Updated | 100% | 85% | ✅ Root cleanup completed 2026-04-27 |
| Docs with Diagrams | 80% | 25% | 🔄 In progress |
| Avg Time-to-Information | -40% | TBD | ⏳ Pending measurement |
| Broken Links | 0 | 1 | ⚠️ api-overview.md link verified (exists) |
| Root-level Files | <10 | 24 | 🔄 17 archived, 4 relocated |
| Archive Hygiene | Current | ✅ | 🗄️ 27 files archived across 2 rounds |

---

## Contributing to Documentation

See [`/contributing/`](./contributing/) for:
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

*This documentation is a living document. Last structural update: 2026-04-27*

### Recent Changes (2026-04-27)

- Archived 17 temporal audit/assessment documents to `docs/archive/2026-04-27/`
- Deleted 1 CI artifact (`GATE_TEST_RESULTS.txt`)
- Moved 4 reference documents to proper `docs/` subdirectories
- Merged `THREAT_MODEL.md` into `docs/core-concepts/security-model.md`
- Root-level docs reduced from 41 to 24 files

## Contributor Pathing Reference

- [Layer Runtime Path Governance Matrix](./reference/layer-runtime-path-governance.md) — Canonical vs legacy layer paths for contributors
