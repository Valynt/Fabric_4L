# Fabric 4L

> **Enterprise agentic SaaS platform that transforms unstructured data into structured knowledge through ontology-guided AI pipelines.**

Six-layer architecture — from ingestion to benchmarks — built for teams that need to turn documents, transcripts, and unstructured sources into queryable, verifiable knowledge graphs at production scale.

---

<p align="center">
  <a href="https://github.com/bmsull560/Fabric_4L/actions/workflows/pr-checks.yml">
    <img src="https://github.com/bmsull560/Fabric_4L/actions/workflows/pr-checks.yml/badge.svg" alt="CI">
  </a>
  <a href="https://codecov.io/gh/bmsull560/Fabric_4L">
    <img src="https://img.shields.io/codecov/c/github/bmsull560/Fabric_4L" alt="Coverage">
  </a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/node-22%2B-green" alt="Node 22+">
  <a href="https://github.com/bmsull560/Fabric_4L/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/bmsull560/Fabric_4L" alt="License">
  </a>
  <a href="https://github.com/bmsull560/Fabric_4L/releases">
    <img src="https://img.shields.io/github/v/release/bmsull560/Fabric_4L" alt="Release">
  </a>
</p>

---

## Quickstart (Canonical Development Environment)

Fabric_4L uses Dev Containers as the single canonical development environment to eliminate toolchain drift across contributors and AI agents. The container provides all pinned dependencies (Python 3.11, Node 22, pnpm, uv, rootless Docker-in-Docker, kubectl, Infisical, cosign, etc.) out of the box.

### 1. Launch Canonical Dev Container

Prerequisites on host: Git and Docker Engine (or Docker Desktop / Nebius VM bootstrapped via [`infra/nebius/cloud-init.yaml`](infra/nebius/README.md)).

```bash
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash
```

*Alternatively, open in VS Code / Cursor and select **"Reopen in Container"** or launch via [GitHub Codespaces](.github/codespaces.md).*

### 2. Verify and Develop

The devcontainer automatically runs bootstrap and environment verification on creation:

```bash
# Verify all toolchains and rootless DinD connectivity:
.devcontainer/verify.sh

# Start development services inside container:
.devcontainer/dev-stack.sh infra     # PostgreSQL, Redis, Neo4j
.devcontainer/dev-stack.sh migrate   # Run database migrations
make verify                          # Run platform verification
```

For detailed architecture commands, see [docs/development/DEV_CONTAINERS.md](docs/development/DEV_CONTAINERS.md), [docs/development/BUILD_SYSTEM.md](docs/development/BUILD_SYSTEM.md), and [docs/development/COMMANDS.md](docs/development/COMMANDS.md).

---

## Architecture

Fabric 4L processes unstructured data through six specialized layers. Each layer is a horizontally scalable service with its own API, storage, and deployment configuration.

```mermaid
graph LR
  A[L1: Ingestion] --> B[L2: Extraction]
  B --> C[L3: Knowledge]
  C --> D[L4: Agents]
  D --> E[L5: Ground Truth]
  E --> F[L6: Benchmarks]
```

| Layer | Purpose | Key Tech |
|-------|---------|----------|
| **L1: Ingestion** | Multi-format document intake, parsing, and chunking | Python, FastAPI, Redis queues |
| **L2: Extraction** | Entity, relationship, and ontology extraction from chunks | LangGraph pipelines, LLM orchestration |
| **L3: Knowledge** | Knowledge graph construction, deduplication, and persistence | Neo4j, Cypher, graph embeddings |
| **L4: Agents** | Autonomous reasoning agents that operate over the knowledge graph | LangGraph, tool-calling, multi-agent |
| **L5: Ground Truth** | Human-in-the-loop validation, feedback collection, and corrections | PostgreSQL RLS, review workflows |
| **L6: Benchmarks** | Performance measurement, regression detection, and reporting | Prometheus, Grafana, custom metrics |

---

## Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui |
| **Graph Database** | Neo4j 5.x with Cypher |
| **Relational Database** | PostgreSQL 15 with Row-Level Security |
| **Cache & Queues** | Redis 7 |
| **AI / ML** | LangGraph, OpenAI/Anthropic models, sentence-transformers |
| **Orchestration** | Kubernetes, Helm |
| **Observability** | Prometheus, Grafana, structured logging |
| **DevOps** | Docker, GitHub Actions, Makefile-driven workflows |

---

## Enterprise Readiness

- **Multi-tenant** — Tenant isolation enforced at the PostgreSQL RLS layer, with schema-per-tenant support
- **SOC 2 Prep** — Controls documented in `compliance/`, audit trails on all data mutations
- **Kubernetes-native** — Helm charts, HPA, PDBs, and health checks in `k8s/`
- **Contract-governed** — Layer-to-layer contracts defined, versioned, and tested via `make contract-tests`

---

## Project Stats

| Metric | Value |
|--------|-------|
| Contributors | 8 |
| Commits | 3,095 |
| Languages | Python 75.2%, TypeScript 21.5%, Other 3.3% |
| Container Images | 7 |
| Latest Release | v1.2.0 |

---

## Directory Structure

```
Fabric_4L/
├── apps/
│   └── web/                    # React frontend (Vite + TypeScript)
├── services/
│   ├── layer1-ingestion/       # L1: Document intake & parsing
│   ├── layer2-extraction/      # L2: Entity & relationship extraction
│   ├── layer3-knowledge/       # L3: Knowledge graph construction
│   ├── layer4-agents/          # L4: Autonomous agent runtime
│   ├── layer5-ground-truth/    # L5: Human validation workflows
│   └── layer6-benchmarks/      # L6: Performance & regression testing
├── packages/
│   ├── shared-models/          # Pydantic models shared across layers
│   ├── shared-config/          # Configuration schemas and loaders
│   └── shared-testing/         # Test fixtures, factories, utilities
├── docs/                       # Architecture docs, runbooks, ADRs
├── k8s/                        # Helm charts and Kubernetes manifests
├── monitoring/                 # Prometheus rules, Grafana dashboards, alerts
├── compliance/                 # SOC 2 controls, audit logs, policies
├── infra/                      # Docker Compose, Terraform, networking
├── .devcontainer/              # VS Code dev container config
└── Makefile                    # Primary interface: make verify, make test, etc.
```

---

## Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 22+
- Make

### Common Commands

| Command | What it does |
|---------|--------------|
| `make setup` | Install Python service development dependencies |
| `make verify` | Run full validation (tests + lint + typecheck + contracts) |
| `make test` | Run unit and integration tests |
| `make contract-tests` | Validate layer-to-layer API contracts |
| `make migrate` | Apply database migrations |
| `make lint` | Run ruff (Python) and eslint (TypeScript) |
| `make typecheck` | Run mypy and tsc |
| `make production-readiness-gate` | Full production gate — CI runs this on every PR |

### Dev Container / Codespaces

Open this repo in [GitHub Codespaces](https://codespaces.new/bmsull560/Fabric_4L) for a fully configured environment. The dev container installs all dependencies, starts PostgreSQL/Neo4j/Redis, and runs migrations automatically. See [codespaces.md](codespaces.md) for details.

---

## License & Governance

- **License:** [MIT](LICENSE)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** See [SECURITY.md](SECURITY.md) for vulnerability reporting
- **Code of Conduct:** See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

<p align="center">
  Built with care by the <strong>Fabric 4L</strong> team.
</p>
