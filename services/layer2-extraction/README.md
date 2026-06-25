# Layer 2: Ontology-Guided Extraction Pipeline
> Routing/versioning reference: see the canonical [Service Routing and API Version Matrix](../../docs/reference/service-routing-and-api-version-matrix.md).

> Runtime path governance: net-new Layer 2 logic must go to the canonical service runtime package under `services/layer2-extraction/src/layer2_extraction/`. The legacy `value_fabric/layer2/` namespace has been removed per [ADR-027](../../docs/explanations/adr/ADR-027-shim-removal.md). See [`docs/reference/layer-runtime-path-governance.md`](../../docs/reference/layer-runtime-path-governance.md).

Transforms unstructured Markdown content into structured RDF/OWL triples using LLM-guided extraction with strict schema compliance.

## Overview

Layer 2 is the semantic extraction service for the Value Fabric platform. It:
1. **Chunks** input Markdown into semantically meaningful segments
2. **Extracts** entities (Capabilities, UseCases, Personas, ValueDrivers) using LLM function calling
3. **Extracts** relationships between entities with evidence quotes
4. **Deduplicates** entities using embeddings (similarity threshold 0.85)
5. **Validates** all output against Pydantic schemas
6. **Generates** RDF/OWL with PROV-O provenance annotations

## Architecture

```
Input (Markdown)
    ↓
Semantic Chunker (LangChain, 2000 char chunks, 200 overlap)
    ↓
Entity Extractor (GPT-4o, temperature 0.0, function calling)
    ↓
Relationship Extractor (Evidence-backed relationships)
    ↓
Deduplicator (text-embedding-3-large, cosine similarity)
    ↓
RDF Generator (rdflib, Turtle format)
    ↓
Output (RDF/OWL + Provenance)
```

## Async Task Processing (Celery)

Layer 2 supports Celery-based async task processing for scalable queue-based extraction. This enables:

- **Queue-based processing**: Tasks are queued in Redis and processed by worker processes
- **Horizontal scaling**: Multiple workers can process extraction tasks in parallel
- **Retry logic**: Failed tasks are automatically retried with exponential backoff
- **Graceful degradation**: Falls back to HTTP if Celery is unavailable

### Celery Tasks

| Task | Description | Max Retries |
|------|-------------|-------------|
| `run_extraction_task` | Full extraction pipeline (chunk → extract → deduplicate → validate → RDF) | 3 |
| `extract_entities_task` | Entity extraction from content | 3 |
| `extract_relationships_task` | Relationship extraction between entities | 3 |

### Configuration

Environment variables for Celery:

```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Running Workers

Start Celery worker:

```bash
celery -A layer2_extraction.shared.tasks worker --loglevel=info --concurrency=2
```

With Docker Compose (dev):

```bash
docker compose -f docker-compose.dev.yml up layer2-worker
```

## Core Ontology

### Entity Types

| Type | Key Attributes | Description |
|------|---------------|-------------|
| **Capability** | `technical_features`, `api_endpoints`, `integrations`, `apqc_mapping` | Technical features with APQC PCF mapping |
| **UseCase** | `industry_context`, `required_capabilities`, `workflow_steps`, `kpis` | Business problems being solved |
| **Persona** | `role_type`, `title`, `department`, `pain_points`, `success_metrics` | Stakeholders in the buying process |
| **ValueDriver** | `category`, `metrics`, `formula_string`, `unit`, `time_to_value` | Quantifiable business outcomes |
| **APQCProcess** | `pcf_id`, `process_name`, `hierarchy_level` | APQC PCF reference process |

### Relationship Types

| Predicate | Direction | Description |
|-----------|-----------|-------------|
| `enables` | Capability → UseCase | Capability makes use case possible |
| `requires` | Capability → Capability | Capability requires another capability |
| `involves` | UseCase → Persona | Use case involves a persona |
| `delivers` | UseCase → ValueDriver | Use case delivers value outcome |
| `implemented_by` | Capability → Feature | Capability implemented by feature |
| `measured_by` | Capability → ValueMetric | Capability measured by metric |
| `maps_to_apqc` | Capability → APQCProcess | Maps to APQC PCF reference |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/extract` | POST | Start extraction job |
| `/v1/extract/status/{job_id}` | GET | Check job status |
| `/v1/extract/batch` | POST | Batch extraction |
| `/v1/ontology/entities` | GET | List entities |
| `/v1/ontology/relationships/{id}` | GET | Get entity relationships |
| `/v1/audit/trace/{job_id}` | GET | Full provenance chain |

## Usage

### Start Extraction

```bash
curl -X POST http://localhost:8000/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "doc-123",
    "source_url": "https://example.com/product",
    "markdown_content": "# Product\n\nOur platform...",
    "extraction_config": {
      "confidence_threshold": 0.75,
      "chunk_size": 2000
    }
  }'
```

Response:
```json
{
  "extraction_job_id": "uuid",
  "status": "queued",
  "message": "Extraction job started"
}
```

### Check Status

```bash
curl http://localhost:8000/v1/extract/status/{job_id}
```

Response:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "entities_extracted": 12,
  "relationships_extracted": 18,
  "rdf_output_path": "/app/rdf-output/uuid.ttl"
}
```

### Get Provenance

```bash
curl http://localhost:8000/v1/audit/trace/{job_id}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `LLM_MODEL` | `gpt-4o` | LLM model for extraction |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `RDF_OUTPUT_DIR` | `/tmp/rdf` | Where to save RDF files |
| `LOG_LEVEL` | `info` | Logging level |

## Cache failure behavior (operations runbook)

Layer 2's `ExtractionCache` is best-effort and fail-open by design so extraction workflows continue even if Redis is degraded.

- **Connect (`operation=connect`)**: If Redis client initialization fails, the service logs a structured warning/error and automatically falls back to in-memory LRU cache.
- **Read (`operation=read`)**: If Redis read or payload decode fails, the service logs a structured warning and continues with in-memory cache or cache miss behavior.
- **Write (`operation=write`)**: If Redis write or payload serialization fails, the service logs a structured warning and writes to in-memory cache when available.
- **Invalidate (`operation=invalidate`)**: If Redis close/invalidation fails during shutdown, the service logs a structured warning and continues shutdown.

Structured cache-failure logs include these fields for correlation when available: `operation`, `tenant_id`, `job_id`, `correlation_id`, and `exception_class`.

Operational expectation: cache failures must **never** fail the extraction request. Layer 2 continues the core extraction path with either in-memory fallback or a cache miss/recompute flow, so SLO impact is latency/cost (extra LLM calls), not availability.

## Development

### Setup

```bash
cd layer2-extraction
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Testing

```bash
# Run unit tests (no LLM calls)
pytest tests/ -v --ignore=tests/test_extraction.py

# Run integration tests (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
pytest tests/ -v
```

### Code Quality

```bash
# Formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

### Docker

```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f layer2-extraction
```

## Project Structure

```
layer2-extraction/
├── src/
│   ├── models/
│   │   ├── ontology.py         # Pydantic models
│   │   └── relationships.py    # Relationship types
│   ├── extraction/
│   │   ├── chunker.py         # Semantic chunking
│   │   ├── llm_extractor.py   # OpenAI extraction
│   │   └── deduplicator.py    # Embedding dedup
│   ├── output/
│   │   ├── rdf_generator.py   # Turtle serialization
│   │   └── provenance.py      # PROV-O tracking
│   └── api/
│       └── main.py            # FastAPI app
├── tests/
│   └── fixtures/              # Sample documents
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Acceptance Criteria

Per the Value Fabric specification:

- [x] Schema compliance: >95% pass Pydantic validation
- [x] No hallucinated entity types (strict schema enforcement)
- [x] Deduplication accuracy: >90% (embedding similarity 0.85)
- [x] Relationship precision: >85% (evidence required)
- [x] Throughput: 100 documents/hour per worker
- [x] RDF validates with Apache Jena (Turtle format)

## Dependencies

- **FastAPI**: REST API framework
- **Pydantic v2**: Data validation
- **OpenAI**: LLM for extraction (GPT-4o)
- **LangChain**: Semantic chunking
- **rdflib**: RDF/OWL generation
- **NumPy**: Embedding operations
- **Redis**: Job queue and caching

## Next Steps

1. Connect to Layer 3 (Neo4j) for persistence
2. Add Celery workers for distributed processing
3. Implement full APQC PCF mapping (currently basic mapping supported)
4. Add monitoring (Prometheus metrics)
5. Build ontology visualization tool

## Runtime path governance

- **Canonical runtime implementation:** `services/layer2-extraction/src/layer2_extraction/`
- **Canonical import namespace (consume here):** `layer2_extraction.*`
- **Removed legacy namespace:** `value_fabric/layer2/`

`value_fabric/layer2/` and `value_fabric/layer2_extraction/` were removed under ADR-027. Do not restore shim packages or add compatibility re-exports there, copy service files into them during builds, or add new `value_fabric.layer2.*` imports. Keep extraction, API, model, integration, and validation logic under `services/layer2-extraction/src/layer2_extraction/`.


## Migration reproducibility reference

- `docs/reference/migration-reproducibility-invariants.md` (mandatory migration invariants and incident-state reconstruction)
