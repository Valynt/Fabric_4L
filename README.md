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

Frontend workspace (`apps/web`) follows the same policy:

```bash
# Install from monorepo root (recommended)
pnpm install

# Or install only the frontend workspace
pnpm --dir apps/web install
```

## Canonical Build Commands

The Makefile is the canonical build, test, migration, contract, and release gate interface.
Root `pnpm` scripts are stable package-manager, frontend, or CI-parity aliases; direct Python CI
runners are reserved for reproducing workflow behavior. See
[`docs/development/BUILD_SYSTEM.md`](docs/development/BUILD_SYSTEM.md) for the hierarchy and
[`docs/development/COMMANDS.md`](docs/development/COMMANDS.md) for the complete command map.

## Quickstart (5 minutes)

### 1. Clone and configure
```bash
git clone https://github.com/bmsull560/Fabric_4L.git && cd Fabric_4L
cp .env.example .env
# Fill in OPENAI_API_KEY and JWT_SECRET
```

### 2. Select Python 3.11

The backend services declare `requires-python = ">=3.11"`; any supported Python 3.11+ patch release is acceptable. The root `.python-version` tracks the `3.11` series so pyenv users do not need the exact `3.11.10` patch. The `Makefile` resolves `python3.11` first and then falls back only to `python3`/`python` interpreters that report Python 3.11 or newer; override it with `make PYTHON=/path/to/python3.11 ...` if your local shim path is unusual.

```bash
# Optional for pyenv users; skip if python3.11 already resolves on PATH
pyenv install --skip-existing "$(pyenv latest -k 3.11)"
pyenv local 3.11
# Or choose any installed 3.11.x patch explicitly if your pyenv does not support series aliases.
```

### 3. Start infrastructure
```bash
docker compose -f docker-compose.full.yml up -d
```

### 4. Run migrations
```bash
make migrate
```

### 5. Verify everything works
```bash
make verify
```

### 6. Open the UI
```bash
open http://localhost:5173
```

**For detailed setup instructions:** See [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md)

## Repository map

Per **[ADR-021](docs/explanations/adr/ADR-021-layer-3-canonical-runtime-path.md)**, the
canonical implementation tree is `services/`. The `value_fabric/layer*/`
packages are **namespace shims only** that re-export from the matching service
package. See **[Layer Runtime Path Governance](docs/reference/layer-runtime-path-governance.md)**
for the full matrix (canonical paths, allowed new-development targets, and
shim-removal review dates).

| Path | Status | Purpose |
|------|--------|---------|
| `services/layer1-ingestion/src/` | **Canonical** | Layer 1 ingestion runtime |
| `services/layer2-extraction/src/` | **Canonical** | Layer 2 extraction runtime |
| `services/layer3-knowledge/src/` | **Canonical** | Layer 3 knowledge / retrieval runtime |
| `services/layer4-agents/src/` | **Canonical** | Layer 4 agent orchestration runtime |
| `services/layer5-ground-truth/src/layer5_ground_truth/` | **Canonical** | Layer 5 ground-truth runtime |
| `services/layer6-benchmarks/src/` | **Canonical** | Layer 6 benchmark runtime |
| `services/api/` | **Maintained** | Cross-layer API service |
| `value_fabric/layer1/` … `value_fabric/layer6/` | **Shim only (per ADR-027)** | Namespace facades; no net-new logic. Shim-removal review by 2026-09-30. |
| `value_fabric/shared/` | **Canonical** | Shared runtime packages (identity, security, models, boundaries) |
| `apps/web/` | **Canonical** | React + TypeScript UI |
| `contracts/` | **Canonical** | Versioned tool manifests, JSON Schemas, OpenAPI specs |
| `k8s/` | **Canonical** | Kubernetes manifests |
| `monitoring/` | **Canonical** | Prometheus + Grafana dashboards |
| `packs/` | **Canonical** | Domain-specific data packs (life-sciences, manufacturing, software) |
| `docs/` | **Canonical** | Architecture docs and runbooks |
| `tests/` | **Canonical** | Cross-layer integration and agent evaluation tests |
| `.github/workflows/` | **Canonical** | CI pipelines |

### Source of truth paths

All net-new runtime code lands under `services/layer{N}-*/src/`. Cross-layer
imports may use either the service package (`layer{N}_{name}.*`) or the
`value_fabric.layer{N}.*` shim during transition — the shim resolves to the
same module objects. See the path governance matrix for layer-specific notes.

### Per-layer contributor rule

For every layer 1–6: place all runtime implementation changes under
`services/layer{N}-*/src/`. Do **not** add new logic under
`value_fabric/layer{N}/` — those packages are namespace shims (per ADR-027)
and CI enforces this via
[`scripts/ci/check_layer6_wrapper_drift.py`](scripts/ci/check_layer6_wrapper_drift.py),
[`scripts/check_mirrored_files.py`](scripts/check_mirrored_files.py), and the
import-topology tests under [`tests/arch/`](tests/arch/) and
[`tests/contract/`](tests/contract/).

## Core Concepts

| Document | Description |
|----------|-------------|
| [System Architecture](docs/core-concepts/architecture.md) | 6-layer pipeline architecture |
| [Canonical Platform Contract](docs/contract.md) | Enforced direction for 6 cross-layer concerns |
| [Architecture Decision Records](docs/explanations/adr/) | Historical design decisions and rationale |
| [Security Model](docs/core-concepts/security-model.md) | Authentication, RBAC, and tenant isolation |
| [Ontology System](docs/core-concepts/ontology-system.md) | Entity taxonomy and extraction pipeline |

## Developer Guide

| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup and contribution guide |
| [AGENTS.md](AGENTS.md) | AI agent reference |
| [Layer Runtime Path Governance](docs/reference/layer-runtime-path-governance.md) | Where new code must live per layer |
| [Testing Strategy](docs/reference/testing-strategy.md) | Test pyramid and coverage requirements |
| [DESIGN.md](DESIGN.md) | Frontend governance contract for apps/web/ |

## API Reference

| Document | Description |
|----------|-------------|
| [API Reference Overview](docs/reference/api-overview.md) | Multi-layer API structure and patterns |
| [Layer 1 Ingestion API](docs/reference/layer1-ingestion-api.md) | Ingestion service endpoints |
| [Layer 2 Extraction API](docs/reference/layer2-extraction-api.md) | Extraction service endpoints |
| [Layer 3 Knowledge API](docs/reference/layer3-knowledge-api.md) | Knowledge graph endpoints |
| [Layer 4 Agents API](docs/reference/layer4-agents-api.md) | Agent workflow endpoints |
| [Layer 5 Ground Truth API](docs/reference/layer5-ground-truth-api.md) | Ground truth validation endpoints |
| [Frontend Query Patterns](docs/reference/frontend-query-patterns.md) | TanStack Query, Zustand, and generated-client rules |

## Operations

| Document | Description |
|----------|-------------|
| [Release Runbook](docs/operations/RELEASE_RUNBOOK.md) | Release procedures |
| [Operator Runbooks](docs/how-to-guides/operators.md) | Single jumping-off point for operator-facing runbooks |
| [Troubleshooting Guide](docs/troubleshooting/index.md) | Decision trees and common issues |
| [Keycloak Integration](docs/operations/keycloak-integration.md) | Keycloak setup and configuration |

## Governance

| Document | Description |
|----------|-------------|
| [Compatibility Debt Registry](docs/governance/compatibility-debt-registry.md) | Canonical registry for compatibility shims |
| [Launch Drift Prevention SOP](docs/governance/launch-drift-prevention-sop.md) | Required approvals on contract/tenant/shim changes |
| [Contract Governance](contracts/GOVERNANCE.md) | How API contracts evolve |

## Security

| Document | Description |
|----------|-------------|
| [SECURITY.md](SECURITY.md) | Security policy and vulnerability reporting |
| [Security Documentation](docs/security/) | Multi-tenancy, secrets management, threat model |

## Documentation

📚 **[Complete Documentation →](docs/README.md)**

Our documentation follows the [Diátaxis Framework](https://diataxis.fr/) with tutorials, how-to guides, reference, and explanations.

## Archived Documentation

🗄️ **[Archived Documentation →](docs/archive/INDEX.md)**

Historical reports, superseded specifications, and outdated analysis documents retained for traceability.

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
