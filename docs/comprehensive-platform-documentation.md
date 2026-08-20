---
title: "Fabric_4L Comprehensive Platform Documentation"
category: "reference"
audience: "all"
last-reviewed: "2026-05-06"
freshness: "current"
related: ["../README.md", "architecture/system-overview.md", "core-concepts/architecture.md", "core-concepts/security-model.md"]
---

# Fabric_4L Comprehensive Platform Documentation

## 1. Product Overview

Fabric_4L is a multi-layer enterprise agentic SaaS platform for business value modeling, ROI quantification, evidence-backed value cases, and agentic enterprise workflows. The platform transforms unstructured enterprise data into structured, actionable knowledge through an ontology-guided pipeline and autonomous AI agents.

**Target Users:**
- Enterprise sales teams (value engineering, pre-sales)
- Customer success organizations (account planning, expansion)
- Executive decision makers (ROI justification, board presentations)
- Value engineering teams (business case development)

**Core Capabilities:**
- **Ingestion**: Automated web crawling, document parsing, SEC EDGAR filing extraction
- **Extraction**: LLM-guided entity and relationship extraction with ontology alignment
- **Knowledge Graph**: Neo4j-based graph storage with hybrid vector + graph retrieval (GraphRAG)
- **Agentic Workflows**: LangGraph-powered AI agents for whitespace analysis, ROI calculation, business case generation
- **Ground Truth**: Evidence-backed fact validation with maturity ladder and provenance tracking
- **Benchmarking**: Peer comparison and statistical validation across industries

**Platform Status:**
- Launch Readiness: 95% (as of ROADMAP.md audit date 2026-04-09)
- Layers 1-6: 75-100% complete (varies by layer)
- Frontend: ~90% complete with API integration
- DevOps/Infra: ~95% complete

## 2. Problem Statement

### Core Problems Addressed

**1. Value Quantification Gap**
Enterprise teams struggle to quantify business value in credible, defensible terms. ROI calculations are often manual, inconsistent, and lack supporting evidence.

**2. Knowledge Fragmentation**
Critical business intelligence exists across disconnected sources: websites, SEC filings, internal documents, competitor research, and tribal knowledge.

**3. Evidence Deficit**
Business cases and ROI projections often lack traceable evidence, making them vulnerable to challenge and reducing stakeholder confidence.

**4. Workflow Inefficiency**
Value engineering workflows are repetitive and manual: gathering data, extracting insights, building models, generating documents, and validating claims.

**5. Trust Erosion**
Outdated or inaccurate documentation and models reduce trust in the platform and slow adoption.

### Fabric_4L Solution

Fabric_4L addresses these problems through:

- **Automated Knowledge Extraction**: LLM-powered extraction from unstructured sources with ontology-guided structure
- **Evidence-Backed Reasoning**: Every claim, relationship, and calculation carries provenance and confidence scores
- **Agentic Workflows**: AI agents automate repetitive value engineering tasks with human-in-the-loop checkpoints
- **Graph-Based Intelligence**: Knowledge graph enables multi-hop reasoning and context-aware insights
- **Ground Truth Validation**: Separation of inferred facts from verified, evidence-backed claims
- **Continuous Synchronization**: Drift detection ensures documentation stays aligned with evolving code

## 3. Architecture Overview

Fabric_4L uses a **six-layer microservices architecture** with strict tenant isolation via PostgreSQL Row-Level Security (RLS) and Neo4j composite constraints.

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

### Architectural Principles

| Principle | Implementation |
|-----------|---------------|
| **Context is explicit** | Typed `RequestContext` via GovernanceMiddleware; single ContextVar for async propagation |
| **Fail-safe defaults** | Missing tenant context → reject; missing auth → reject |
| **One dependency, one lifetime** | DB session created once per request, committed once, rolled back on exception |
| **Schema-first at boundaries** | Every tool, agent output, and API response has declared Pydantic schema |
| **Traceability mandatory** | Every request carries `trace_id`; every agent run carries `workflow_id` |
| **Frontend: route-driven** | URL is primary navigation; Zustand stores are typed; server state in React Query |

### Multi-Tenant Architecture

**PostgreSQL RLS:**
- Tenant isolation via `SET LOCAL app.tenant_id` per session
- Policies restrict rows based on `tenant_id` column
- Application-level middleware sets tenant context automatically

**Neo4j Tenant Scoping:**
- All entities and relationships include `tenant_id` property
- Composite unique constraints on `(id, tenant_id)` for all entity types
- Same `id` allowed across different tenants
- Community Edition compatible (no enterprise-only features required)

## 4. Layer Responsibilities

### Layer 1: Intelligent Data Ingestion (75% Complete)

**Purpose:** Convert unstructured source materials into clean, normalized Markdown documents with full metadata, compliance auditing, and multi-tenant isolation.

**Port:** 8001 (host-mapped from container port 8000)

**Key Components:**
- **Scheduler Service**: Determines crawl targets and priorities
- **Crawler Workers**: Headless Playwright browser instances executing extraction
- **Post-Processor**: Cleans, deduplicates, and normalizes raw content to Markdown
- **Source Registry**: Document metadata, freshness tracking, access URLs
- **Compliance Auditor**: robots.txt validation, rate limit enforcement, PII detection

**Data Sources (Priority Order):**
1. Corporate websites, SEC EDGAR filings (10-K/10-Q), earnings call transcripts
2. Competitor documentation, industry analyst reports, patent filings
3. LinkedIn company pages, news mentions (NewsAPI)

**Compliance (Non-Negotiable):**
- robots.txt parsing with 24-hour cache; never crawl Disallow paths
- Rate limiting: Global 1,000 req/min; per-domain 1 req/sec with 20% jitter
- PII detection with Microsoft Presidio — redact SSN, credit cards, phone, email; block pages with > 3 PII entities
- Audit log: URL, timestamp, IP, bytes downloaded, outcome (7-year retention)

**What's Built:**
- ✅ FastAPI application with full REST API (`/api/v1/ingestion`)
- ✅ SQLAlchemy models with migrations (Alembic)
- ✅ Playwright crawler implementation
- ✅ PII scanner (compliance)
- ✅ robots.txt checker
- ✅ SEC EDGAR adapter
- ✅ XBRL parser
- ✅ Priority queue scheduler
- ✅ Content extractor/post-processor
- ✅ Unit tests

**What's Missing:**
- ⚠️ Celery task queue integration (stubs exist, not wired to L2)
- ⚠️ Redis integration for distributed processing
- ❌ Proxy rotation implementation
- ⚠️ Rate limiting enforcement (partial)
- ❌ Production monitoring/alerting
- ❌ Kubernetes deployment manifests

### Layer 2: Ontology-Guided Extraction (92% Complete)

**Purpose:** Extract structured entities and relationships from ingested Markdown using LLMs, then serialize results as RDF/OWL with full provenance. Includes direct Layer 3 ingestion capability via `extract-and-ingest` endpoint.

**Port:** 8002

**Core Ontology (Pydantic v2 Models):**
```
Capability → UseCase → Persona → ValueDriver
   ↓           ↓          ↓           ↓
[What we]  [How it's] [Who]     [Business]
[do]       [used]     [benefits] [outcome]
```

**Entity Types:**
- `Capability`: Technical features or abilities (e.g., "Real-Time Data Ingestion")
- `UseCase`: Business problem scenarios (e.g., "Touchless Accounts Payable")
- `Persona`: Stakeholder roles: `economic_buyer`, `operational_user`, `stakeholder`
- `ValueDriver`: Quantifiable outcomes: `revenue`, `cost`, `risk`, `capital`

**Relationship Types:** `enables`, `requires`, `benefits`, `drives`, `contributes_to`, `depends_on`, `alternative_to`

**Extraction Pipeline (6 Stages):**
1. Chunking & Preprocessing — LangChain `RecursiveCharacterTextSplitter`; 2,000-token chunks, 200-token overlap
2. Entity Extraction (LLM Call 1) — GPT-4o or Claude 3.5 Sonnet; temperature 0.0; confidence threshold 0.8
3. Relationship Extraction (LLM Call 2) — Evidence-backed only; confidence threshold 0.75
4. Semantic Alignment & Deduplication — `text-embedding-3-large`; similarity threshold 0.85
5. Validation & Normalization — Pydantic schema validation; resolve all ID references
6. RDF/OWL Serialization — Turtle format; PROV-O provenance metadata; OWL axioms

**What's Built:**
- ✅ Pydantic ontology models (Capability, UseCase, Persona, ValueDriver)
- ✅ Relationship definitions
- ✅ Text chunker implementation
- ✅ Semantic aligner (deduplication)
- ✅ Coreference resolver
- ✅ RDF/OWL generator
- ✅ Provenance tracker
- ✅ Entailment validator stub
- ✅ LLM integration (OpenAI/Anthropic client) with cost tracking
- ✅ Prompt templates for extraction
- ✅ Function calling schema implementation
- ✅ Vector embedding generation
- ✅ LLM cost Prometheus metrics
- ✅ Full validation pipeline orchestration
- ✅ Confidence scoring mechanism

**What's Missing:**
- ❌ APQC/BIAN/FIBO reference model integration
- ⚠️ Production smoke verification (cross-layer E2E)

### Layer 3: Knowledge Graph & Semantic Layer (85% Complete)

**Purpose:** Store, index, and query the structured knowledge graph; support GraphRAG and hybrid vector + graph retrieval. Provides coherent subgraph API for frontend visualization.

**Port:** 8003

**Data Model:**
- **Nodes:** `:Capability`, `:UseCase`, `:Persona`, `:ValueDriver`, `:Formula`, `:Industry`, `:GroundTruth`
- **Relationships:** `ENABLES`, `BENEFITS`, `DRIVES`, `CONTRIBUTES_TO`, `HAS_FORMULA`, `APPLIES_TO`, `GROUNDS`
- **Node Properties:** `embedding` (1,536-dim), `confidence`, `source_url`, `extracted_at`, `tenant_id`

**GraphRAG Implementation:**
- **Indexing Phase:** Entity embeddings stored in vector index; Leiden community detection (Neo4j GDS); LLM-generated community summaries; Hierarchical index built
- **Retrieval Phase:** Vector search (cosine similarity) → entry nodes; Graph traversal (BFS/DFS, max 3 hops) → connected subgraphs; Reranking by relevance; Citation support with source nodes
- **Global Queries:** Use community summaries for broad questions (no vector search required)

**What's Built:**
- ✅ Extensive FastAPI application structure
- ✅ GraphRAG retrieval implementation
- ✅ Hybrid search (vector + graph)
- ✅ Vector store abstraction
- ✅ Community detection (Leiden)
- ✅ Similarity analytics
- ✅ Centrality metrics
- ✅ Agent implementations (whitespace, ROI, narrative, provenance)
- ✅ API middleware, rate limiting, auth stubs
- ✅ Redis cache abstraction
- ✅ Prometheus metrics stubs
- ✅ Comprehensive test suite
- ✅ Neo4j connection (driver implemented, Docker Compose wired)

**What's Missing:**
- ⚠️ Neo4j vector indexes (schema defined, needs verification)
- ❌ Pinecone/Weaviate integration
- ❌ Semantic layer metric definitions
- ⚠️ Row-level security implementation (partial)
- ❌ Production performance tuning

### Layer 4: Agentic Workflow Engine (78% Complete)

**Purpose:** Execute composable AI workflows for whitespace analysis, ROI calculation, business case generation, and provenance auditing. Uses LangGraph for checkpointed, resumable workflows with human-in-the-loop gates.

**Port:** 8004 (host-mapped from container port 8000)

**Agent Workflows:**
1. **Whitespace Analysis:** `IngestProspect → ExtractInsights → MapToCapabilities → IdentifyWhitespace → GeneratePlan`
2. **Dynamic ROI Calculator:** Retrieves Value Tree from graph → safely evaluates formula strings (numexpr) → Monte Carlo sensitivity analysis
3. **Business Case Generator:** Auto-generates Executive Summary, Current State, Proposed Solution, Financial Analysis, Risk Mitigation, Next Steps (Markdown, DOCX, PDF, PPTX)
4. **Provenance Audit Agent:** Traverses PROV-O graph backward showing LLM calls → extractions → source documents with confidence scores

**Skill Tiers:**
1. Knowledge Navigation: `/graph_traverse`, `/semantic_search`, `/resolve_value_tree`, `/find_path`
2. Reasoning: `/multi_hop_reason`, `/analyze_gaps`
3. Calculation: `/evaluate_formula`, `/sensitivity_analysis`
4. Content Generation: `/build_narrative`, `/generate_business_case`, `/write_executive_summary`
5. Research: `/research_web`, `/analyze_competitor`, `/enrich_industry_context`
6. Audit: `/trace_provenance`, `/escalate_to_human`
7. Meta: `/value_fabric_help`

**What's Built:**
- ✅ Tool registry structure
- ✅ Knowledge tools, calculation tools, generation tools
- ✅ Workflow base classes
- ✅ Business case, ROI calculator, whitespace workflows
- ✅ Agent state models (Pydantic)
- ✅ Message bus abstraction
- ✅ Tenant context middleware
- ✅ Provenance store
- ✅ Layer 1/2/3 client integrations
- ✅ LangGraph state machine (base classes implemented)
- ✅ State manager persistence (AsyncPostgresSaver configured)
- ✅ Human-in-the-loop integration (`/resume` endpoint)
- ✅ Workflow scheduler (TaskScheduler implemented)
- ✅ Tool execution orchestration (ToolRegistry wired)

**What's Missing:**
- ⚠️ Workflow executor engine (partial, needs OrchestrationController wiring)
- ❌ Agent decision logic (which workflow to run)

### Layer 5: Ground Truth (100% Complete) ⭐ PRODUCTION READY

**Purpose:** Evidence-backed, CFO-defensible facts for the Value Fabric platform. Stores, validates, and governs factual claims extracted from customer conversations, documents, and web content. Every claim has traceable provenance, confidence score, and maturity level.

**Port:** 8005

**Core Concepts:**

**TruthObject:** Structured, evidence-backed factual claim with validation state machine
- `claim`: Plain-language factual statement
- `claim_type`: Semantic category (`efficiency_gain`, `cost_savings_baseline`)
- `value`: Structured value (amount, unit, period)
- `confidence`: 0.0–1.0 score from extraction model
- `status`: Validation state
- `maturity_level`: 0–5 maturity ladder position
- `sources`: Evidence sources (call transcripts, documents, web pages)
- `applies_to`: Scoping context (opportunity_id, account_id, persona_id)

**Validation State Machine:**
```
EXTRACTED → SUPPORTED → CORROBORATED → APPROVED → OPERATIONALIZED
                │              │              │
                └──────────────┴──────────────┘──► DISPUTED → CORROBORATED
```

**Maturity Ladder:**
- Level 0: Raw (Captured but not processed)
- Level 1: Extracted (AI-structured from source content)
- Level 2: Supported (≥ 1 linked evidence source)
- Level 3: Corroborated (≥ 2 independent sources)
- Level 4: Approved (Human-validated)
- Level 5: Operationalized (Used in board-level decision)

**What's Built:**
- ✅ TruthObject SQLAlchemy model with all fields
- ✅ TruthSource, ValidationEvent, MaturityHistory models
- ✅ Validation state machine (extracted → supported → corroborated → approved)
- ✅ Maturity ladder (0-5 levels) with progression tracking
- ✅ FastAPI with full REST API (/api/v1/truths)
- ✅ Layer 3 Knowledge Graph integration client
- ✅ Auto-advancement logic
- ✅ Dispute resolution workflow
- ✅ Comprehensive test suite
- ✅ Background scheduler integration (FreshnessMonitor complete)

**What's Missing:**
- ⚠️ Production hardening (rate limiting exists, needs monitoring dashboards)
- ❌ Human approval workflow UI integration (frontend)

### Layer 6: Benchmark Service (90% Complete)

**Purpose:** Standalone service for comparative intelligence and peer benchmarking. Provides curated datasets for peer comparison and statistical validation.

**Port:** 8006

**Features:**
- Benchmark Dataset Management by industry and segment
- Peer Comparison APIs with percentile ranking
- Range Validation for sanity checks
- Manufacturing Reference Dataset included as seed data

**What's Built:**
- ✅ Benchmark dataset management
- ✅ Peer comparison APIs
- ✅ Range validation
- ✅ Manufacturing reference dataset
- ✅ CI coverage gate ✅ COMPLETE (Task 42)

**What's Missing:**
- ⚠️ Additional industry datasets beyond manufacturing

## 5. Core Workflows

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

## 6. API and Contract Alignment

### OpenAPI Contract Drift Detection

**CI/CD Workflows:**
- `drift-check.yml`: Detects OpenAPI contract drift on pull requests
- `openapi-drift-check.yml`: Validates OpenAPI specs and checks for drift across all layers
- `generated-api-freshness.yml`: Checks if generated frontend API clients are stale

**Contract Storage:**
- All OpenAPI specs stored in `contracts/openapi/` as source of truth
- Specs per layer: `layer1-ingestion.json`, `layer2-extraction.json`, `layer3-knowledge.json`, `layer4-agents.json`, `layer5-ground-truth.json`

**Regeneration Process:**
```bash
# Regenerate OpenAPI specs from implementation
python scripts/export_openapi.py

# Regenerate frontend TypeScript clients
cd apps/web && pnpm run generate:api
```

### API Endpoints by Layer

**Layer 1 (Ingestion):**
- `POST /api/v1/ingestion/targets` - Create scraping target
- `GET /api/v1/ingestion/targets` - List targets with filters
- `POST /api/v1/ingestion/jobs` - Start scraping job
- `GET /api/v1/ingestion/jobs/{id}` - Get job status and progress
- `GET /api/v1/ingestion/content/{id}` - Retrieve Markdown + metadata
- `DELETE /api/v1/ingestion/content/{id}` - Soft delete with 30-day retention
- `GET /api/v1/ingestion/compliance/logs` - Compliance audit trail

**Layer 2 (Extraction):**
- `POST /v1/extract` - Start extraction job
- `GET /v1/extract/status/{id}` - Check job status
- `POST /v1/extract/batch` - Batch extraction
- `POST /v1/extract-and-ingest` - Extract + push to Layer 3 in one call
- `GET /v1/ontology/entities` - List entities
- `GET /v1/audit/trace/{id}` - Full provenance trace

**Layer 3 (Knowledge Graph):**
- `POST /v1/query/graph` - GraphRAG traversal with citations
- `POST /v1/search/hybrid` - Vector + graph hybrid search
- `POST /v1/ingest` - Ingest RDF from Layer 2
- `GET /v1/entities` - List entities
- `GET /v1/graph/subgraph` - Coherent subgraph for visualization
- `GET /v1/value-trees/{entity_id}` - Build full value chain from any node
- `GET /v1/formulas` - List formulas
- `POST /v1/formulas/evaluate` - Evaluate formula with variables
- `GET /v1/health` / `GET /v1/health/detailed` - Health checks

**Layer 4 (Agents):**
- `POST /v1/workflows/whitespace` - Start whitespace analysis workflow
- `POST /v1/workflows/roi` - Execute ROI calculation
- `POST /v1/workflows/business-case` - Generate business case document
- `GET /v1/workflows/{id}/status` - Poll workflow status
- `POST /v1/workflows/{id}/approve` - Human-in-the-loop approval gate
- `GET /v1/checkpoints/{workflow_id}` - Resume from checkpoint
- `POST /v1/tools/{tool_name}/invoke` - Direct tool invocation
- `GET /v1/health` - Health check with component status
- `GET /v1/health/badges` - Component health badges for UI

**Layer 5 (Ground Truth):**
- `POST /api/v1/truths` - Create TruthObject
- `GET /api/v1/truths` - List with filters
- `GET /api/v1/truths/{id}` - Get detail with audit trail
- `POST /api/v1/truths/{id}/validate` - Apply state transition
- `POST /api/v1/truths/{id}/sources` - Add evidence source
- `POST /api/v1/truths/sync-kg` - Bulk sync to Layer 3
- `GET /api/v1/health` - Health check

**Layer 6 (Benchmarks):**
- `GET /health` - Health check
- `GET /v1/benchmarks/datasets` - List datasets
- `GET /v1/benchmarks/datasets/{id}` - Get dataset details
- `POST /v1/benchmarks/compare` - Peer comparison
- `POST /v1/benchmarks/validate` - Range validation
- `GET /v1/benchmarks/industries` - List industries

## 7. Frontend Application Structure

### Technology Stack

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

### Frontend Status

**What's Built:**
- ✅ React + TypeScript application
- ✅ shadcn/ui component library (complete)
- ✅ Routing with wouter
- ✅ Page structure for all major features
- ✅ API integration with generated TypeScript clients
- ✅ 47 unit/component test files (~150 tests)
- ✅ 18 E2E test files (~92 tests)

**What's Missing:**
- ⚠️ 5 test fixes needed (Tasks 43-45 from ROADMAP)
- ⚠️ Some pages still use mock data (74% of pages have zero API calls per facade-page-connector workflow)

## 8. Agent Orchestration

### LangGraph Integration

Layer 4 uses LangGraph for stateful, checkpointed workflow orchestration:

**Workflow Checkpoints:**
- PostgreSQL-backed checkpoint storage
- Automatic resume on service restart
- Human-in-the-loop pause points

**Agent State Management:**
- Pydantic models for typed state
- AsyncPostgresSaver for persistence
- State versioning for schema evolution

### Tool Registry

The Tool Registry provides centralized tool management:
- Tool definitions in JSON schemas (`contracts/tool-manifests/`)
- Skill definitions in `.devin/skills/`
- Runtime invocation with permission checks
- Cost tracking and budget enforcement

### Human-in-the-Loop Gates

Workflows support human approval at critical points:
- `/v1/workflows/{id}/approve` endpoint for approval/rejection
- Checkpoint resume via `/v1/checkpoints/{workflow_id}`
- WebSocket notifications for pending approvals

### Agent Skills

**Knowledge Navigation Skills:**
- `graph_traverse` - Navigate knowledge graph
- `semantic_search` - Vector similarity search
- `resolve_value_tree` - Build value chain from entity
- `find_path` - Find shortest path between entities

**Reasoning Skills:**
- `multi_hop_reason` - Multi-hop reasoning over graph
- `analyze_gaps` - Identify knowledge gaps

**Calculation Skills:**
- `evaluate_formula` - Safe formula evaluation with numexpr
- `sensitivity_analysis` - Monte Carlo sensitivity analysis

**Content Generation Skills:**
- `build_narrative` - Generate narrative from evidence
- `generate_business_case` - Auto-generate business case documents
- `write_executive_summary` - Generate executive summaries

## 9. Data, Memory, and Knowledge Graph Model

### Knowledge Graph Schema

**Node Types:**
- `:Capability` - Technical features and abilities
- `:UseCase` - Business problem scenarios
- `:Persona` - Stakeholder roles (economic_buyer, operational_user, stakeholder)
- `:ValueDriver` - Quantifiable outcomes (revenue, cost, risk, capital)
- `:Formula` - Calculation formulas with variables
- `:Industry` - Industry classifications
- `:GroundTruth` - Evidence-backed factual claims

**Relationship Types:**
- `ENABLES` - Capability → UseCase
- `BENEFITS` - UseCase → Persona
- `DRIVES` - UseCase → ValueDriver
- `CONTRIBUTES_TO` - ValueDriver → ValueDriver (hierarchical)
- `HAS_FORMULA` - ValueDriver → Formula
- `APPLIES_TO` - Benchmark → Industry
- `GROUNDS` - GroundTruth → (Capability/Outcome/ValueDriver/Persona)

**Node Properties:**
- `embedding` - 1,536-dimensional vector for semantic search
- `confidence` - 0.0-1.0 confidence score
- `source_url` - Origin document URL
- `extracted_at` - Extraction timestamp
- `tenant_id` - Tenant identifier for isolation

### Vector Storage

**PostgreSQL pgvector:**
- Embeddings stored in vector columns
- Cosine similarity search
- Integrated with relational queries

**Neo4j Vector Indexes:**
- Native vector similarity search
- Combined with graph traversal for GraphRAG
- Community detection for hierarchical indexing

### Provenance Tracking

**PROV-O Metadata:**
- Every entity records extraction source
- LLM call logs with prompts and responses
- Confidence scores at each extraction step
- Evidence quotes for relationship justification

**Provenance Chain:**
```
Business Case → Narrative → Value Tree → Relationships → Extractions → Chunks → Documents
```

Each link records: timestamp, processing version, confidence, evidence quotes.

### Formula System

**Formula Structure:**
- Variables with units and periods
- Safe evaluation using numexpr
- Monte Carlo sensitivity analysis
- Dependency tracking for formula chains

**Formula Evaluation:**
- Type-safe variable resolution
- Unit conversion support
- Error handling for invalid formulas
- Caching for repeated evaluations

## 10. Governance, Security, and Tenant Isolation

### Authentication Methods

**JWT Authentication (User Sessions):**
- Token structure: header (alg, kid, typ), payload (sub, tenant_id, roles, permissions, iat, exp, jti)
- Algorithms: HS256 / RS256 / ES256
- Key ID (kid) for rotation support
- Expiration: 1 hour with refresh support

**API Key Authentication (Service-to-Service):**
- Format: `vf_live_<64-char-hex>` or `vf_test_<64-char-hex>`
- Storage: HMAC-SHA256 hash for fast verification
- Prefix: Environment identification (live/test)
- Rotation: Manual or 90-day auto

**OIDC/SAML SSO (Enterprise):**
- Integration with Okta/Azure AD
- Authorization Code flow
- Session creation with JWT
- Redirect-based authentication

### Role-Based Access Control (RBAC)

**Role Hierarchy:**
```
System Admin → Tenant Admin → Analyst/Developer → Viewer
```

**Roles and Permissions:**
- **System Admin**: `tenant:create`, `user:impersonate`, `system:config`
- **Tenant Admin**: `user:manage`, `billing:view`, `workflow:admin`
- **Analyst**: `workflow:create`, `entity:read`, `report:generate`
- **Developer**: `api_key:manage`, `webhook:configure`, `entity:read`
- **Viewer**: `entity:read`, `dashboard:view`

### Tenant Isolation

**Isolation Mechanisms:**
- **API**: Header validation with `X-Tenant-ID` required
- **Database**: PostgreSQL Row-Level Security policies
- **Graph**: Neo4j tenant labels with composite unique constraints
- **Cache**: Redis key prefixing with `tenant:{id}:`
- **Queue**: Job queue namespacing per tenant
- **Storage**: S3 path prefixing with tenant prefix

**Cross-Tenant Access Prevention:**
- All queries must include tenant filter
- Tenant context verified against authenticated context
- Database-level RLS enforcement
- Fail-closed security posture

### Audit Trail

**Audit Event Structure:**
- event_id, timestamp, action, actor (type, id, tenant_id)
- resource (type, id), context (ip_address, user_agent, request_id)
- result, changes (before, after)

**Audit Actions:**
- Authentication: login, logout, token:refresh, token:revoke (1 year retention)
- Authorization: access:denied, permission:elevated (2 years retention)
- Data Access: entity:read, entity:create, entity:update, entity:delete (90 days retention)
- Workflow: workflow:create, workflow:pause, workflow:resume (1 year retention)
- Admin: user:invite, role:assign, api_key:create (2 years retention)

**Append-Only Guarantee:**
- Database trigger prevents modification
- WORM storage for critical logs
- Immutable audit trail for compliance

### Security Best Practices

**Secrets Management:**
- API Keys: Infisical / HashiCorp Vault (90-day rotation)
- JWT Secret: Environment variable (180-day rotation)
- Database passwords: Vault dynamic credentials (24-hour rotation)
- LLM API keys: Infisical with usage monitoring (90-day rotation)

**Network Security:**
- Public Zone: CDN/WAF
- DMZ: Load Balancer with SSL termination, API Gateway with rate limiting
- Private Zone: Services L1-L4, Databases
- Secure Zone: HashiCorp Vault
- mTLS between services
- TLS 1.3 everywhere

**Production Checklist:**
- JWT_SECRET changed from default/changeme
- All secrets in Vault/Infisical (not in code)
- Audit logging enabled
- Rate limiting configured
- mTLS between services
- Database encryption at rest
- Backup encryption
- Security headers configured
- WAF rules active
- Penetration testing completed

### Compliance

**Supported Standards:**
- SOC 2 Type II: Audit controls, access logs (In Progress)
- GDPR: Data retention, deletion, export (Implemented)
- CCPA: Consumer privacy rights (Implemented)
- HIPAA: PHI handling (optional add-on) (Available)

## 11. Testing and Production Readiness Gates

### Test Inventory

- **Layer 1 (Ingestion):** Ingestion jobs, Playwright crawling, robots.txt, PII scanning
- **Layer 2 (Extraction):** Ontology models, Pydantic validation, RDF/OWL serialization, provenance
- **Layer 3 (Knowledge):** GraphRAG retrieval, Neo4j connectivity, hybrid vector + graph search
- **Layer 4 (Agents):** LangGraph workflows, ROI evaluation, business cases, whitespace analysis
- **Layer 5 (Ground Truth):** TruthObject validation state machine, maturity ladder, provenance
- **Layer 6 (Benchmarks):** Datasets, peer comparisons, statistical validation
- **Frontend (`apps/web`):** Unit/component tests (Vitest), accessibility tests, contract tests
- **E2E Tests:** Playwright journeys, golden paths
- **Root / Security / Contract:** Cross-layer OpenAPI contracts, tenant boundary isolation, OWASP regression gates

### CI Gates

**Required (PR Merge Blocking):**
- PR Checks (`pr-checks.yml`) - Linting, formatting, type checking, structural preflight
- Contract Checks (`contract-checks.yml`) - OpenAPI drift and contract validation
- Production Readiness Gate (`make production-readiness-gate`) - Behavior readiness audit and release gates
- Security Gates - Tenant boundary isolation and OWASP regression tests

**Nightly / Scheduled:**
- Integration Tests (`integration-tests.yml`)
- Smoke Tests (`make test-backend-integrated-release-smoke`)
- Performance Tests (`performance-load-tests.yml`)
- AI Evals (`ai-evals-pipeline.yml`)
- Chaos Testing (`chaos-testing.yml`)

### Test Categories

**Unit Tests:**
- Location: `services/*/tests/`
- Rules: Deterministic, no external calls, fast
- Markers: `@pytest.mark.unit`

**Integration Tests:**
- Location: `services/*/tests/`, `tests/`
- Rules: Uses local container infrastructure or test fixtures
- Markers: `@pytest.mark.integration`

**E2E Tests:**
- Location: `apps/web/e2e/`
- Technology: Playwright
- Scope: Critical user journeys and golden paths

**Contract Tests:**
- Location: `tests/contract/`
- Purpose: Validate tool manifests, API shapes, and schema boundaries
- Markers: `@pytest.mark.contract_static`

**Behavior Readiness:**
- Verification: `make check-behavior-readiness-audit` and `pnpm run test:critical-behaviors`

### Production Invariant Coverage

| Boundary | Scope | Coverage |
|----------|-------|----------|
| Tenant Isolation | Cross-service tenant context propagation and hostile negative tests | Active |
| Authentication | Token verification and 8-phase auth pipeline | Active |
| Authorization | Role and capability checks | Active |
| Input Validation | Schema-first Pydantic and JSON Schema boundaries | Active |
| RLS Enforcement | PostgreSQL row security and Neo4j tenant scoping | Active |
| Secrets Protection | Placeholder secret scanning and no hardcoded credentials | Active |
| Idempotency | Webhook and workflow checkpoint deduplication | Active |
| Rate Limiting | Ingestion and API rate limiters | Active |

## 12. Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js ≥ 22.12.0 and pnpm 10.18.1
- Docker + Docker Compose (v2)
- `make`

### Local Development Process

```bash
# 1. Clone repository
git clone https://github.com/bmsull560/Fabric_4L.git && cd Fabric_4L

# 2. Enable pnpm and install dependencies
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile

# 3. Setup Python service dependencies
make setup

# 4. Generate local dev env and start infrastructure
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d

# 5. Run database migrations
make migrate

# 6. Verify everything passes
make verify
```

### Coding Standards

**Python:**
- Formatter and linter: **ruff** (configured in each `pyproject.toml`)
- Type checker: **mypy** — type hints required on all public functions
- Test runner: **pytest** — 80%+ coverage required on all layers
- No bare `except:` — always catch specific exception types
- Use `async/await` throughout; no blocking I/O in async contexts

**TypeScript / React:**
- Linter: **ESLint** (configured in `apps/web/`)
- Formatter: **Prettier**
- Avoid `any` unless strictly necessary and documented
- Co-locate tests with components using Vitest

**All Languages:**
- No secrets in code — use environment variables
- No commented-out code in PRs
- Keep functions small and focused

### Verification Commands

```bash
# Backend verification
make verify   # lint + type-check + unit tests + contract tests

# Agent/skill verification
make evals    # golden-trace agent evaluations

# Frontend verification
cd apps/web
pnpm run test -- --coverage
pnpm run lint
pnpm run typecheck
```

## 13. Deployment and Infrastructure Notes

### Container Strategy

| Layer | Container | External Port | Internal Port |
|-------|-----------|---------------|---------------|
| Layer 1 (Ingestion) | Document processing workers | 8001 | 8000 |
| Layer 2 (Extraction) | LLM-based extraction (GPU-enabled) | 8002 | 8000 |
| Layer 3 (Knowledge) | API server + Neo4j graph database | 8003 | 8001 |
| Layer 4 (Agents) | LangGraph agent runtime | 8004 | 8000 |
| Layer 5 (Ground Truth) | Truth validation service | 8005 | 8005 |
| Layer 6 (Benchmarks) | Peer comparison service | 8006 | 8006 |
| Frontend | React + Vite static build | 3001 | 80 |

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

### Deployment Topology (Production)

**Kubernetes Cluster:**
- Ingress Controller: nginx/cert-manager
- Application Tier: Frontend (3 replicas), L1 (2 replicas), L2 (2 replicas), L3 (3 replicas), L4 (2 replicas)
- Data Tier: PostgreSQL (Primary-Replica), Neo4j Cluster (3 cores), Redis Cluster (6 nodes)
- External: CloudFront/Cloudflare CDN, Load Balancer with SSL termination, HashiCorp Vault, S3 Object Storage

### Infrastructure Status

**What's Built:**
- ✅ Docker Compose configurations for local development
- ✅ Kubernetes manifests in `k8s/` directory
- ✅ Monitoring (Prometheus + Grafana) dashboards
- ✅ Alerting rules
- ✅ Security regression gates
- ✅ Contract drift detection

**What's Missing:**
- ⚠️ Production Kubernetes deployment (manifests exist, needs production hardening)
- ⚠️ SSO/OIDC integration (Task 69: P0 - in progress)
- ❌ Production monitoring dashboards (stubs exist)
- ❌ Production alerting (PagerDuty integration)

## 14. Known Gaps and Limitations

### Layer-Specific Gaps

**Layer 1 (Ingestion):**
- Celery task queue not wired to Layer 2 (stubs exist)
- Redis integration for distributed processing incomplete
- Proxy rotation implementation missing
- Rate limiting enforcement partial
- Production monitoring/alerting missing
- Kubernetes deployment manifests missing

**Layer 2 (Extraction):**
- APQC/BIAN/FIBO reference model integration missing
- Production smoke verification incomplete (cross-layer E2E)

**Layer 3 (Knowledge Graph):**
- Neo4j vector indexes need verification (schema defined)
- Pinecone/Weaviate integration missing
- Semantic layer metric definitions missing
- Row-level security implementation partial
- Production performance tuning incomplete

**Layer 4 (Agents):**
- Workflow executor engine partial (needs OrchestrationController wiring)
- Agent decision logic missing (which workflow to run)

**Layer 5 (Ground Truth):**
- Production hardening incomplete (rate limiting exists, needs monitoring dashboards)
- Human approval workflow UI integration missing (frontend)

**Layer 6 (Benchmarks):**
- Additional industry datasets needed beyond manufacturing

### Frontend Gaps

- 5 test fixes needed (Tasks 43-45 from ROADMAP)
- 74% of pages have zero API calls (use mock data or generic workspace endpoints)
- Some pages still use mock data

### Testing Gaps

- Need continuous execution of behavior readiness audit (`make check-behavior-readiness-audit`)
- Need continuous expansion of hostile negative tests for tenant isolation
- OIDC/WebSocket authentication gaps
- Role escalation tests needed
- Oversized payload tests needed
- Webhook duplicate/idempotency tests needed

### Infrastructure Gaps

- SSO/OIDC integration in progress (Task 69: P0)
- Production Kubernetes deployment needs hardening
- Production monitoring dashboards incomplete
- Production alerting (PagerDuty integration) missing
- mTLS between services partial (K8s only)

### Documentation Gaps

- This comprehensive documentation is newly created (2026-05-06)
- Some API documentation may not reflect latest implementation
- Runbooks exist but may need updates for production
- Architecture documentation exists but may not reflect all recent changes

### Limitations

**Technical Limitations:**
- Neo4j Community Edition features only (no enterprise-only features)
- PostgreSQL RLS may impact query performance at scale
- Redis queue not persistent by default
- Network overhead between layers (~10-50ms per hop)

**Operational Limitations:**
- 6 services to monitor vs. monolithic approach
- Cross-layer transactions require sagas (no distributed transactions)
- Local development requires running multiple services
- Complex deployment vs. single-container applications

**Security Limitations:**
- Cache side-channel protection partial
- Service account abuse protection partial
- Container escape hardening in progress

## 15. Suggested README Introduction

```markdown
# Value Fabric — Enterprise Agentic SaaS Platform

A production-grade, multi-agent system (MAS) that transforms unstructured enterprise data into
structured, actionable knowledge through an ontology-guided pipeline and autonomous AI agents.

## What it is

Value Fabric is an **enterprise agentic SaaS platform** built on a 6-layer semantic pipeline.
Agents reason over a knowledge graph to produce ROI analyses, business cases, and executive insights—
automatically, at scale, with full auditability.

## Quickstart

```bash
# 1. Clone and enter repo
git clone https://github.com/bmsull560/Fabric_4L.git && cd Fabric_4L

# 2. Enable pnpm and install dependencies
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile

# 3. Setup Python service dependencies
make setup

# 4. Generate local dev env and start infrastructure
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d

# 5. Run database migrations
make migrate

# 6. Verify everything works
make verify

# 7. Start and open the UI
pnpm dev:web
# Open http://localhost:3001
```

## Repository map

| Path | Purpose |
|------|---------|
| `services/layer1-ingestion/` | Data ingestion service (FastAPI + Playwright) |
| `services/layer2-extraction/` | Ontology-guided extraction (LLM + RDF) |
| `services/layer3-knowledge/` | Knowledge graph API (Neo4j + pgvector) |
| `services/layer4-agents/` | Agentic workflow engine (LangGraph) |
| `services/layer5-ground-truth/` | Ground truth & evaluation store |
| `services/layer6-benchmarks/` | Benchmark harness |
| `services/api/` | Cross-layer shared services |
| `contracts/` | Versioned tool manifests, JSON Schemas, OpenAPI specs |
| `apps/web/` | React + TypeScript UI (canonical frontend) |
| `k8s/` | Kubernetes manifests |
| `monitoring/` | Prometheus + Grafana dashboards |
| `packs/` | Domain-specific data packs (life-sciences, manufacturing, software) |
| `docs/` | Architecture docs and runbooks |
| `tests/` | Cross-layer integration and agent evaluation tests |
| `.github/workflows/` | CI pipelines |

## Core concepts

- **Contracts** — All tool schemas and API shapes live in `contracts/`. They are the source of truth.
- **Runtime** — Provider-agnostic orchestration in `services/layer4-agents/src/layer4_agents/engine/`.
- **Agents** — Behavior defined as versioned artifacts in `services/layer4-agents/agents/` and `services/layer4-agents/skills/`.
- **Providers** — Vendor-specific adapters (OpenAI, Anthropic, Neo4j, pgvector) isolated from core logic.
- **Packs** — Domain vertical extensions that add ontology, formulas, and variables without touching core.
- **Drift Detection** — Automated checks for API contract drift, schema drift, and documentation staleness via CI/CD workflows and the Drift Assessor agent.

## Documentation

📚 **[Complete Documentation →](docs/README.md)**

🚀 **[Platform Launch Checklist →](docs/launch-checklists/platform-launch.md)** (Sprint 4 Release Hardening)

Our documentation follows the [Diátaxis Framework](https://diataxis.fr/) with tutorials, how-to guides, reference, and explanations.

### Getting Started

| Document | Description |
|----------|-------------|
| [Quickstart (15 min)](docs/getting-started/quickstart.md) | Get a local instance running fast |
| [Environment Setup](docs/getting-started/environment.md) | Configure secrets, env vars, and services |

### Core Concepts

| Document | Description |
|----------|-------------|
| [System Architecture](docs/core-concepts/architecture.md) | C4 model diagrams and layer interactions |
| [Security Model](docs/core-concepts/security-model.md) | Authentication, RBAC, and tenant isolation |
| [Comprehensive Platform Documentation](docs/comprehensive-platform-documentation.md) | Complete platform overview and technical details |

### API Reference

| Document | Description |
|----------|-------------|
| [API Overview](docs/reference/api-overview.md) | Authentication patterns and common formats |
| [Layer 1: Ingestion](docs/reference/layer1-ingestion-api.md) | Web scraping and job management |
| [Layer 2: Extraction](docs/reference/layer2-extraction-api.md) | LLM-based entity extraction |
| [Layer 3: Knowledge Graph](docs/reference/layer3-knowledge-api.md) | Neo4j + pgvector hybrid search |
| [Layer 4: Agents](docs/reference/layer4-agents-api.md) | Workflow orchestration with LangGraph |
| [Layer 5: Ground Truth](docs/reference/layer5-ground-truth-api.md) | Evaluation and benchmarking |

### Troubleshooting & Operations

| Document | Description |
|----------|-------------|
| [Troubleshooting Guide](docs/troubleshooting/index.md) | Decision trees and common issues |
| [Runbooks](docs/troubleshooting/runbooks/) | 38 operational procedures |
| [Drift Detection](docs/how-to-guides/drift-detection.md) | API contract, schema, and documentation drift detection |

### Architecture Decisions

| Document | Description |
|----------|-------------|
| [All ADRs](docs/explanations/adr/) | Architecture Decision Records |

### Meta

| Document | Description |
|----------|-------------|
| [`AGENTS.md`](AGENTS.md) | How to work with this repo as an AI agent |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Developer contribution guide |
| [`SECURITY.md`](SECURITY.md) | Vulnerability reporting |
| [`ROADMAP.md`](ROADMAP.md) | Completion status and roadmap |

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

## Summary

This comprehensive documentation provides a complete overview of the Fabric_4L platform as of 2026-05-06. Key points:

**Platform Status:**
- Launch Readiness: 95%
- 6-layer architecture with 75-100% completion per layer
- Frontend at ~90% completion with API integration
- DevOps/Infra at ~95% completion

**Strengths:**
- Comprehensive security model with JWT, RBAC, and tenant isolation
- Extensive test coverage (238+ test files, ~1,371 tests)
- Drift detection capabilities for contracts and documentation
- Ground Truth layer production-ready
- Strong CI/CD gates for contract compliance and security

**Known Gaps:**
- Test pass rate at 46.56% (needs improvement)
- SSO/OIDC integration in progress
- Some frontend pages still use mock data
- Production monitoring dashboards incomplete
- Layer-specific gaps documented per section

**Next Steps:**
1. Improve test pass rate by addressing failing and skipped tests
2. Complete SSO/OIDC integration (Task 69)
3. Wire remaining frontend pages to real backend APIs
4. Complete production monitoring and alerting setup
5. Fill layer-specific gaps identified in documentation
