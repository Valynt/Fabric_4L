# Layer 2 Extraction Engine - Gap Analysis Report

> ⚠️ **ARCHIVED CONTENT** (Date: 2026-04-19)
> This document refers to deprecated analysis that is no longer accurate. Layer 2 is now 90% complete. For current status, see [ROADMAP.md](../../ROADMAP.md) and the [Archive Registry](../archive-registry.md).

**Date:** April 18, 2026
**Status:** ⚠️ CRITICAL ISSUES IDENTIFIED - Not Production Ready
**Analyst:** AI Code Review

---

## 1. Current Extraction Engine Implementation Overview

### 1.1 Entrypoint & Module Structure

```
Entrypoint: uvicorn src.layer2_extraction.api.main:app --host 0.0.0.0 --port 8000
Module Root: services/layer2-extraction/src/layer2_extraction/
```

**Package Structure:**
```
layer2-extraction/
├── src/layer2_extraction/
│   ├── api/
│   │   ├── main.py              # FastAPI app, handlers, pipeline logic
│   │   ├── routes/
│   │   │   ├── extraction.py    # /v1/extract, /v1/extract-and-ingest
│   │   │   ├── ontology.py    # /v1/ontology/* (CRITICAL BUG HERE)
│   │   │   ├── audit.py       # Audit endpoints
│   │   │   └── system.py      # Health, metrics
│   │   ├── websocket/         # Real-time streaming
│   │   └── deps.py            # Request context
│   ├── extraction/
│   │   ├── llm_extractor.py   # Entity/Relationship extraction
│   │   ├── chunker.py         # Markdown chunking
│   │   ├── deduplicator.py    # Entity deduplication
│   │   └── prompts/           # LLM prompt templates
│   ├── integration/
│   │   ├── layer3_client.py   # Layer 3 ingestion client
│   │   └── pending_ingestion_store.py  # Retry queue
│   ├── models/
│   │   ├── ontology.py        # Pydantic models (Capability, UseCase, etc.)
│   │   ├── relationships.py   # Relationship types
│   │   └── extraction_response.py  # LLM response schemas
│   ├── output/
│   │   ├── rdf_generator.py   # RDF/Turtle generation
│   │   └── provenance.py      # Provenance tracking
│   ├── alignment/             # Semantic alignment
│   ├── validation/            # Entailment validation
│   ├── repositories/
│   │   └── ontology_schema_repository.py  # Ontology CRUD
│   ├── shared/
│   │   └── llm_client.py      # Unified OpenAI/Anthropic client
│   └── metrics.py             # Prometheus metrics
├── tests/                     # 251 test cases
├── Dockerfile
└── pyproject.toml
```

### 1.2 How Extraction Is Triggered

**Synchronous API Flow:**
1. Client POSTs to `/v1/extract` or `/v1/extract-and-ingest`
2. FastAPI creates a background task via `BackgroundTasks`
3. Immediate response returns `job_id` with status "queued"
4. Background task runs the 6-stage pipeline:
   - Stage 1: Chunking
   - Stage 2: Entity Extraction (LLM)
   - Stage 3: Relationship Extraction (LLM)
   - Stage 4: Semantic Alignment
   - Stage 5: Deduplication
   - Stage 6: Validation + RDF Generation
5. For extract-and-ingest: Layer3KnowledgeClient pushes to Neo4j

**Key Code (`api/main.py:1099-1133`):**
```python
@app.post("/v1/extract")
async def extract(request: ExtractRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    background_tasks.add_task(run_extraction, job_id=job_id, ...)
    return ExtractResponse(extraction_job_id=job_id, status="queued")
```

### 1.3 LLM Usage

**Provider Support:**
- OpenAI (gpt-4o, gpt-4o-mini, gpt-4-turbo)
- Anthropic (claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus)

**Structured Outputs:**
- Uses OpenAI's `beta.chat.completions.parse()` API with Pydantic models
- Extraction response models in `models/extraction_response.py`

**Prompt System:**
- System prompt: "You are an enterprise ontology extractor. Be precise and conservative."
- Entity-specific prompts in `extraction/prompts/`

### 1.4 Data Flow

```
Input (Layer 1)
    ↓ markdown_content + source_url + extraction_config
Chunker (chunk_markdown)
    ↓ chunks[]
EntityExtractor (LLM - structured output)
    ↓ {capabilities[], use_cases[], personas[], value_drivers[]}
RelationshipExtractor (LLM)
    ↓ relationships[]
SemanticAligner (embeddings + similarity)
    ↓ aligned_entities
Deduplicator
    ↓ deduplicated_entities
EntailmentValidator (6 validation rules)
    ↓ validated_result
RDF Generator
    ↓ .ttl file (Neo4j-ready)
Layer3KnowledgeClient.ingest_extraction_result()
    ↓ Neo4j (Layer 3)
```

### 1.5 Dependencies

**External APIs:**
- OpenAI API (or Anthropic)
- Layer 3 API (http://localhost:8001)

**Infrastructure:**
- PostgreSQL (pending_ingestion_store)
- SQLite (fallback for pending ingestion)
- Redis (not directly used in extraction, Celery referenced but not configured)
- Neo4j (via Layer 3 client)

**Python Dependencies (from pyproject.toml):**
- fastapi>=0.115.0
- openai>=1.40.0 (structured outputs)
- langchain>=0.3.0
- rdflib>=7.1.0
- asyncpg>=0.29.0
- alembic>=1.13.0

---

## 2. Intended Extraction Engine Behavior

### 2.1 Expected Input Handling

| Input Type | Status | Notes |
|------------|--------|-------|
| Raw URLs | ⚠️ Partial | Requires Layer 1 to fetch markdown first |
| Markdown documents | ✅ Implemented | Primary input format |
| Batch extraction | ✅ Implemented | `/v1/extract/batch` endpoint |
| Streaming upload | ❌ Missing | No multipart/chunked upload support |

### 2.2 Expected Output

| Output Type | Status | Notes |
|-------------|--------|-------|
| RDF/Turtle | ✅ Implemented | Saved to `/tmp/rdf/{job_id}.ttl` |
| Neo4j ingestion | ⚠️ Partial | Via Layer3KnowledgeClient, requires L3 healthy |
| Relational storage | ❌ Missing | No direct Postgres persistence of entities |
| Provenance chain | ✅ Implemented | Full audit trail in `output/provenance.py` |

### 2.3 Expected Async Execution

| Feature | Status | Notes |
|---------|--------|-------|
| Background tasks | ✅ Implemented | FastAPI `BackgroundTasks` |
| Celery integration | ❌ Not Configured | Celery in deps but no broker setup |
| Job status tracking | ✅ Implemented | In-memory `PIPELINE_JOBS` dict |
| SSE streaming | ✅ Implemented | `/v1/extract/jobs/{job_id}/events` |
| Retry with backoff | ✅ Implemented | Exponential backoff for L3 ingestion |

---

## 3. Gap Analysis (Implementation vs Intended)

### 3.1 Critical/Blocking Issues

| Issue | Severity | File | Description |
|-------|----------|------|-------------|
| **FastAPI Dependency Injection Bug** | 🔴 **CRITICAL** | `api/routes/ontology.py:145` | Using `Query(default_factory=get_repository)` for `OntologySchemaRepository` parameter. This is invalid - should use `Depends()`. Causes test collection failure. |
| **No Celery Broker** | 🟡 HIGH | `pyproject.toml` | Celery listed as dependency but no Redis/RabbitMQ broker configured. Background tasks use FastAPI's limited `BackgroundTasks` instead. |
| **In-Memory Job Store** | 🟡 HIGH | `api/main.py:265` | `PIPELINE_JOBS: dict[str, PipelineJob] = {}` - jobs lost on container restart. Should use Redis/Postgres. |

### 3.2 Architecture Gaps

| Gap | Impact | Current | Expected |
|-----|--------|---------|----------|
| **Job Persistence** | 🔴 HIGH | In-memory dict | Redis/Postgres job store |
| **Queue System** | 🟡 MEDIUM | FastAPI BackgroundTasks | Celery with Redis broker |
| **Schema Repository** | 🟡 MEDIUM | Has repository but DI broken | Proper FastAPI dependency injection |
| **Multi-tenancy** | 🟡 MEDIUM | Basic tenant_id passing | Full tenant isolation in all queries |

### 3.3 Data Pipeline Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| **Direct URL fetching** | 🟡 MEDIUM | ❌ Missing - requires L1 to fetch |
| **Batch job status tracking** | 🟡 MEDIUM | ⚠️ Partial - batch ID returned but no batch status endpoint |
| **Entity pagination** | 🟢 LOW | ❌ Not implemented - `list_entities` returns empty list |
| **Relationship queries** | 🟢 LOW | ❌ Stubbed - returns empty arrays |

### 3.4 LLM/Extraction Logic Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| **Anthropic structured outputs** | 🟡 MEDIUM | ❌ Not supported - raises ValueError |
| **Cost tracking** | ✅ GOOD | ✅ Implemented in `shared/llm_client.py` |
| **Prompt versioning** | 🟡 MEDIUM | ❌ Missing - prompts are static |
| **LLM fallback/retries** | 🟡 MEDIUM | ⚠️ Partial - has retries but no provider fallback |

### 3.5 Integration Gaps

| Gap | Impact | Status |
|-----|--------|--------|
| **Layer 1 → Layer 2** | 🟡 MEDIUM | ⚠️ Manual - requires `content_id`, `source_url`, `markdown_content` pre-fetched |
| **Layer 2 → Layer 3** | 🟡 MEDIUM | ✅ Implemented but requires healthy L3 |
| **Error propagation to L1** | 🟡 MEDIUM | ⚠️ Basic - SSE events but no callback/webhook |

---

## 4. Critical Failures (Blocking Issues)

### 4.1 Root Cause: FastAPI Dependency Injection Error

**Error Message:**
```
fastapi.exceptions.FastAPIError: Invalid args for response field!
Hint: check that <class 'layer2_extraction.repositories.ontology_schema_repository.OntologySchemaRepository'>
is a valid Pydantic field type.
```

**Root Cause Analysis:**

The `api/routes/ontology.py` file uses incorrect FastAPI dependency injection syntax:

```python
# ❌ WRONG (lines 145, 169, 193, etc.)
@router.get("/schema", response_model=OntologySchema)
async def get_ontology_schema(
    request: Request,
    repo: OntologySchemaRepository = Query(default_factory=get_repository),  # ← ERROR
):
```

**Why This Fails:**
1. `Query()` is for query parameters (URL `?key=value`)
2. `Query(default_factory=...)` tells FastAPI to treat `OntologySchemaRepository` as a Pydantic field type
3. `OntologySchemaRepository` is a class, not a Pydantic model
4. FastAPI tries to validate it as a response field and fails

**Correct Syntax:**
```python
from fastapi import Depends

# ✅ CORRECT
@router.get("/schema", response_model=OntologySchema)
async def get_ontology_schema(
    request: Request,
    repo: OntologySchemaRepository = Depends(get_repository),
):
```

**Impact:**
- Tests cannot collect (pytest fails during import)
- Application likely fails to start
- All 19 ontology endpoints affected

---

## 5. Data Pipeline Readiness

### 5.1 Layer 1 → Layer 2 Input

| Aspect | Status | Evidence |
|--------|--------|----------|
| Receives input | ⚠️ Partial | Requires pre-fetched markdown from L1 |
| Content validation | ✅ Implemented | Pydantic `ExtractRequest` model |
| Config extraction | ✅ Implemented | `extraction_config` with defaults |

### 5.2 Extraction Processing

| Aspect | Status | Evidence |
|--------|--------|----------|
| 6-stage pipeline | ✅ Implemented | `run_extraction()` in `api/main.py:575-932` |
| Chunking | ✅ Implemented | `chunk_markdown()` with size/overlap |
| Entity extraction | ✅ Implemented | `EntityExtractor.extract_entities()` |
| Relationship extraction | ✅ Implemented | `RelationshipExtractor.extract_relationships()` |
| Semantic alignment | ✅ Implemented | `SemanticAligner.align_entities()` |
| Deduplication | ✅ Implemented | `deduplicate_entities()` |
| Validation | ✅ Implemented | `EntailmentValidator` with 6 rules |
| RDF generation | ✅ Implemented | `generate_rdf()` |

### 5.3 Layer 2 → Layer 3 Output

| Aspect | Status | Evidence |
|--------|--------|----------|
| Neo4j ingestion | ⚠️ Partial | `Layer3KnowledgeClient.ingest_extraction_result()` |
| Retry logic | ✅ Implemented | Exponential backoff, max 5 retries |
| Pending queue | ✅ Implemented | `PendingIngestionStore` with SQLite/Postgres |
| Batch ingestion | ❌ Missing | Single entity at a time |

### 5.4 Persistence & State

| Aspect | Status | Evidence |
|--------|--------|----------|
| Job state | 🔴 BROKEN | In-memory dict - lost on restart |
| Provenance | ✅ Implemented | `output/provenance.py` with full chain |
| RDF files | ✅ Implemented | `/tmp/rdf/{job_id}.ttl` |
| Cost tracking | ✅ Implemented | Per-request cost records |

---

## 6. File-Level Mapping

### 6.1 API Layer

| File | Purpose | Status |
|------|---------|--------|
| `api/main.py` | FastAPI app, handlers, 6-stage pipeline | ⚠️ Has deprecated `@app.on_event` |
| `api/routes/extraction.py` | `/v1/extract*` endpoints | ✅ Clean |
| `api/routes/ontology.py` | `/v1/ontology*` endpoints | 🔴 **CRITICAL BUG** - Invalid DI |
| `api/routes/system.py` | Health, metrics | ✅ Working |
| `api/websocket/routes.py` | SSE streaming | ✅ Working |

### 6.2 Extraction Logic

| File | Purpose | Status |
|------|---------|--------|
| `extraction/llm_extractor.py` | Entity/Relationship extraction | ✅ Uses structured outputs |
| `extraction/chunker.py` | Markdown chunking | ✅ Token-aware |
| `extraction/deduplicator.py` | Entity deduplication | ✅ With coreference |
| `extraction/prompt_loader.py` | Prompt templates | ✅ Jinja2 |

### 6.3 Integration Layer

| File | Purpose | Status |
|------|---------|--------|
| `integration/layer3_client.py` | Layer 3 API client | ✅ Async httpx |
| `integration/pending_ingestion_store.py` | Retry queue | ✅ SQLite/Postgres backends |

### 6.4 Models & Schema

| File | Purpose | Status |
|------|---------|--------|
| `models/ontology.py` | Entity types (Capability, UseCase, etc.) | ✅ Pydantic v2 |
| `models/relationships.py` | Relationship types | ✅ Validated |
| `models/extraction_response.py` | LLM response schemas | ✅ Structured outputs |

### 6.5 Supporting Infrastructure

| File | Purpose | Status |
|------|---------|--------|
| `shared/llm_client.py` | Unified LLM client | ✅ Cost tracking |
| `repositories/ontology_schema_repository.py` | Schema CRUD | ⚠️ Not fully wired |
| `output/rdf_generator.py` | Turtle generation | ✅ Working |
| `output/provenance.py` | Audit trail | ✅ Complete |

---

## 7. Root Cause Diagnosis

### 7.1 Primary Failure: Import/Collection Error

**Symptom:** Tests fail during collection with FastAPI error about `OntologySchemaRepository`.

**Root Cause Chain:**
1. Developer used `Query(default_factory=get_repository)` for dependency injection
2. `Query` is meant for query parameters, not dependencies
3. FastAPI interprets this as: "I need to validate `OntologySchemaRepository` as a Pydantic field"
4. `OntologySchemaRepository` is a regular class, not a Pydantic model
5. FastAPI raises `FastAPIError: Invalid args for response field`

**Why It Happened:**
- Confusion between FastAPI's `Query`, `Depends`, and `Body` parameter classes
- Lack of integration testing (tests mock heavily, don't catch DI errors)
- Repository pattern implemented but not properly wired

### 7.2 Secondary Issues

| Issue | Root Cause |
|-------|------------|
| In-memory job store | Simplification for MVP, no Redis configured |
| Deprecated `@app.on_event` | Code written before FastAPI lifespan events |
| No Celery broker | Infrastructure complexity, BackgroundTasks deemed sufficient |
| Empty entity/relationship list endpoints | Neo4j integration deferred to Layer 3 |

---

## 8. Recommended Fix Plan (Execution-Ready)

### Phase 1: Critical Fix (Blocks All Testing)

**File:** `services/layer2-extraction/src/layer2_extraction/api/routes/ontology.py`

**Changes Required:**

1. **Add import at line 10:**
```python
from fastapi import APIRouter, HTTPException, Query, Request, Depends  # Add Depends
```

2. **Replace all `Query(default_factory=get_repository)` with `Depends(get_repository)`**

Affected lines: 145, 169, 193, 222, 235, 246, 260, 277, 296, 313, 329, 344, 362, 373, 393, 408, 429

Example fix for line 145:
```python
# Before:
repo: OntologySchemaRepository = Query(default_factory=get_repository)

# After:
repo: OntologySchemaRepository = Depends(get_repository)
```

**Verification:**
```bash
cd services/layer2-extraction
python -c "from layer2_extraction.api.main import app; print('✓ Import successful')"
pytest tests/test_extract_and_ingest_pipeline.py -v --collect-only
```

### Phase 2: Fix Deprecation Warnings

**File:** `services/layer2-extraction/src/layer2_extraction/api/main.py`

**Changes:**
Replace `@app.on_event` with lifespan context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global _retry_task
    if _retry_task is None:
        _retry_task = asyncio.create_task(_pending_ingestion_retry_loop())
    await _ws_manager.start()
    yield
    # Shutdown
    if _retry_task:
        _retry_task.cancel()
        try:
            await _retry_task
        except asyncio.CancelledError:
            pass
    await _ws_manager.stop()

app = FastAPI(lifespan=lifespan)
```

### Phase 3: Add Job Persistence

**File:** `services/layer2-extraction/src/layer2_extraction/api/main.py`

Replace `PIPELINE_JOBS: dict` with a proper store:

```python
# Add to startup
from layer2_extraction.integration.pending_ingestion_store import build_job_store

job_store = build_job_store()  # Implement similar pattern
```

### Phase 4: Integration Testing

```bash
# Test L2 independently
pytest tests/ -v --ignore=tests/test_ontology_alignment.py

# Test L2 → L3 integration (requires L3 running)
pytest tests/test_extract_and_ingest_pipeline.py -v
```

---

## 9. Final Verdict

### 9.1 Is the Extraction Engine Currently Functional?

**NO** - The Layer 2 Extraction Engine has a critical blocking bug that prevents:
- Application startup (likely)
- Test execution (confirmed)
- Ontology endpoint access (19 endpoints affected)

### 9.2 Issue Classification

| Category | Count | Issues |
|----------|-------|--------|
| **Runtime/Configuration** | 1 | FastAPI DI syntax error |
| **Missing Implementation** | 3 | Celery broker, job persistence, URL fetching |
| **Architectural Mismatch** | 2 | In-memory state, BackgroundTasks vs Celery |

### 9.3 Top 3 Blockers Preventing Production Use

| Rank | Blocker | Impact | Fix Effort |
|------|---------|--------|------------|
| **1** | **FastAPI Dependency Injection Bug** | 🔴 CRITICAL | 15 minutes |
| **2** | **In-Memory Job Store** | 🔴 HIGH | 2-4 hours |
| **3** | **No Celery Broker** | 🟡 MEDIUM | 4-8 hours |

### 9.4 Production Readiness Score

| Area | Score | Notes |
|------|-------|-------|
| Extraction Logic | 85% | 6-stage pipeline complete |
| LLM Integration | 90% | Structured outputs, cost tracking |
| API Surface | 40% | Critical bug in ontology routes |
| Data Pipeline | 60% | L2→L3 working, L1→L2 manual |
| Persistence | 30% | In-memory only |
| Observability | 70% | Metrics, provenance, SSE |
| **Overall** | **62%** | **Not production ready** |

### 9.5 Recommended Actions

**Immediate (Today):**
1. Fix the `Query()` → `Depends()` bug in `ontology.py`
2. Verify all tests pass
3. Run end-to-end extraction test

**Short-term (This Week):**
1. Implement Redis-based job store
2. Add Celery worker configuration
3. Configure proper Postgres connection for pending ingestion

**Medium-term (This Month):**
1. Add direct URL fetching capability
2. Implement entity pagination endpoints
3. Add webhook callbacks for job completion

---

## Appendix: Evidence Sources

1. **Test Collection Error:** `pytest tests/test_extract_and_ingest_pipeline.py` output showing FastAPIError
2. **Source Code:** `api/routes/ontology.py` lines 145, 169, 193 showing incorrect `Query()` usage
3. **Architecture:** `api/main.py` showing 6-stage pipeline implementation
4. **Dockerfile:** Shows PYTHONPATH and startup command configuration
5. **System Diagnostics:** `SYSTEM_DIAGNOSTICS.md` showing operational status

---

**End of Report**
