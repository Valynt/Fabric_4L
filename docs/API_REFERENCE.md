# Value Fabric — API Reference

> **Version:** 1.0.0  
> **Base URLs:** Each layer runs as a separate service. Replace `<host>` with the appropriate service address.  
> **Source of truth:** the OpenAPI specs under [`contracts/openapi/`](../contracts/openapi/) are authoritative. This document is a human-readable summary kept in sync with those specs. When in doubt, trust the contract files. Regenerate specs via `make contracts`.

## Service ports

| Layer | Service | Port |
| ----- | ------- | ---- |
| 1 | layer1-ingestion    | 8001 |
| 2 | layer2-extraction   | 8002 |
| 3 | layer3-knowledge    | 8003 |
| 4 | layer4-agents       | 8004 |
| 5 | layer5-ground-truth | 8005 |
| 6 | layer6-benchmarks   | 8006 |

---

## Table of Contents

- [Authentication](#authentication)
- [Error Response Format](#error-response-format)
- [Layer 1 — Ingestion](#layer-1--ingestion)
- [Layer 2 — Extraction](#layer-2--extraction)
- [Layer 3 — Knowledge Graph](#layer-3--knowledge-graph)
- [Layer 4 — Agents](#layer-4--agents)
- [Layer 5 — Ground Truth](#layer-5--ground-truth)
- [Layer 6 — Benchmarks](#layer-6--benchmarks)
- [Health Endpoints](#health-endpoints)
- [Interactive Exploration](#interactive-exploration)

---

## Authentication

All API endpoints are secured by the shared identity middleware (`shared/identity`).

Every request **must** include the following headers:

| Header            | Required | Description                                      |
| ----------------- | -------- | ------------------------------------------------ |
| `Authorization`   | Yes      | `Bearer <token>` — a valid JWT issued by the identity service. |
| `X-Tenant-ID`     | Yes      | UUID of the tenant making the request. Used for data isolation and RBAC. |

Requests that omit or provide invalid credentials will receive a `401 Unauthorized` or `403 Forbidden` response.

---

## Error Response Format

All layers return errors in a consistent JSON envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description of the problem.",
    "details": {}
  }
}
```

| Field              | Type   | Description                                |
| ------------------ | ------ | ------------------------------------------ |
| `error.code`       | string | Machine-readable error code.               |
| `error.message`    | string | Human-readable explanation.                |
| `error.details`    | object | Optional additional context (field errors, trace IDs, etc.). |

### Common HTTP Status Codes

| Status | Meaning                |
| ------ | ---------------------- |
| 400    | Bad Request — validation failed. |
| 401    | Unauthorized — missing or invalid token. |
| 403    | Forbidden — insufficient permissions. |
| 404    | Not Found — resource does not exist. |
| 409    | Conflict — duplicate or state conflict. |
| 422    | Unprocessable Entity — semantically invalid input. |
| 429    | Too Many Requests — rate limit exceeded. |
| 500    | Internal Server Error. |

---

## Layer 1 — Ingestion

Intelligent web data ingestion powered by Playwright, Redis, and PostgreSQL.

**Base path:** `/api/v1/ingestion`

### Endpoints

| Method | Path                            | Description                          | Auth | Status |
| ------ | ------------------------------- | ------------------------------------ | ---- | ------ |
| GET    | `/api/v1/ingestion/targets`     | List all scraping targets.           | Yes  | 200    |
| POST   | `/api/v1/ingestion/targets`     | Create a new scraping target.        | Yes  | 201    |
| GET    | `/api/v1/ingestion/jobs`        | List ingestion jobs.                 | Yes  | 200    |
| POST   | `/api/v1/ingestion/jobs`        | Start a new ingestion job.           | Yes  | 201    |
| GET    | `/api/v1/ingestion/jobs/{id}`   | Get status / details of a specific job. | Yes  | 200    |

### Request / Response Schemas

#### POST `/api/v1/ingestion/targets`

**Request body:**

```json
{
  "url": "https://example.com",
  "schedule": "daily",
  "scrape_config": {
    "selectors": [".main-content"],
    "wait_for": "#loaded"
  }
}
```

**Response (201):**

```json
{
  "target_id": "uuid",
  "url": "https://example.com",
  "schedule": "daily",
  "status": "active",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### POST `/api/v1/ingestion/jobs`

**Request body:**

```json
{
  "target_id": "uuid",
  "priority": "normal"
}
```

**Response (201):**

```json
{
  "job_id": "uuid",
  "target_id": "uuid",
  "status": "queued",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### GET `/api/v1/ingestion/jobs/{id}`

**Response (200):**

```json
{
  "job_id": "uuid",
  "target_id": "uuid",
  "status": "completed",
  "started_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:01:00Z",
  "pages_scraped": 12,
  "errors": []
}
```

---

## Layer 2 — Extraction

Ontology-guided extraction using LLM + RDF/OWL.

**Base path:** `/api/v1/extraction`

### Endpoints

| Method | Path                                  | Description                                   | Auth | Status |
| ------ | ------------------------------------- | --------------------------------------------- | ---- | ------ |
| POST   | `/api/v1/extraction/extract`          | Submit content for ontology-guided extraction. | Yes  | 202    |
| GET    | `/api/v1/extraction/status/{id}`      | Poll the status of an extraction job.          | Yes  | 200    |

### Request / Response Schemas

#### POST `/api/v1/extraction/extract`

**Request body:**

```json
{
  "source_id": "uuid",
  "content": "Raw text or HTML content to extract from.",
  "ontology_id": "uuid",
  "options": {
    "extract_entities": true,
    "extract_relationships": true
  }
}
```

**Response (202):**

```json
{
  "extraction_id": "uuid",
  "status": "processing",
  "estimated_duration_seconds": 30
}
```

#### GET `/api/v1/extraction/status/{id}`

**Response (200):**

```json
{
  "extraction_id": "uuid",
  "status": "completed",
  "entities_found": 42,
  "relationships_found": 18,
  "results_url": "/api/v1/extraction/results/uuid"
}
```

---

## Layer 3 — Knowledge Graph

Knowledge graph API backed by Neo4j and pgvector.

**Base path:** `/v1`

### Endpoints

| Method | Path                         | Description                                 | Auth | Status |
| ------ | ---------------------------- | ------------------------------------------- | ---- | ------ |
| GET    | `/v1/value-trees`            | List value trees.                           | Yes  | 200    |
| POST   | `/v1/value-trees`            | Create a new value tree.                    | Yes  | 201    |
| GET    | `/v1/formulas`               | List formulas.                              | Yes  | 200    |
| POST   | `/v1/formulas`               | Create a new formula.                       | Yes  | 201    |
| GET    | `/v1/value-packs`            | List value packs.                           | Yes  | 200    |
| POST   | `/v1/value-packs`            | Create a new value pack.                    | Yes  | 201    |
| GET    | `/v1/formula-governance`     | List formula governance rules.              | Yes  | 200    |
| POST   | `/v1/formula-governance`     | Create a governance rule.                   | Yes  | 201    |
| GET    | `/v1/variables`              | List variables.                             | Yes  | 200    |
| POST   | `/v1/variables`              | Create a new variable.                      | Yes  | 201    |
| GET    | `/v1/benchmarks`             | List benchmarks.                            | Yes  | 200    |
| POST   | `/v1/benchmarks`             | Create a benchmark.                         | Yes  | 201    |
| POST   | `/v1/ingest`                 | Ingest data into the knowledge graph.       | Yes  | 201    |
| POST   | `/v1/search/hybrid`          | Hybrid semantic + graph search.             | Yes  | 200    |

### Request / Response Schemas

#### POST `/v1/search/hybrid`

**Request body:**

```json
{
  "query": "cost reduction strategies for manufacturing",
  "filters": {
    "industry": "manufacturing",
    "entity_types": ["value_driver", "formula"]
  },
  "limit": 20
}
```

**Response (200):**

```json
{
  "results": [
    {
      "id": "uuid",
      "type": "value_driver",
      "label": "Operational Efficiency",
      "score": 0.92,
      "metadata": {}
    }
  ],
  "total": 1
}
```

#### POST `/v1/ingest`

**Request body:**

```json
{
  "source": "extraction",
  "extraction_id": "uuid",
  "entities": [],
  "relationships": []
}
```

**Response (201):**

```json
{
  "ingested": {
    "entities": 42,
    "relationships": 18
  },
  "status": "completed"
}
```

---

## Layer 4 — Agents

Agentic engine with LangGraph orchestration, workflow management, analysis tools, and a REST API.

**Base path:** `/api/v1`

### Workflow Endpoints

| Method | Path                                        | Description                                | Auth | Status |
| ------ | ------------------------------------------- | ------------------------------------------ | ---- | ------ |
| POST   | `/api/v1/workflows`                         | Create and start a new workflow.           | Yes  | 201    |
| GET    | `/api/v1/workflows/{id}`                    | Get workflow status and details.           | Yes  | 200    |
| GET    | `/api/v1/workflows/{id}/events`             | Stream workflow events (SSE).              | Yes  | 200    |
| GET    | `/api/v1/workflows/{id}/result`             | Get workflow output / result.              | Yes  | 200    |
| DELETE | `/api/v1/workflows/{id}`                    | Cancel and delete a workflow.              | Yes  | 200    |
| POST   | `/api/v1/workflows/{id}/resume`             | Resume a paused workflow.                  | Yes  | 200    |
| POST   | `/api/v1/workflows/{id}/pause`              | Pause a running workflow.                  | Yes  | 200    |
| GET    | `/api/v1/workflows/active`                  | List all active workflows.                 | Yes  | 200    |

#### POST `/api/v1/workflows`

**Request body (`WorkflowCreateRequest`):**

```json
{
  "workflow_type": "roi_calculator",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "inputs": {},
  "priority": "NORMAL"
}
```

`workflow_type` is one of: `roi_calculator`, `whitespace_analysis`, `business_case`, `orchestrator`.

**Response (201) (`WorkflowCreateResponse`):**

```json
{
  "workflow_instance_id": "uuid",
  "status": "running",
  "estimated_duration_seconds": 45
}
```

#### GET `/api/v1/workflows/{id}`

**Response (200) (`WorkflowStatusResponse`):**

```json
{
  "workflow_instance_id": "uuid",
  "workflow_type": "roi_calculator",
  "status": "running",
  "current_state": "calculating",
  "current_node": "roi_compute",
  "progress_percentage": 65,
  "started_at": "2025-01-01T00:00:00Z",
  "completed_at": null,
  "error_count": 0,
  "has_output": false,
  "results": null,
  "tenant_id": "uuid",
  "user_id": "uuid",
  "priority": "NORMAL",
  "scheduler_status": "active"
}
```

#### GET `/api/v1/workflows/{id}/events`

Server-Sent Events (SSE) stream. Each event is a `WorkflowEvent`:

```json
{
  "event_id": "uuid",
  "event_type": "state_change",
  "timestamp": "2025-01-01T00:00:05Z",
  "message": "Transitioned to roi_compute node",
  "payload": {}
}
```

#### POST `/api/v1/workflows/{id}/resume`

**Request body (`WorkflowResumeRequest`):**

```json
{
  "user_id": "uuid",
  "resume_data": {},
  "tenant_id": "uuid"
}
```

**Response (200) (`WorkflowResumeResponse`):**

```json
{
  "workflow_instance_id": "uuid",
  "status": "running",
  "resumed_from_node": "human_review",
  "message": "Workflow resumed successfully",
  "estimated_completion_seconds": 30
}
```

#### POST `/api/v1/workflows/{id}/pause`

**Request body (`WorkflowPauseRequest`):**

```json
{
  "user_id": "uuid",
  "reason": "Awaiting manager approval",
  "tenant_id": "uuid"
}
```

**Response (200) (`WorkflowPauseResponse`):**

```json
{
  "workflow_instance_id": "uuid",
  "status": "paused",
  "paused_at": "2025-01-01T00:02:00Z",
  "current_node": "human_review",
  "message": "Workflow paused successfully"
}
```

### Analysis Endpoints

| Method | Path                            | Description                               | Auth | Status |
| ------ | ------------------------------- | ----------------------------------------- | ---- | ------ |
| POST   | `/api/v1/analysis/roi`          | Run an ROI analysis for a prospect.       | Yes  | 200    |
| POST   | `/api/v1/analysis/whitespace`   | Run a whitespace / gap analysis.          | Yes  | 200    |
| POST   | `/api/v1/cases`                 | Generate a business case document.        | Yes  | 200    |

#### POST `/api/v1/analysis/roi`

**Request body (`ROIAnalysisRequest`):**

```json
{
  "prospect_id": "uuid",
  "value_driver_ids": ["uuid1", "uuid2"],
  "prospect_data": {},
  "industry_vertical": "manufacturing",
  "company_size": "enterprise"
}
```

**Response (200) (`ROIAnalysisResponse`):**

```json
{
  "prospect_id": "uuid",
  "aggregated_roi": {
    "total_value": 1200000,
    "net_present_value": 950000,
    "payback_months": 8
  },
  "detailed_results": [],
  "benchmark_comparison": {}
}
```

#### POST `/api/v1/analysis/whitespace`

**Request body (`WhitespaceAnalysisRequest`):**

```json
{
  "prospect_id": "uuid",
  "prospect_needs": "We need to reduce operational costs and improve supply chain visibility.",
  "analysis_depth": "standard"
}
```

`analysis_depth` is one of: `quick`, `standard`, `deep`.

**Response (200) (`WhitespaceAnalysisResponse`):**

```json
{
  "prospect_id": "uuid",
  "extracted_needs": ["cost reduction", "supply chain visibility"],
  "gap_analysis": [],
  "opportunity_score": 0.85,
  "recommendations": []
}
```

#### POST `/api/v1/cases`

**Request body (`BusinessCaseRequest`):**

```json
{
  "prospect_id": "uuid",
  "opportunity_id": "uuid",
  "sections": ["executive_summary", "roi_analysis", "implementation_plan"],
  "output_format": "pdf"
}
```

`output_format` is one of: `pdf`, `docx`, `html`.

**Response (200) (`BusinessCaseResponse`):**

```json
{
  "case_id": "uuid",
  "title": "Business Case — Acme Corp",
  "summary": "Executive summary text...",
  "total_value": 1200000,
  "implementation_cost": 400000,
  "roi_ratio": 3.0,
  "payback_months": 8,
  "confidence_score": 0.88,
  "recommendations": [],
  "status": "generated",
  "created_at": "2025-01-01T00:00:00Z",
  "document_url": "/api/v1/cases/uuid/download",
  "page_count": 12,
  "file_size_bytes": 245760
}
```

### Tool Endpoints

| Method | Path                           | Description                           | Auth | Status |
| ------ | ------------------------------ | ------------------------------------- | ---- | ------ |
| GET    | `/api/v1/tools`                | List all available tools.             | Yes  | 200    |
| GET    | `/api/v1/tools/{name}`         | Get details of a specific tool.       | Yes  | 200    |
| POST   | `/api/v1/tools/invoke`         | Invoke a tool by name.                | Yes  | 200    |
| GET    | `/api/v1/tools/categories`     | List tool categories.                 | Yes  | 200    |

### Integration Endpoints

| Method | Path                           | Description                                    | Auth | Status |
| ------ | ------------------------------ | ---------------------------------------------- | ---- | ------ |
| POST   | `/api/v1/c1/stream`            | C1 proxy — stream agent responses (SSE).       | Yes  | 200    |
| POST   | `/api/v1/crm/salesforce`       | Salesforce CRM webhook receiver.               | Yes  | 200    |
| POST   | `/api/v1/crm/hubspot`          | HubSpot CRM webhook receiver.                  | Yes  | 200    |

---

## Layer 5 — Ground Truth

Ground-truth store and evaluation API for validating agent outputs.

**Base path:** `/api/v1`

### Endpoints

| Method | Path                        | Description                                   | Auth | Status |
| ------ | --------------------------- | --------------------------------------------- | ---- | ------ |
| GET    | `/api/v1/truths`            | List ground-truth records.                    | Yes  | 200    |
| POST   | `/api/v1/truths`            | Create a new ground-truth record.             | Yes  | 201    |
| POST   | `/api/v1/evaluations`       | Run an evaluation against ground truth.       | Yes  | 200    |

### Request / Response Schemas

#### POST `/api/v1/truths`

**Request body:**

```json
{
  "entity_id": "uuid",
  "entity_type": "formula",
  "expected_value": {},
  "source": "manual",
  "notes": "Verified by domain expert."
}
```

**Response (201):**

```json
{
  "truth_id": "uuid",
  "entity_id": "uuid",
  "entity_type": "formula",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### POST `/api/v1/evaluations`

**Request body:**

```json
{
  "evaluation_type": "accuracy",
  "agent_output_id": "uuid",
  "truth_ids": ["uuid1", "uuid2"]
}
```

**Response (200):**

```json
{
  "evaluation_id": "uuid",
  "score": 0.94,
  "passed": true,
  "details": {}
}
```

---

## Layer 6 — Benchmarks

Base path: `/v1/benchmarks` on port **8006**. Routes are defined in
[`services/layer6-benchmarks/src/api/routes/benchmarks.py`](../services/layer6-benchmarks/src/api/routes/benchmarks.py).
All handlers require an authenticated request context (`get_request_context`)
and are tenant-scoped where the underlying data model requires it.

| Method | Path | Description | Auth |
| ------ | ---- | ----------- | ---- |
| GET  | `/v1/benchmarks/datasets`                 | List benchmark datasets. Optional `industry` and `segment` query filters. | Yes |
| GET  | `/v1/benchmarks/datasets/{dataset_id}`    | Fetch a single dataset's detail. | Yes |
| POST | `/v1/benchmarks/compare`                  | Compare a tenant signal against peer datasets. | Yes |
| POST | `/v1/benchmarks/validate`                 | Statistically validate a candidate benchmark value. | Yes |
| GET  | `/v1/benchmarks/industries`               | List known industries available for benchmarking. | Yes |

### `GET /v1/benchmarks/datasets`

Returns `List[DatasetSummary]`. Filterable by:

- `industry` (query, optional)
- `segment`  (query, optional)

### `GET /v1/benchmarks/datasets/{dataset_id}`

Returns `DatasetDetail` for one dataset. 404 if the dataset is not visible to
the caller's tenant context.

### `POST /v1/benchmarks/compare`

**Request body:** `ComparisonRequestPayload`  
**Response:** `ComparisonResponse`

Produces a peer-comparison result for the supplied signal. Schema details live
in the OpenAPI spec under `contracts/openapi/` and the route schema module
[`services/layer6-benchmarks/src/api/schemas.py`](../services/layer6-benchmarks/src/api/schemas.py).

### `POST /v1/benchmarks/validate`

**Request body:** `ValidationRequestPayload`  
**Response:** `ValidationResponse`

Runs statistical validation (confidence, sample size, outlier checks) on a
candidate benchmark value.

### `GET /v1/benchmarks/industries`

Returns the list of industries the benchmark service knows about. Useful for
populating filter UIs prior to calling `/datasets`.

Layer 6 also exposes:

| Method | Path | Description | Auth |
| ------ | ---- | ----------- | ---- |
| GET | `/ready` | Readiness probe with backing-store status. | No |

---

## Health Endpoints

Every layer exposes a standard health check:

| Method | Path       | Description            | Auth | Status |
| ------ | ---------- | ---------------------- | ---- | ------ |
| GET    | `/health`  | Basic liveness probe.  | No   | 200    |
| GET    | `/ready`   | Readiness probe.       | No   | 200    |

**Response (200):**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

---

## Interactive Exploration

Every service mounts an interactive Swagger UI at `/docs` and a ReDoc view at
`/redoc` when run in non-production mode. Use these to explore live endpoints
against a running stack.

For offline tooling:

- **OpenAPI specs:** [`contracts/openapi/`](../contracts/openapi/) — authoritative source.
- **Generated TypeScript client:** [`apps/web/src/api/generated`](../apps/web/src/api/generated) — regenerated from the specs above.
- **Postman / Insomnia:** import any spec from `contracts/openapi/` directly into the tool of choice.
- **Contract governance:** [`contracts/GOVERNANCE.md`](../contracts/GOVERNANCE.md).

Regenerate everything: `make contracts`.

---

## Deprecation Schedule & Headers

Deprecated endpoints emit schedule headers so clients can migrate predictably:

- `Warning: 299 - "<message>"`
- `X-Deprecated-Since: YYYY-MM-DD`
- `X-Target-Removal-Date: YYYY-MM-DD`
- `X-Deprecation-Owner: <owner>`

Current schedule source of truth: `docs/deprecation_register.json`.

Highlighted routes:

| Endpoint | Preferred Replacement | Deprecated Since | Target Removal |
|---|---|---|---|
| `POST /v1/query` | `POST /v1/query/graph` | `2026-04-14` | `2026-08-01` |
| `POST /v1/search` | `POST /v1/search/hybrid` | `2026-04-14` | `2026-08-01` |
| `GET /health` (Layer 1 legacy route) | `GET /api/v1/ingestion/health` | `2026-04-14` | `2026-08-01` |
