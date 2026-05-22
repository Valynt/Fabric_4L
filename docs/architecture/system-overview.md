# Value Fabric — Architecture

## Overview

Value Fabric is an AI-powered value selling platform built on a **6-layer pipeline architecture** plus a React frontend that transforms raw, unstructured data into actionable business intelligence. Each layer is an independently deployable microservice with its own Docker Compose configuration, API surface, and test suite.

The architecture follows the [Platform Contract](packages/platform-contract/CONTRACT.md) which governs all cross-layer patterns including tenant context propagation, database sessions, middleware flows, and API boundaries.

```
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

---

## Platform Contract

All cross-layer implementation patterns are governed by the **Platform Contract** at `packages/platform-contract/CONTRACT.md`. This contract is enforced by CI and violations block merge.

### Core Principles

| Principle | Implementation |
|-----------|---------------|
| **Context is explicit** | Typed `RequestContext` via GovernanceMiddleware; single ContextVar for async propagation |
| **Fail-safe defaults** | Missing tenant context → reject; missing auth → reject |
| **One dependency, one lifetime** | DB session created once per request, committed once, rolled back on exception |
| **Schema-first at boundaries** | Every tool, agent output, and API response has declared Pydantic schema |
| **Traceability mandatory** | Every request carries `trace_id`; every agent run carries `workflow_id` |
| **Frontend: route-driven** | URL is primary navigation; Zustand stores are typed; server state in React Query |

### Tenant Context Propagation

```python
# Canonical pattern for endpoints
from shared.identity.dependencies import get_request_context
from shared.identity.context import RequestContext

@router.get('/items')
async def list_items(ctx: RequestContext = Depends(get_request_context)):
    tenant_id = ctx.tenant_id  # Guaranteed to be set
    ...
```

---

## Multi-Tenant Architecture

Value Fabric implements **PostgreSQL Row-Level Security (RLS)** for multi-tenancy, combined with **composite unique constraints** in Neo4j.

### PostgreSQL RLS

- Tenant isolation via `SET LOCAL app.tenant_id` per session
- Policies restrict rows based on `tenant_id` column
- Application-level middleware sets tenant context automatically

### Neo4j Tenant Scoping

- All entities and relationships include `tenant_id` property
- Composite unique constraints on `(id, tenant_id)` for all entity types
- Same `id` allowed across different tenants
- Community Edition compatible (no enterprise-only features required)

See [ADR-003](docs/explanations/adr/ADR-009-postgresql-rls-multi-tenancy.md) for detailed design.

---

## Layer 1 — Intelligent Data Ingestion Service

**Build order:** Phase 4
**Status:** ✅ Complete
**Port:** 8001 (host-mapped from container port 8000)

### Purpose

Convert unstructured source materials (web pages, SEC filings, PDFs, APIs) into clean, normalized Markdown documents with full metadata, compliance auditing, and multi-tenant isolation.

### Components

| Component | Responsibility |
|-----------|---------------|
| **Scheduler Service** | Determines crawl targets and priorities |
| **Crawler Workers** | Headless Playwright browser instances executing extraction |
| **Post-Processor** | Cleans, deduplicates, and normalizes raw content to Markdown |
| **Source Registry** | Document metadata, freshness tracking, access URLs |
| **Compliance Auditor** | robots.txt validation, rate limit enforcement, PII detection |

### Data Sources

| Priority | Sources |
|----------|---------|
| 1 | Corporate websites, SEC EDGAR filings (10-K/10-Q), earnings call transcripts |
| 2 | Competitor documentation, industry analyst reports, patent filings |
| 3 | LinkedIn company pages, news mentions (NewsAPI) |

### Compliance (Non-Negotiable)

- **robots.txt** parsing with 24-hour cache; never crawl Disallow paths
- **Rate limiting:** Global 1,000 req/min; per-domain 1 req/sec with 20% jitter
- **PII detection** with Microsoft Presidio — redact SSN, credit cards, phone, email; block pages with > 3 PII entities
- **Audit log:** URL, timestamp, IP, bytes downloaded, outcome (7-year retention)

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/ingestion/targets` | Create scraping target |
| `GET /api/v1/ingestion/targets` | List targets with filters |
| `POST /api/v1/ingestion/jobs` | Start scraping job |
| `GET /api/v1/ingestion/jobs/{id}` | Get job status and progress |
| `GET /api/v1/ingestion/content/{id}` | Retrieve Markdown + metadata |
| `DELETE /api/v1/ingestion/content/{id}` | Soft delete with 30-day retention |
| `GET /api/v1/ingestion/compliance/logs` | Compliance audit trail |

### Acceptance Criteria

- ≥ 1,000 pages/day throughput
- Zero robots.txt violations
- > 95% PII detection accuracy
- ≥ 4/5 Markdown readability score
- 99.5% API uptime

---

## Layer 2 — Ontology-Guided Extraction Pipeline

**Build order:** Phase 1 (built first)
**Status:** ✅ Complete
**Port:** 8002

### Purpose

Extract structured entities and relationships from ingested Markdown using LLMs, then serialize results as RDF/OWL with full provenance. Includes direct Layer 3 ingestion capability via `extract-and-ingest` endpoint.

### Core Ontology (Pydantic v2 Models)

```
Capability → UseCase → Persona → ValueDriver
   ↓           ↓          ↓           ↓
[What we]  [How it's] [Who]     [Business]
[do]       [used]     [benefits] [outcome]
```

**Entity types:**

| Type | Description |
|------|-------------|
| `Capability` | Technical features or abilities (e.g., "Real-Time Data Ingestion") |
| `UseCase` | Business problem scenarios (e.g., "Touchless Accounts Payable") |
| `Persona` | Stakeholder roles: `economic_buyer`, `operational_user`, `stakeholder` |
| `ValueDriver` | Quantifiable outcomes: `revenue`, `cost`, `risk`, `capital` |

**Relationship types:** `enables`, `requires`, `benefits`, `drives`, `contributes_to`, `depends_on`, `alternative_to`

### Extraction Pipeline (6 Stages)

1. **Chunking & Preprocessing** — LangChain `RecursiveCharacterTextSplitter`; 2,000-token chunks, 200-token overlap
2. **Entity Extraction (LLM Call 1)** — GPT-4o or Claude 3.5 Sonnet; temperature 0.0; confidence threshold 0.8
3. **Relationship Extraction (LLM Call 2)** — Evidence-backed only; confidence threshold 0.75
4. **Semantic Alignment & Deduplication** — `text-embedding-3-large`; similarity threshold 0.85
5. **Validation & Normalization** — Pydantic schema validation; resolve all ID references
6. **RDF/OWL Serialization** — Turtle format; PROV-O provenance metadata; OWL axioms

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/extract` | Start extraction job |
| `GET /v1/extract/status/{id}` | Check job status |
| `POST /v1/extract/batch` | Batch extraction |
| `POST /v1/extract-and-ingest` | Extract + push to Layer 3 in one call |
| `GET /v1/ontology/entities` | List entities |
| `GET /v1/audit/trace/{id}` | Full provenance trace |

### Layer 2 → Layer 3 Integration

The `extract-and-ingest` endpoint uses `Layer3KnowledgeClient` to push RDF data directly to Layer 3:

```python
# Batching for large extractions (default 100)
# Retry with exponential backoff (max 3)
# Env vars: LAYER3_API_URL, LAYER3_API_KEY
```

### Acceptance Criteria

- > 95% Pydantic schema compliance
- Zero hallucinated entity types
- > 90% deduplication accuracy
- > 85% relationship precision (evidence-supported)
- 100 documents/hour per worker
- RDF validates with Apache Jena

---

## Layer 3 — Knowledge Graph & Semantic Layer

**Build order:** Phase 2 (after Layer 2)
**Status:** ✅ Complete
**Port:** 8003

### Purpose

Store, index, and query the structured knowledge graph; support GraphRAG and hybrid vector + graph retrieval. Provides coherent subgraph API for frontend visualization.

### Data Model

**Nodes:** `:Capability`, `:UseCase`, `:Persona`, `:ValueDriver`, `:Formula`, `:Industry`, `:GroundTruth`

**Relationships:**

| Relationship | Direction |
|-------------|-----------|
| `ENABLES` | Capability → UseCase |
| `BENEFITS` | UseCase → Persona |
| `DRIVES` | UseCase → ValueDriver |
| `CONTRIBUTES_TO` | ValueDriver → ValueDriver (hierarchical) |
| `HAS_FORMULA` | ValueDriver → Formula |
| `APPLIES_TO` | Benchmark → Industry |
| `GROUNDS` | GroundTruth → (Capability/Outcome/ValueDriver/Persona) |

**Node properties:** `embedding` (1,536-dim), `confidence`, `source_url`, `extracted_at`, `tenant_id`

### GraphRAG Implementation

**Indexing Phase:**
- Entity embeddings stored in vector index
- Leiden community detection (Neo4j GDS)
- LLM-generated community summaries
- Hierarchical index built

**Retrieval Phase:**
- Vector search (cosine similarity) → entry nodes
- Graph traversal (BFS/DFS, max 3 hops) → connected subgraphs
- Reranking by relevance
- Citation support with source nodes

**Global Queries:** Use community summaries for broad questions (no vector search required)

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/query/graph` | GraphRAG traversal with citations |
| `POST /v1/search/hybrid` | Vector + graph hybrid search |
| `POST /v1/ingest` | Ingest RDF from Layer 2 |
| `GET /v1/entities` | List entities |
| `GET /v1/graph/subgraph` | **NEW:** Coherent subgraph for visualization |
| `GET /v1/value-trees/{entity_id}` | Build full value chain from any node |
| `GET /v1/formulas` | List formulas |
| `POST /v1/formulas/evaluate` | Evaluate formula with variables |
| `GET /v1/health` / `GET /v1/health/detailed` | Health checks |

### Subgraph API

The `/v1/graph/subgraph` endpoint returns coherent node+edge sets for frontend visualization:

```python
# Query Mode: ?query=search_term&depth=2
# Center Mode: ?center_entity_id=xxx&depth=2
# Returns: { nodes: [...], edges: [...], stats: {...} }
```

### Performance Targets

| Query Type | Latency (p95) |
|-----------|--------------|
| Single-hop | < 50 ms |
| Multi-hop (3 levels) | < 200 ms |
| Vector + graph hybrid | < 500 ms |
| Concurrent connections | 1,000+ |
| Graph size | 10M nodes, 100M relationships |

### Acceptance Criteria

- > 90% multi-hop reasoning accuracy (vs. 60% vector-only baseline)
- Zero Cypher injection (pen tested)
- Semantic consistency: same metric = same value
- Full provenance trace < 500 ms

---

## Layer 4 — Agentic Workflow Engine

**Build order:** Phase 3 (after Layer 3)
**Status:** ✅ Complete
**Port:** 8004 (host-mapped from container port 8000)

### Purpose

Execute composable AI workflows for whitespace analysis, ROI calculation, business case generation, and provenance auditing. Uses LangGraph for checkpointed, resumable workflows with human-in-the-loop gates.

### Agent Workflows

#### Workflow 1: Whitespace Analysis
`IngestProspect → ExtractInsights → MapToCapabilities → IdentifyWhitespace → GeneratePlan`
**Output:** JSON account plan with whitespace opportunities, stakeholder map, entry strategy

#### Workflow 2: Dynamic ROI Calculator
Retrieves Value Tree from graph → safely evaluates formula strings (numexpr) → Monte Carlo sensitivity analysis
**Output:** Deterministic ROI projection + risk assessment (best/worst/expected cases)

#### Workflow 3: Business Case Generator
Auto-generates Executive Summary, Current State, Proposed Solution, Financial Analysis, Risk Mitigation, Next Steps
**Formats:** Markdown, DOCX, PDF, PPTX (10–15 slides)

#### Workflow 4: Provenance Audit Agent
Traverses PROV-O graph backward showing LLM calls → extractions → source documents with confidence scores at each step

### Skill Tiers

| Tier | Skills |
|------|--------|
| 1: Knowledge Navigation | `/graph_traverse`, `/semantic_search`, `/resolve_value_tree`, `/find_path` |
| 2: Reasoning | `/multi_hop_reason`, `/analyze_gaps` |
| 3: Calculation | `/evaluate_formula`, `/sensitivity_analysis` |
| 4: Content Generation | `/build_narrative`, `/generate_business_case`, `/write_executive_summary` |
| 5: Research | `/research_web`, `/analyze_competitor`, `/enrich_industry_context` |
| 6: Audit | `/trace_provenance`, `/escalate_to_human` |
| 7: Meta | `/value_fabric_help` |

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/workflows/whitespace` | Start whitespace analysis workflow |
| `POST /v1/workflows/roi` | Execute ROI calculation |
| `POST /v1/workflows/business-case` | Generate business case document |
| `GET /v1/workflows/{id}/status` | Poll workflow status |
| `POST /v1/workflows/{id}/approve` | Human-in-the-loop approval gate |
| `GET /v1/checkpoints/{workflow_id}` | Resume from checkpoint |
| `POST /v1/tools/{tool_name}/invoke` | Direct tool invocation |
| `GET /v1/health` | Health check with component status |
| `GET /v1/health/badges` | Component health badges for UI |

### Workflow Checkpoints

LangGraph provides checkpointed state for long-running workflows:

```python
# PostgreSQL-backed checkpoint storage
# Automatic resume on service restart
# Human-in-the-loop pause points
```

See [ADR-004](docs/explanations/adr/ADR-010-langgraph-workflow-orchestration.md) for workflow design.

### Acceptance Criteria

- Whitespace analysis: < 5 minutes end-to-end
- ROI calculations deterministic (same inputs → same outputs)
- Business case documents rated ≥ 4/5 by sales team
- 99% workflow completion rate
- All actions logged with PROV-O metadata

---

## Layer 5 — Ground Truth

**Status:** ✅ Complete
**Port:** 8005

### Purpose

Evidence-backed, CFO-defensible facts for the Value Fabric platform. Stores, validates, and governs factual claims extracted from customer conversations, documents, and web content. Every claim has traceable provenance, confidence score, and maturity level.

### Core Concepts

#### TruthObject

A structured, evidence-backed factual claim with validation state machine:

| Field | Description |
|-------|-------------|
| `claim` | Plain-language factual statement |
| `claim_type` | Semantic category (`efficiency_gain`, `cost_savings_baseline`) |
| `value` | Structured value (amount, unit, period) |
| `confidence` | 0.0–1.0 score from extraction model |
| `status` | Validation state (see state machine) |
| `maturity_level` | 0–5 maturity ladder position |
| `sources` | Evidence sources (call transcripts, documents, web pages) |
| `applies_to` | Scoping context (opportunity_id, account_id, persona_id) |

#### Validation State Machine

```
EXTRACTED → SUPPORTED → CORROBORATED → APPROVED → OPERATIONALIZED
                │              │              │
                └──────────────┴──────────────┘──► DISPUTED → CORROBORATED
```

| Level | Name | Description |
|-------|------|-------------|
| 0 | Raw | Captured but not processed |
| 1 | Extracted | AI-structured from source content |
| 2 | Supported | ≥ 1 linked evidence source |
| 3 | Corroborated | ≥ 2 independent sources |
| 4 | Approved | Human-validated |
| 5 | Operationalized | Used in board-level decision |

### Layer 5 → Layer 3 Integration

Approved TruthObjects sync to Layer 3 Knowledge Graph as `:GroundTruth` nodes:

```cypher
(GroundTruth)-[:GROUNDS]->(Capability | Outcome | ValueDriver | Persona)
```

Sync is best-effort — Layer 5 remains operational if Layer 3 is unavailable.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/truths` | Create TruthObject |
| `GET` | `/api/v1/truths` | List with filters |
| `GET` | `/api/v1/truths/{id}` | Get detail with audit trail |
| `POST` | `/api/v1/truths/{id}/validate` | Apply state transition |
| `POST` | `/api/v1/truths/{id}/sources` | Add evidence source |
| `POST` | `/api/v1/truths/sync-kg` | Bulk sync to Layer 3 |
| `GET` | `/api/v1/health` | Health check |

---

## Layer 6 — Benchmark Service

**Status:** ✅ Complete
**Port:** 8006

### Purpose

Standalone service for comparative intelligence and peer benchmarking. Provides curated datasets for peer comparison and statistical validation.

### Features

- **Benchmark Dataset Management** by industry and segment
- **Peer Comparison APIs** with percentile ranking
- **Range Validation** for sanity checks
- **Manufacturing Reference Dataset** included as seed data

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/v1/benchmarks/datasets` | List datasets |
| `GET` | `/v1/benchmarks/datasets/{id}` | Get dataset details |
| `POST` | `/v1/benchmarks/compare` | Peer comparison |
| `POST` | `/v1/benchmarks/validate` | Range validation |
| `GET` | `/v1/benchmarks/industries` | List industries |

### Integration

Layer 6 integrates with Layer 4 Agents via `IBenchmarkClient` interface for ROI validation against peer benchmarks.

---

## Frontend — React Presentation Layer

**Technology Stack:**
- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **State Management:** Zustand (client), React Query (server)
- **UI Library:** shadcn/ui components + Tailwind CSS
- **Routing:** Wouter (lightweight React Router alternative)
- **Charts:** Recharts

### Architecture Patterns

**Route-Driven Navigation:**
- URL is primary navigation state
- Three-tier UX model: Standard → Advanced → Admin
- Progressive disclosure based on user tier

**State Management:**
- **Server State:** React Query with automatic caching, background refetching
- **Client State:** Zustand stores (user tier, account context, UI preferences)
- **Form State:** React Hook Form with Zod validation

**Component Organization:**
- Barrel exports via `components/index.ts` for clean imports
- Hook aggregation via `hooks/index.ts`
- Domain-based page organization (`pages/admin/`, `pages/intelligence/`, `pages/studio/`)

### Key Pages

| Page | Purpose |
|------|---------|
| `CommandCenter` | Main dashboard with tiered navigation |
| `GraphExplorer` | Interactive graph visualization with 3-panel layout |
| `FormulaBuilder` | Create and manage value formulas |
| `BusinessCase` | Generate and view business cases |
| `WhitespaceAnalysis` | AI-powered account whitespace identification |
| `FormulaGovernance` | Admin: Formula approval workflows |
| `HealthMonitor` | Admin: System health badges |

### API Integration

Frontend communicates with:
- **Layer 3:** `/v1/graph/subgraph` for graph visualization
- **Layer 3:** `/v1/value-trees/{id}` for value tree rendering
- **Layer 4:** `/v1/workflows/*` for agent workflows
- **Layer 4:** `/v1/tools/*` for direct tool invocation

---

## Shared Services (`shared/`)

Cross-layer functionality extracted into the `shared/` package:

### Identity (`shared/identity/`)

- **GovernanceMiddleware** — Unified auth, tenant context, rate limiting
- **RequestContext** — Typed context with tenant_id, user_id, roles
- **RBAC** — Role-based access control with permission matrix
- **API Key Management** — Secure key hashing and validation

### Audit (`shared/audit/`)

- **Structured Logging** — JSON format with trace correlation
- **Audit Events** — Immutable audit trail for compliance

### Error Handling (`shared/error_handling/`)

- **RequestIDMiddleware** — Correlation ID propagation
- **Exception Handlers** — Standardized error responses across all layers

---

## Data Flow

### Ingestion Flow

```
Source Document → Chunking → Embedding → Object Storage
                     ↓
               LLM Extraction → Entities + Relationships → RDF/OWL
                                                              ↓
                                                       Knowledge Graph (Neo4j)
```

### Query Flow

```
User Query → Agent Router → Skill Selection → Graph Query / Hybrid Search
                                                        ↓
                                              Confidence Check
                                                        ↓
                                     Response Synthesis / Human Escalation
```

### Generation Flow

```
Request → Value Tree Resolution → Formula Evaluation → Narrative → Document Assembly
              ↓                         ↓                  ↓
        Provenance Chain ← Evidence Quotes ← Source Documents
```

### Ground Truth Validation Flow

```
Extraction → TruthObject (EXTRACTED) → Evidence Link → SUPPORTED
                                                  → Multiple Sources → CORROBORATED
                                                  → Human Approval → APPROVED
                                                  → Board Usage → OPERATIONALIZED
                                                         ↓
                                                   Knowledge Graph Sync
```

---

## Confidence & Provenance

### Confidence Scoring

Every entity, relationship, and generated output carries a confidence score (0.0–1.0) derived from:

- **Source quality** — authoritative vs. speculative
- **Extraction clarity** — explicit vs. inferred
- **Evidence strength** — direct quote vs. paraphrase
- **Model certainty** — logprob-based scoring

### Provenance Chain

```
Business Case → Narrative → Value Tree → Relationships → Extractions → Chunks → Documents
```

Each link records: timestamp, processing version, confidence, evidence quotes.

---

## Deployment Architecture

### Container Strategy

| Layer | Container | External Port | Internal Port |
|-------|-----------|---------------|---------------|
| Layer 1 (Ingestion) | Document processing workers | 8001 | 8000 |
| Layer 2 (Extraction) | LLM-based extraction (GPU-enabled) | 8002 | 8000 |
| Layer 3 (Knowledge) | API server + Neo4j graph database | 8003 | 8003 |
| Layer 4 (Agents) | LangGraph agent runtime | 8004 | 8000 |
| Layer 5 (Ground Truth) | Truth validation service | 8005 | 8005 |
| Layer 6 (Benchmarks) | Peer comparison service | 8006 | 8006 |
| Frontend | React + Vite static build | 5173 | 80 |

### Communication

- **Layer-to-layer:** REST/HTTP (async `httpx`)
- **Event streaming:** Redis / RabbitMQ for async Celery tasks
- **Storage:** PostgreSQL + Neo4j + MinIO (object storage)
- **Frontend-to-Backend:** REST API + WebSocket for real-time updates

### Scalability

- **Layers 1 & 2:** Horizontal scaling via Celery worker pools
- **Layer 3:** Read replicas for query load; Neo4j cluster for production
- **Layer 4:** Stateless agent runtime — scales with request volume
- **Layer 5:** PostgreSQL-backed — scales with connection pooling
- **Layer 6:** Stateless — scales horizontally

---

## Global Engineering Standards

| Standard | Requirement |
|----------|-------------|
| Language | Python 3.11+ with `async/await` |
| Type checking | Strict mypy (zero errors) |
| Formatting | Ruff (replaces Black) |
| Linting | Ruff (zero warnings) |
| Test coverage | ≥ 85% unit test coverage |
| Imports | Absolute only: stdlib → third-party → local |
| Commits | Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`) |
| Secrets | Environment variables only — no hardcoded secrets |
| Observability | Prometheus metrics, structured JSON logging, OpenTelemetry traces |
| API design | RESTful, `/v1/` prefix, standardized error format |
| Data provenance | URL + timestamp on all data |
| Confidence scores | 0.0–1.0 on all LLM outputs |
| Contract enforcement | CI blocks merge on Platform Contract violations |

---

## Project Structure

```
Fabric_4L/
├── services/                    # Core platform (Layers 1–6)
│   ├── layer1-ingestion/            # ✅ Intelligent Data Ingestion
│   ├── layer2-extraction/           # ✅ Ontology-Guided Extraction
│   ├── layer3-knowledge/            # ✅ Knowledge Graph & Semantic Layer
│   ├── layer4-agents/               # ✅ Agentic Workflow Engine
│   ├── layer5-ground-truth/         # ✅ Ground Truth Validation
│   ├── layer6-benchmarks/           # ✅ Benchmark Service
│   └── shared/                      # Cross-layer services (identity, audit)
├── frontend/                        # React + TypeScript UI
│   └── client/                      # Vite + React + shadcn/ui
├── packages/                        # Shared packages
│   ├── platform-contract/           # Cross-layer patterns (CONTRACT.md)
│   └── config/                      # Shared configuration
├── contracts/                       # API contracts
│   ├── openapi/                     # Generated OpenAPI specs per layer
│   ├── jsonschema/                  # Shared data model schemas
│   └── tool-manifests/              # Agent tool JSON schemas
├── docs/                            # ADRs, runbooks, API specs
│   ├── architecture/
│   ├── audit/
│   └── assets/
├── specs/                           # Detailed technical specifications
├── packs/                           # Domain-specific value packs
│   ├── ai-technology/
│   ├── energy-utilities/
│   ├── financial-services/
│   └── life-sciences/
├── k8s/                             # Kubernetes manifests
├── monitoring/                      # Prometheus + Grafana
├── scripts/                         # Smoke tests, tooling scripts
├── tests/                           # Cross-layer integration tests
├── Architecture.md                  # This file
├── AGENTS.md                        # AI agent contributor guide
└── Providers.md                     # External providers reference
```

---

## Architectural Decision Records (ADRs)

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](docs/explanations/adr/ADR-007-multi-layer-architecture-vs-monolith.md) | Multi-Layer Architecture vs Monolith | Accepted |
| [ADR-002](docs/explanations/adr/ADR-008-neo4j-knowledge-graph-storage.md) | Neo4j for Knowledge Graph Storage | Accepted |
| [ADR-003](docs/explanations/adr/ADR-009-postgresql-rls-multi-tenancy.md) | PostgreSQL RLS Multi-Tenancy | Accepted |
| [ADR-004](docs/explanations/adr/ADR-010-langgraph-workflow-orchestration.md) | LangGraph Workflow Orchestration | Accepted |
| [ADR-005](docs/explanations/adr/ADR-011-circuit-breaker-pattern.md) | Circuit Breaker Pattern | Accepted |
| [ADR-006](docs/explanations/adr/ADR-012-repository-pattern.md) | Repository Pattern | Accepted |
| [ADR-007](docs/explanations/adr/ADR-013-opentelemetry-observability.md) | OpenTelemetry Observability | Accepted |
| [ADR-008](docs/explanations/adr/ADR-014-jwt-api-key-hybrid-authentication.md) | JWT + API Key Authentication | Accepted |

---

## Related Documentation

- [Platform Contract](packages/platform-contract/CONTRACT.md) — Cross-layer implementation patterns
- [AGENTS.md](AGENTS.md) — Contributor guide for AI agents
- [Providers.md](Providers.md) — External providers and credentials
- [TEST_STRATEGY.md](TEST_STRATEGY.md) — Testing approach across layers
- [SECURITY.md](SECURITY.md) — Security architecture and threat model

---

*Document Version: 2.0*
*Last Updated: April 26, 2026*
