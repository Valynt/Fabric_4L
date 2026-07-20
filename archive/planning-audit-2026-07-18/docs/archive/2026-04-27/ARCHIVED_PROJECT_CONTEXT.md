---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Historical background context
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Project Context - Value Fabric Architectural Audit

**Generated:** 2026-04-21
**Auditor:** Principal Staff Engineer
**Repository:** Fabric_4L (Value Fabric Enterprise AI Platform)

---

## 1. Architecture Overview

### Architectural Pattern: **Layered Microservices (6-Layer Stack)**

The Value Fabric platform follows a **layered microservices architecture** with clear separation of concerns across 6 functional layers. Each layer is a standalone service with its own Docker container, API, and data store.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 6: BENCHMARKS              (Port 8006)               │
│ Load testing, performance validation, SLO enforcement        │
├─────────────────────────────────────────────────────────────┤
│ LAYER 5: GROUND TRUTH            (Port 8005)               │
│ Truth state management, checkpoint/resume, audit logging    │
├─────────────────────────────────────────────────────────────┤
│ LAYER 4: AGENTIC WORKFLOW ENGINE (Port 8004)               │
│ LangGraph orchestration, multi-agent workflows, tool registry│
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: KNOWLEDGE GRAPH         (Port 8003/8001)          │
│ Neo4j graph store, GraphRAG retrieval, semantic layer      │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: ONTOLOGY EXTRACTION     (Port 8002)               │
│ LLM-based entity extraction, RDF/OWL generation             │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: DATA INGESTION          (Port 8001)               │
│ Playwright crawling, Celery workers, PII detection          │
└─────────────────────────────────────────────────────────────┘
```

### Module/Package Boundaries

| Module | Path | Responsibility |
|--------|------|----------------|
| **Layer 1 Ingestion** | `services/layer1-ingestion/` | Web crawling via Playwright, content extraction, rate limiting, robots.txt compliance, PII redaction |
| **Layer 2 Extraction** | `services/layer2-extraction/` | LLM-based entity extraction (Capability, UseCase, Persona, ValueDriver), relationship mapping, RDF/OWL output |
| **Layer 3 Knowledge** | `services/layer3-knowledge/` | Neo4j graph storage, vector embeddings, GraphRAG retrieval, hybrid search |
| **Layer 4 Agents** | `services/layer4-agents/` | LangGraph workflow engine, agent orchestration, tool registry (24 skills), checkpoint/resume |
| **Layer 5 Ground Truth** | `services/layer5-ground-truth/` | Truth state persistence, audit logging, ground truth evaluation |
| **Layer 6 Benchmarks** | `services/layer6-benchmarks/` | Performance testing, load testing, SLO validation |
| **Shared Identity** | `shared/identity/` | Cross-layer JWT auth, RBAC, tenant isolation, API key management |
| **Shared Audit** | `shared/audit/` | Append-only audit logging (DB trigger-enforced) |
| **Frontend** | `frontend/` | React 19 + TypeScript + Vite UI with tiered navigation |
| **Packs** | `packs/*/` | Domain verticals (life-sciences, financial-services, energy-utilities, etc.) |

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INGESTION (Layer 1)                                          │
│    URL → Playwright → Markdown + Metadata → PostgreSQL/Redis    │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 2. EXTRACTION (Layer 2)                                         │
│    Markdown → Chunking → LLM Extraction → Entities/Relations    │
│    → RDF/OWL + Provenance metadata                             │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 3. KNOWLEDGE GRAPH (Layer 3)                                  │
│    RDF → Neo4j Loader → Vector Embeddings (Pinecone)           │
│    → GraphRAG Index (Leiden communities)                       │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 4. AGENT WORKFLOWS (Layer 4)                                    │
│    Natural Language Query → Hybrid Search → Graph Traversal    │
│    → Agent Reasoning → Business Case / ROI Calculation         │
│    → Checkpoint to Layer 5                                     │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 5. GROUND TRUTH (Layer 5)                                       │
│    State persistence, audit trail, truth evaluation            │
│    → PostgreSQL with Alembic migrations                      │
└─────────────────────────────────────────────────────────────────┘
```

### External Dependencies & Integration Points

| Service | Layer | Integration Type | Purpose |
|---------|-------|------------------|---------|
| **OpenAI API** | L2, L4 | REST API | GPT-4o / Claude 3.5 for entity extraction and agent reasoning |
| **Neo4j** | L2, L3, L4 | Bolt protocol | Graph storage (5.x Community/Enterprise) |
| **PostgreSQL** | L1, L5 | SQL | Crawl state, ground truth persistence |
| **Redis** | L1, L2, L4 | Redis protocol | Celery queue, caching, rate limiting |
| **Pinecone** | L3 | REST API | Vector embeddings storage |
| **Vault/Infisical** | All | REST API | Secrets management |
| **Prometheus** | All | HTTP pull | Metrics collection |
| **Jaeger** | All | OTLP | Distributed tracing |
| **Salesforce API** | L4 | REST API | CRM sync for accounts |
| **Browserbase/Firecrawl** | L1 | REST API | Alternative crawling backends |

---

## 2. Tech Stack Inventory

### Backend (Python)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| Python | 3.11+ | Runtime | ✅ Current |
| FastAPI | >=0.115.0 | API framework | ✅ Current |
| Pydantic | v2 (>=2.9.0) | Data validation | ✅ Current |
| Uvicorn | >=0.32.0 | ASGI server | ✅ Current |
| LangGraph | >=0.2.0 | Agent orchestration | ✅ Current |
| LangChain | >=0.3.0 | LLM abstraction | ✅ Current |
| OpenAI SDK | >=1.54.0 | LLM integration | ✅ Current |
| Neo4j Python Driver | >=5.26.0 | Graph database | ✅ Current |
| SQLAlchemy | >=2.0.0 | ORM | ✅ Current |
| Alembic | >=1.13.0 | Migrations | ✅ Current |
| Celery | >=5.4.0 | Task queue | ✅ Current |
| Redis | >=5.2.0 | Cache/Queue | ✅ Current |
| asyncpg | >=0.30.0 | Async PostgreSQL | ✅ Current |
| structlog | >=24.4.0 | Structured logging | ✅ Current |
| prometheus-client | >=0.21.0 | Metrics | ✅ Current |
| opentelemetry-* | >=1.20.0 | Tracing | ✅ Current |
| rdflib | >=7.0.0 | RDF/OWL handling | ✅ Current |
| pytest | >=8.3.0 | Testing | ✅ Current |
| ruff | >=0.8.0 | Linting | ✅ Current |
| black | >=24.10.0 | Formatting | ✅ Current |
| mypy | >=1.13.0 | Type checking | ✅ Current |

**Security/Vulnerability Flags:**
- ⚠️ `infisicalsdk>=1.0.0` downgraded from v2 due to breaking changes (documented in `layer1-ingestion/pyproject.toml:47-49`)
- ⚠️ `pinecone-client>=3.0` may need upgrade to v6+ for latest features

### Frontend (TypeScript/React)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| React | ^19.2.1 | UI framework | ✅ Current |
| TypeScript | 5.6.3 | Type safety | ✅ Current |
| Vite | ^7.1.7 | Build tool | ✅ Current |
| TailwindCSS | ^4.1.14 | Styling | ✅ Current |
| Radix UI | ^1.x | Primitives | ✅ Current |
| TanStack Query | ^5.97.0 | Data fetching | ✅ Current |
| Zustand | ^5.0.12 | State management | ✅ Current |
| Wouter | ^3.3.5 | Routing | ✅ Current (patched) |
| React Hook Form | ^7.64.0 | Forms | ✅ Current |
| Zod | ^4.1.12 | Schema validation | ✅ Current |
| Recharts | ^2.15.2 | Charts | ✅ Current |
| Framer Motion | ^12.23.22 | Animations | ✅ Current |
| Lucide React | ^0.453.0 | Icons | ✅ Current |
| Playwright | ^1.47.0 | E2E testing | ✅ Current |
| Vitest | ^2.1.4 | Unit testing | ✅ Current |

**Deprecated/EOL Flags:**
- ⚠️ No ESLint configuration found in frontend (relies on TypeScript strict mode + Prettier)
- ⚠️ `vite-plugin-manus-runtime` (^0.0.57) - Custom plugin, maintenance burden

### Infrastructure & DevOps

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker Compose | v3.8 | Local orchestration |
| Kubernetes | 1.28+ | Production deployment |
| Prometheus | v2.54.1 | Monitoring |
| Grafana | 11.2.0 | Dashboards |
| Alertmanager | v0.28.1 | Alerting |
| Jaeger | 1.50 | Distributed tracing |
| Neo4j | 5-community/enterprise | Graph database |
| PostgreSQL | 15 | Relational database |
| Redis | 7-alpine | Cache/queue |
| Vault | latest | Secrets (dev mode) |

### Build System & CI/CD

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| **Build** | `Makefile` + `hatchling` (L2-L6), `setuptools` (L1) | Package building |
| **Lint** | `ruff` (all layers), `black` | Python linting/formatting |
| **Type Check** | `mypy` (per-layer flags in Makefile) | Static analysis |
| **Test** | `pytest` with markers (unit, integration, e2e, contract, security) | Testing |
| **CI/CD** | GitHub Actions (30+ workflows) | Automation |

**Key CI Workflows:**
- `test.yml` - Unit, integration, contract, security tests
- `pr-checks.yml` - PR validation (866 lines - comprehensive)
- `smoke-gate.yml` - Cross-layer integration validation
- `security-gates.yml` - OWASP, dependency scanning
- `e2e-tests.yml` - Playwright browser tests

### Deployment Targets

| Environment | Target | Configuration |
|-------------|--------|---------------|
| Local | Docker Compose | `docker-compose.full.yml` |
| Development | Kubernetes (K8s) | `k8s/` manifests |
| Production | EKS/GKE + Helm | Terraform planned |

---

## 3. Code Conventions & Standards

### Naming Conventions

| Element | Convention | Example | Files |
|---------|------------|---------|-------|
| **Files** | snake_case for Python, PascalCase for React | `llm_extractor.py`, `GraphExplorer.tsx` | All |
| **Functions** | snake_case (Python), camelCase (TS) | `extract_entities()`, `useGraphQuery()` | All |
| **Classes** | PascalCase | `CapabilityExtractor`, `GraphNode` | All |
| **Variables** | snake_case (Python), camelCase (TS) | `entity_id`, `isLoading` | All |
| **Constants** | UPPER_SNAKE_CASE | `MAX_CHUNK_SIZE`, `DEFAULT_TIMEOUT` | All |
| **Private** | Leading underscore | `_internal_helper()`, `_private_var` | Python |
| **Type Variables** | PascalCase, descriptive | `GraphNode`, `ExtractionConfig` | All |

### Linting Rules

**Python (Ruff):**
- Line length: 100 (L1), 88 (L3), 100 (L2, L4)
- Target: Python 3.11
- Enabled: E, F, I, N, W, UP, B, C4, SIM
- Ignored: E501 (line length), B008 (FastAPI Depends pattern), various SIM rules
- Google-style docstrings enforced

**Per-Layer Variations:**
- `layer1-ingestion`: Relaxed mypy (`disallow_untyped_defs=false`)
- `layer2-extraction`: Strict mypy, 85% coverage requirement
- `layer3-knowledge`: Strict mypy, 88 char line length
- `layer4-agents`: Moderate mypy (flexibility for agent patterns)

**Frontend:**
- Prettier for formatting
- TypeScript strict mode
- No ESLint configuration found (relies on TS compiler)

### Error Handling Strategy

**Pattern: Structured JSON Errors with HTTP Status Mapping**

```python
# Layer 2-4 pattern (from main.py files)
class FabricError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code

# FastAPI exception handlers registered globally
@app.exception_handler(FabricError)
async def fabric_error_handler(request: Request, exc: FabricError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message}
    )
```

**Error Categories:**
- `VALIDATION_ERROR` (400) - Pydantic validation failures
- `NOT_FOUND` (404) - Entity/mapping not found
- `CONFLICT` (409) - Duplicate/constraint violations
- `RATE_LIMITED` (429) - Throttling
- `INTERNAL_ERROR` (500) - Unexpected failures
- `SERVICE_UNAVAILABLE` (503) - Circuit breaker open

**Frontend Error Handling:**
- React Query error boundaries
- `ErrorBoundary` component at root
- `SectionError`, `InlineError` for partial failures
- Console logging guarded by `NODE_ENV === 'development'`

### Design Patterns Applied

| Pattern | Usage | Location |
|---------|-------|----------|
| **Repository Pattern** | Data access abstraction | `layer3-knowledge/src/db/`, `layer4-agents/src/repositories/` |
| **Dependency Injection** | FastAPI Depends for services | All API layers |
| **Circuit Breaker** | LLM/External service resilience | `layer4-agents/src/config/settings.py:139-148` |
| **Factory Pattern** | Test fixtures, mock generation | `tests/factories.py`, `frontend/src/test-utils.tsx` |
| **Observer Pattern** | SSE streaming, audit logging | `layer2-extraction/tests/test_sse_streaming.py` |
| **Strategy Pattern** | Crawler adapters (Playwright/HTTPX) | `layer1-ingestion/src/crawler/` |
| **Barrel Exports** | Consolidated imports | `frontend/client/src/components/index.ts`, `hooks/index.ts` |

---

## 4. Critical Paths Map

### Hot Paths (User-Facing, Must Be Fast)

| Path | Target | Current Status |
|------|--------|----------------|
| **Graph Query** | <50ms p95 single-hop, <200ms p95 multi-hop | ⚠️ Layer 3 Neo4j queries need monitoring |
| **Hybrid Search** | <500ms p95 | ⚠️ Vector + graph traversal |
| **Extraction Job** | <5 min end-to-end | ✅ Async Celery processing |
| **Formula Evaluation** | <100ms | ✅ In-memory calculation |
| **Agent Workflow** | <5 min whitespace analysis | ✅ LangGraph with checkpointing |
| **Frontend Page Load** | <3s TTI | ⚠️ Bundle size optimization needed |

### Database Query Patterns

**N+1 Risks Identified:**
1. **Layer 3** `services/layer3-knowledge/src/api/main.py`:
   - Lines 2091, 2133, 2152, 2171 - Node queries without `tenant_id` filtering
   - Lines 2672, 2704, 2725 - Graph queries matching by `id` only
   - **Risk:** Multi-tenant read security gap (documented in memory)

2. **Relationship Sampling** (Historical - Fixed):
   - Old pattern: Sample 5 nodes → N+1 context API calls
   - Fixed: New `/graph/subgraph` endpoint returns coherent subgraph

**Missing Indexes (Identified):**
- Neo4j: `tenant_id` index exists, but composite `(id, tenant_id)` constraints vary by edition
- PostgreSQL: Alembic migrations manage indexes per-layer

**Heavy Joins:**
- Graph traversal queries (3-hop max) - mitigated by community detection indexing
- Value tree calculations - formula dependencies resolved at query time

### Authentication/Authorization Flows

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Request Entry                                                │
│    JWT in Authorization header OR API key in X-API-Key header │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 2. Middleware (shared.identity.middleware.GovernanceMiddleware)│
│    - Decode JWT / verify API key                                │
│    - Extract tenant_id from claims                             │
│    - Rate limiting (RedisRateLimiter)                          │
│    - Feature flag evaluation                                    │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 3. Dependency Injection                                         │
│    require_tenant_admin / require_super_admin                  │
│    → RequestContext with user, tenant, permissions               │
└──────────────────────────────────┬──────────────────────────────┘
                                   ↓
┌──────────────────────────────────┴──────────────────────────────┐
│ 4. Handler Execution                                            │
│    - Row-level security: tenant_id filter on all queries       │
│    - Column-level masking for sensitive fields                   │
│    - Audit logging (shared.audit.emitter)                       │
└─────────────────────────────────────────────────────────────────┘
```

### Synchronous Blocking Operations

| Operation | Location | Mitigation |
|-----------|----------|------------|
| **LLM API calls** | L2 extraction, L4 agents | Async with timeout (60s), circuit breaker |
| **Neo4j queries** | L3 graph traversal | Connection pooling, query timeouts |
| **PDF processing** | L1 ingestion | Celery background tasks |
| **Document generation** | L4 business cases | Async WeasyPrint, streaming response |
| **Embedding generation** | L2, L3 | Batch processing, caching (Redis 7-day TTL) |

**Identified Blocking Issues:**
- ⚠️ `layer1-ingestion/src/crawler/decision_store.py:6-8` - FIXME: Async methods use sync SQLAlchemy calls (Risk #13)

---

## 5. Tech Debt Registry

### TODO/FIXME Comments

| Location | Issue | Priority |
|----------|-------|----------|
| `services/layer4-agents/tests/test_llm_cost_tracking.py:133` | Wire up actual metrics recording | P2 |
| `services/layer4-agents/tests/test_llm_cost_tracking.py:185` | Import actual CostRecord | P2 |
| `services/layer3-knowledge/src/api/models.py:957` | Deprecate legacy ontology fields | P2 |
| `services/layer3-knowledge/src/api/models.py:1011` | Deprecate 'type' field | P2 |
| `services/layer1-ingestion/src/shared/tasks.py:597` | Implement schema validation | P1 |
| `services/layer1-ingestion/src/crawler/decision_store.py:6-8` | Async methods use sync SQLAlchemy | **P0** |
| `services/layer1-ingestion/src/api/main.py:330` | Use cron-validator library | P2 |
| `sdk/python/src/valuefabric/cli/auth.py:148` | Implement callback server for token | P2 |
| `scripts/load_value_packs.py:149` | API integration pending | P2 |
| `frontend/client/src/hooks/useSources.ts:219` | Backend should add source_category | P2 |
| `frontend/client/src/pages/ValuePacks.test.tsx:117` | Error state not rendering (skipped test) | P1 |
| `frontend/client/src/pages/admin/VariableRegistry.tsx:238` | Invoke binding test via L3 API | P2 |
| `frontend/client/src/pages/Accounts.tsx:469` | Add account functionality pending | P1 |
| `frontend/client/src/stores/ontologyStore.ts:285,301` | Undo/redo state management | P2 |
| `frontend/client/src/components/ErrorBoundary.tsx:82` | Sentry/DataDog integration | P2 |
| `frontend/client/src/components/WfPrimitives.tsx:7` | Migrate to fabric components | P2 |
| `frontend/e2e/navigation.spec.ts:276` | Mobile navigation not implemented | P2 |

### Code Duplication Hotspots

| Pattern | Locations | Count | Recommendation |
|---------|-----------|-------|----------------|
| **API client setup** | Multiple hook files | 5+ | Consolidate to `client.ts` factory |
| **Error handling try/catch** | Test files | 5+ | Use `spyAndSuppress()` helper |
| **Mock response objects** | `useValuePacks.test.tsx` | 4 | Use `createMockResponse<T>()` factory |
| **Import patterns** | 34+ frontend files | Many | Migrate to barrel imports |
| **Retry configuration** | Multiple hooks | 3+ | Centralize retry policy |
| **Duplicate test contracts** | `tests/contract/` vs `tests/contracts/` | 2 | Merge directories |

### Large Files (>300 lines)

| File | Lines | Concern |
|------|-------|---------|
| `services/layer2-extraction/src/api/main.py` | 651+ | Monolithic API - consider router split |
| `services/layer3-knowledge/src/api/main.py` | ~3700 | **Critical** - Severely oversized, needs router decomposition |
| `services/layer4-agents/src/api/main.py` | ~4000 | **Critical** - Severely oversized |
| `frontend/client/src/pages/GraphExplorer.tsx` | 585 | Acceptable - complex visualization |
| `frontend/client/src/pages/ExtractionEngine.tsx` | ~400 | Acceptable - streaming UI complexity |
| `services/layer3-knowledge/src/api/models.py` | ~1000 | Large but models are declarative |

### Tight Coupling / Circular Dependencies

| Issue | Location | Severity |
|-------|----------|----------|
| **Cross-layer imports** | `shared/identity` imported by all layers | Medium - Intentional shared library |
| **Layer 4 → All layers** | L4 imports L1, L2, L3, L5, L6 | Medium - Orchestrator pattern |
| **Memory circular refs** | `stores/ontologyStore.ts` history management | Low - Functional, not import-based |

### Missing Error Handling

| Location | Gap | Risk |
|----------|-----|------|
| `layer1-ingestion/src/crawler/decision_store.py` | Sync calls in async context | Performance degradation |
| Frontend API hooks | Limited retry strategies | Poor UX on transient failures |
| `layer3-knowledge` read queries | Missing `tenant_id` filter | Data isolation breach |
| `layer4-agents` workflow errors | Partial checkpoint recovery | State inconsistency |

---

## 6. Testing Landscape

### Test Coverage Summary

| Module | Coverage | Tool | Notes |
|--------|----------|------|-------|
| **Layer 1** | ~75% | pytest-cov | Target: 80% |
| **Layer 2** | **85%+** | pytest-cov | ✅ Meets requirement |
| **Layer 3** | ~75% | pytest-cov | Integration heavy |
| **Layer 4** | ~70% | pytest-cov | Complex agent flows |
| **Layer 5** | ~80% | pytest-cov | State machine tests |
| **Frontend** | ~65% | Vitest coverage | 456 tests passing |
| **E2E** | N/A | Playwright | 30+ scenarios |

### Test Distribution

| Category | Count | Location |
|----------|-------|----------|
| **Unit tests** | ~2000 | Per-layer `tests/` directories |
| **Integration tests** | ~200 | `tests/integration/`, `tests/contract/` |
| **Security tests** | ~100 | `tests/security/` (OWASP, RBAC, tenant isolation) |
| **Contract tests** | ~50 | `tests/contract/` (OpenAPI validation) |
| **E2E tests** | ~30 | `frontend/e2e/` (Playwright) |
| **Evals** | ~20 | `tests/evals/` (golden traces) |
| **Chaos tests** | ~10 | `tests/chaos/` (tenant isolation load) |

### Untested Critical Paths

| Path | Risk | Mitigation |
|------|------|------------|
| **Neo4j Community edition constraints** | High | Test gap identified - L3 e2e fails on Community |
| **Checkpoint/resume (L4)** | High | `test_checkpoint_resume.py` exists but may not cover all failure modes |
| **LLM cost tracking** | Medium | TODO comments indicate unimplemented |
| **CRM sync (Salesforce)** | Medium | Mock-based tests, no live integration |
| **PII detection (Presidio)** | Medium | Limited coverage in L1 tests |

### Mocking Strategy

| Layer | Strategy | Tools |
|-------|----------|-------|
| **Backend** | pytest-mock, factory-boy, respx (HTTPX) | `@pytest.mark.asyncio`, `unittest.mock` |
| **Frontend** | MSW (Mock Service Worker), axios-mock-adapter | `test-utils.tsx` wrappers |
| **E2E** | Isolated Docker stack, testcontainers | Playwright fixtures |

**Anti-Patterns Identified:**
- ⚠️ `test.skip()` in `frontend/client/src/pages/ValuePacks.test.tsx:117` - Error state test disabled
- ⚠️ `test.fixme()` in `frontend/e2e/navigation.spec.ts:276` - Mobile navigation not implemented

### Flaky/Skipped Tests

| Test | Location | Reason |
|------|----------|--------|
| `displays error state with retry button` | `frontend/client/src/pages/ValuePacks.test.tsx:117` | Error state not rendering - implementation issue |
| `mobile menu is accessible` | `frontend/e2e/navigation.spec.ts:276` | Mobile UI not implemented (#456) |
| L4 checkpoint/resume tests | `services/layer4-agents/tests/` | ModuleNotFoundError importing 'src' during collection |
| L3 e2e pipeline tests | `services/layer3-knowledge/tests/` | Neo4j Community edition incompatibility |

---

## 7. Performance Baseline

### Bundle Size / Load Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Frontend main bundle** | ~850KB (estimated) | <500KB | ⚠️ Needs optimization |
| **Vite build time** | ~15s | <10s | ✅ Acceptable |
| **Type check time** | ~8s | <5s | ✅ Acceptable |
| **Docker image sizes** | Not measured | <500MB per layer | ⚠️ Unknown |

### Cold Start Times

| Service | Estimated | Target |
|---------|-----------|--------|
| **Layer 1** | ~3s | <5s |
| **Layer 2** | ~2s | <5s |
| **Layer 3** | ~4s (Neo4j connect) | <5s |
| **Layer 4** | ~5s (LangGraph init) | <5s |

### Large Dependencies (Tree-Shaking Candidates)

| Dependency | Size | Usage | Action |
|------------|------|-------|--------|
| `recharts` | ~250KB | Charts only on dashboard | ⚠️ Lazy load |
| `framer-motion` | ~100KB | Animations throughout | ⚠️ Consider CSS alternatives |
| `lucide-react` | ~50KB | Icons | ✅ Modular imports working |
| `lodash` | Not found | - | ✅ Not present |

### Memory Leaks / Resource Exhaustion Risks

| Risk | Location | Mitigation |
|------|----------|------------|
| **Redis connection leaks** | All layers | Connection pooling configured |
| **Neo4j driver sessions** | L3 | `with` context managers used |
| **Playwright browser instances** | L1 | Celery worker pool limits (concurrency=4) |
| **Log file growth** | Frontend | 1MB trim limit in `vite.config.ts:16` |
| **Workflow state accumulation** | L4 | 24-hour TTL in Redis |

### Caching Strategies

| Layer | Cache | TTL | Status |
|-------|-------|-----|--------|
| **L1** | robots.txt | 24 hours | ✅ Implemented |
| **L2** | Embeddings | 7 days | ✅ Redis TTL |
| **L2** | Raw LLM responses | 30 days | ✅ Audit requirement |
| **L3** | Vector search | Session | ⚠️ Query-level caching needed |
| **L3** | Graph query results | Not implemented | ❌ Missing |
| **L4** | Workflow state | 24 hours | ✅ Redis checkpoint |
| **Frontend** | React Query | Stale-while-revalidate | ✅ TanStack Query |

---

## Appendix A: File Reference Quick Links

### Key Configuration Files
- `docker-compose.full.yml` - Local orchestration
- `Makefile` - Build automation
- `pytest.ini` - Test configuration
- `frontend/vite.config.ts` - Frontend build
- `frontend/package.json` - Frontend dependencies

### Critical Source Files
- `shared/identity/__init__.py` - Auth exports
- `shared/identity/middleware.py` - Governance middleware
- `services/layer3-knowledge/src/api/main.py` - L3 API (lines 3700+)
- `services/layer4-agents/src/api/main.py` - L4 API (lines 4000+)
- `frontend/client/src/components/index.ts` - Component barrel
- `frontend/client/src/hooks/index.ts` - Hooks barrel

### Documentation
- `AGENTS.md` - Contributor guide
- `Architecture.md` - System architecture
- `ROADMAP.md` - Feature roadmap
- `TEST_STRATEGY.md` - Testing approach
- `SECURITY.md` - Security practices

---

**Confidence Levels:**
- **High** - Direct code inspection, configuration verified
- **Medium** - Inferred from patterns, partial inspection
- **Low** - Documentation-based, not directly verified

*Most metrics: High confidence*
*Performance baselines: Medium confidence (estimated)*
*Bundle sizes: Low confidence (no direct measurement)*
