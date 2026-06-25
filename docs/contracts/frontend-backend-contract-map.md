# Frontend-Backend Contract Map

> **Status:** Draft — alignment package for Fabric_4L  
> **Scope:** Map every frontend query domain to its canonical backend endpoint.  
> **Principle:** Backend layers = capabilities. Frontend modules = product workflows. This document makes the translation explicit.

---

## Legend

| Status | Meaning |
|--------|---------|
| `implemented` | Both frontend and backend exist and agree on path, method, and shape. |
| `partially-implemented` | Endpoint exists on both sides but shape or params differ; normalization required. |
| `stubbed` | Frontend has query key / hook but backend endpoint is missing or mocked. |
| `missing` | Frontend expects an endpoint that does not exist in backend docs or code. |
| `unknown` | Could not verify backend existence; may be composed or gateway-routed. |

---

## Layer 1 — Ingestion

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Ingestion Jobs | `QK.ingestion.jobs()` | L1 | `/api/v1/ingestion/jobs` | GET | `limit`, `offset`, `status`, `sort_by` | — | `JobListResponse` (paginated) | `X-Tenant-ID` mandatory, Bearer JWT | `implemented` | Frontend path: `GET l1 /jobs`. Vite proxy rewrites `/api/v1/ingest/*` → `/api/v1/ingestion/*`. |
| Ingestion Recent | `QK.ingestion.recent()` | L1 | `/api/v1/ingestion/jobs?limit=&sort_by=created_at` | GET | `limit`, `sort_by` | — | `JobListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Same endpoint as list with filters. |
| Ingestion Stats | `QK.ingestion.stats()` | L1 | `/api/v1/ingestion/jobs?limit=1` | GET | `limit=1` | — | `JobListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend uses `limit=1` to infer stats; prefers dedicated `/compliance/summary` in future. |
| Ingestion Detail | `QK.ingestion.detail(id)` | L1 | `/api/v1/ingestion/jobs/{job_id}` | GET | `job_id` path param | — | `ApiJobDetailDto` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Ingestion Logs | `QK.ingestion.logs(id)` | L1 | `/api/v1/ingestion/compliance/logs?job_id={id}` | GET | `job_id` query param | — | `ApiComplianceLogDto[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Ingestion Retry | — | L1 | `/api/v1/ingestion/jobs/{job_id}/retry` | POST | `job_id` path param | — | `ApiIngestionJobDto` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Ingestion Cancel | — | L1 | `/api/v1/ingestion/jobs/{job_id}` | DELETE | `job_id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source List | `QK.sources.list(filters)` | L1 | `/api/v1/ingestion/targets` | GET | `page`, `limit`, `search`, `status` | — | `SourceListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend path: `GET l1 /targets`. |
| Source Detail | `QK.sources.detail(id)` | L1 | `/api/v1/ingestion/targets/{target_id}` | GET | `target_id` path param | — | `DataSource` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Create | — | L1 | `/api/v1/ingestion/targets` | POST | — | `CreateSourceRequest` | `DataSource` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Update | — | L1 | `/api/v1/ingestion/targets/{target_id}` | PUT | `target_id` path param | `UpdateSourceRequest` | `DataSource` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Delete | — | L1 | `/api/v1/ingestion/targets/{target_id}` | DELETE | `target_id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Validate | — | L1 | `/api/v1/ingestion/targets/{target_id}/validate` | POST | `target_id` path param | — | `TestConnectionResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Execute | — | L1 | `/api/v1/ingestion/targets/{target_id}/execute` | POST | `target_id` path param | — | `ApiIngestionJobDto` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Source Stats | `QK.sources.stats` | L1 | `/api/v1/ingestion/targets?page=1&limit=1000` | GET | `page`, `limit` | — | `SourceListResponse` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Frontend aggregates client-side; no dedicated stats endpoint. Prefer backend aggregation. |

---

## Layer 2 — Extraction

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Extraction Job | `QK.extraction.job(id)` | L2 | `/v1/extract/status/{job_id}` | GET | `job_id` path param | — | `ExtractionStatusResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend must call `/v1/extract/status/{job_id}`. The legacy `/v1/jobs/{job_id}` alias was removed. |
| Extraction Results | `QK.extraction.results(id)` | L2 | — | — | — | — | — | — | `missing` | Frontend defines query key but no corresponding backend endpoint found for raw results retrieval. |
| Extraction Create | — | L2 | `/v1/extract` | POST | — | `ExtractRequest` | `ExtractResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Not currently consumed by frontend hooks; used directly in workflows. |
| Extraction Batch | — | L2 | `/v1/extract/batch` | POST | — | `ExtractRequest[]` | `{ total_jobs: number }` | `X-Tenant-ID`, Bearer JWT | `implemented` | Not currently consumed by frontend hooks. |
| Extraction Events (SSE) | — | L2 | `/v1/extract/jobs/{job_id}/events` | SSE | `job_id` path param | — | SSE stream | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend polls instead of using SSE today. |
| Signal Extraction | — | L2 | `/v1/extract/signals` | POST | — | `SignalExtractionRequest` | `SignalExtractionResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Consumed by L4 workflows, not directly by frontend. |

**🔴 Layer 2 Mismatch Detail:**
- **Frontend call:** `apiClient.get('l2', '/extract/status/{jobId}')` → resolved via baseURL `/api/extract` or `/api/v1/extract` → Vite proxy strips prefix → backend receives `/extract/status/{jobId}`.
- **Backend actual:** `/v1/extract/status/{job_id}` (in `extraction.py`).
- **Gap resolved:** The legacy `/v1/jobs/{job_id}` alias was removed. Frontend must use the canonical route. `tier_policy.py` still references `/jobs` for tier mapping, but that is a policy artifact for historical route prefixes, not a live route.

---

## Layer 3 — Knowledge Graph

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Graph Query | `QK.graph.query(params)` | L3 | `/v1/query/graph` | POST | — | `GraphQueryRequest` | `GraphQueryResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Zod-validated in frontend (`GraphQueryResponseSchema`). |
| Graph Stream | — | L3 | `/v1/query/graph/stream` | POST | — | `GraphQueryRequest` | Streaming response | `X-Tenant-ID`, Bearer JWT | `implemented` | Not yet consumed by frontend hooks. |
| Entity Context | `QK.graph.context(entityId, hops)` | L3 | `/v1/entity/{entity_id}/context` | GET | `entity_id` path, `hops` query | — | `EntityContextResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Zod-validated (`EntityContextResponseSchema`). |
| Entity Traversal | `QK.graph.traversal(params)` | L3 | `/v1/entity/traverse` | POST | — | `EntityTraversalRequest` | `EntityTraversalResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Zod-validated (`EntityTraversalResponseSchema`). |
| Subgraph | `QK.graph.subgraph(...)` | L3 | `/v1/graph/subgraph` | GET | `query`, `center_entity_id`, `depth`, `limit` | — | `SubgraphResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend path updated to `/graph/subgraph` to align with backend router prefix. |
| Entity List | `QK.entities.list()` | L3 | `/v1/entities` | GET | `page`, `limit`, `search_text`, `entity_type` | — | `EntityListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Entity Search | `QK.entities.search(query)` | L3 | `/v1/entities?search_text={query}` | GET | `search_text` | — | `EntityListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Entity Detail | `QK.entities.detail(id)` | L3 | `/v1/entities/{entity_id}` | GET | `entity_id` path, `include_provenance`, `include_relationships` | — | `Entity` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula List | `QK.formulas.list(filters)` | L3 | `/v1/formulas` | GET | `status`, `owner`, `search` | — | `Formula[]` paginated | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula Detail | `QK.formulas.detail(id)` | L3 | `/v1/formulas/{id}` | GET | `id` path param | — | `Formula` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula Create | — | L3 | `/v1/formulas` | POST | — | `CreateFormulaInput` | `Formula` | `X-Tenant-ID`, Bearer JWT | `missing` | Backend router does not implement plain POST /formulas. Use `/v1/formulas/evaluate` or `/v1/formulas/scenario` instead. |
| Formula Update | — | L3 | `/v1/formulas/{id}` | PATCH | `id` path param | `UpdateFormulaInput` | `Formula` | `X-Tenant-ID`, Bearer JWT | `missing` | Backend router does not implement PATCH /formulas/{id}. |
| Formula Delete | — | L3 | `/v1/formulas/{id}` | DELETE | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `missing` | Backend router does not implement DELETE /formulas/{id}. |
| Formula Evaluate | — | L3 | `/v1/formulas/evaluate` | POST | — | `FormulaEvaluationInput` | `FormulaEvaluationResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula Scenario | — | L3 | `/v1/formulas/scenario` | POST | — | `{ formula_id, variables }` | `FormulaEvaluationResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | Consumed by Thesys C1 (`thesysClient.ts`). |
| Formula Approvals | `QK.formulas.approvals` | L3 | `/v1/formulas/approvals/pending` | GET | — | — | `ApprovalRequest[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula Approve | — | L3 | `/v1/formulas/{id}/approve` | POST | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Formula Submit | — | L3 | `/v1/formulas/{id}/submit` | POST | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack List | `QK.valuePacks.list(filters)` | L3 | `/v1/packs` | GET | `industry`, `status`, `scope` | — | `ValuePack[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Detail | `QK.valuePacks.detail(id)` | L3 | `/v1/packs/{id}` | GET | `id` path param | — | `ValuePack` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Apply | — | L3 | `/v1/packs/{id}/apply` | POST | `id` path param | — | `ApplyValuePackResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Framework | — | L3 | `/v1/valuepacks/{industryId}` | GET | `industryId` path param | — | `ValuePackFrameworkData` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Ontology Map | — | L3 | `/v1/valuepacks/ontology-map` | GET | — | — | `OntologyMapData` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Templates | — | L3 | `/v1/valuepacks/composable-templates` | GET | — | — | `TemplateLibraryData` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Pack Compare | — | L3 | `/v1/valuepacks/compare` | POST | — | `ValuePackComparisonRequest` | `ValuePackComparisonData` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Model List | `QK.models.list(filters)` | L3 | `/v1/models` | GET | `folder`, `status`, `search` | — | `ValueModel[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Model Folders | `QK.models.folders()` | L3 | `/v1/models/folders` | GET | — | — | `ModelFolder[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Model Create | — | L3 | `/v1/models` | POST | — | `CreateModelPayload` | `ValueModel` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Model Delete | — | L3 | `/v1/models/{id}` | DELETE | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Value Tree | `QK.valueTrees.tree(...)` | L3 | `/v1/value-trees/{entity_id}` | GET | `entity_id` path, `direction`, `max_depth` | — | `ValueTreeResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Zod schema exists (`ValueTreeResponseSchema`). |
| Value Tree Paths | `QK.valueTrees.paths(...)` | L3 | `/v1/value-trees/{entity_id}/paths` | GET | `entity_id` path, `direction`, `max_depth` | — | `ValueTreePath[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Product List | `QK.products.list(filters)` | L3 | `/v1/products` | GET | `page`, `limit`, `search` | — | `ProductListResponse` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Backend route exists; frontend types inferred, not strongly typed. |
| Product Detail | `QK.products.detail(id)` | L3 | `/v1/products/{id}` | GET | `id` path param | — | `Product` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |
| Evidence List | `QK.evidence.list(filters)` | L3 | `/v1/evidence/case-studies` | GET | `page`, `limit`, `industry`, `product_id` | — | `CaseStudyListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/evidence/case-studies`. |
| Evidence Detail | `QK.evidence.detail(id)` | L3 | `/v1/evidence/case-studies/{id}` | GET | `id` path param | — | `CaseStudy` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/evidence/case-studies/{id}`. |
| Competitive List | `QK.competitive.list(filters)` | L3 | `/v1/competitive/competitors` | GET | `page`, `limit`, `industry` | — | `CompetitorListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/v1/competitive/competitors`. |
| Competitive Detail | `QK.competitive.detail(id)` | L3 | `/v1/competitive/competitors/{id}` | GET | `id` path param | — | `Competitor` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/v1/competitive/competitors/${id}`. |
| Competitive Battlecards | `QK.competitive.battlecards(id)` | L3 | `/v1/competitive/competitors/{id}/battlecards` | GET | `id` path param | — | `Battlecard` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/v1/competitive/competitors/${id}/battlecards`. Alias `/battlecard` also added for compatibility. |
| Competitive Win/Loss Summary | `QK.competitive.winLoss(id)` | L3 | `/v1/competitive/win-loss/summary` | GET | `competitor_id` query param | — | `WinLossSummary[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/competitive/win-loss/summary`. |
| Competitive Landscape | `QK.competitive.landscape(productId)` | L3 | `/v1/competitive/landscape` | GET | `product_id` query | — | `LandscapeResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/v1/competitive/landscape`. |
| ROI List | `QK.roi.list(filters)` | L3 | `/v1/roi/calculations` | GET | `page`, `limit`, `prospect_id` | — | `ROICalculationListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/roi/calculations`. |
| ROI Detail | `QK.roi.detail(id)` | L3 | `/v1/roi/calculations/{id}` | GET | `id` path param | — | `ROICalculation` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/roi/calculations/{id}`. |
| ROI Templates | `QK.roi.templates()` | L3 | `/v1/roi/templates` | GET | — | — | `ROITemplate[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/roi/templates`. |
| ROI Benchmarks | `QK.roi.benchmarks(industry)` | L3 | `/v1/roi/benchmarks/{industry}` | GET | `industry` path param | — | `IndustryBenchmark` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend hook calls `/v1/roi/benchmarks/{industry}`. |
| Benchmark List | `QK.benchmarks.list(filters)` | L3 | `/v1/roi/benchmarks` | GET | `category`, `industry` | — | `Benchmark[]` | `X-Tenant-ID`, Bearer JWT | `missing` | Backend only provides `/v1/roi/benchmarks/{industry}`; no list endpoint without industry param. |
| Variable List | `QK.variables.list(filters)` | L3 | `/v1/variables` | GET | `category`, `search` | — | `Variable[]` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |

---

## Layer 4 — Agents / Workflows / Intelligence

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Workflow Create | — | L4 | `/v1/workflows` | POST | — | `WorkflowCreateRequest` | `WorkflowCreateResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Status | `QK.workflows.detail(id)` | L4 | `/v1/workflows/{workflow_id}` | GET | `workflow_id` path param | — | `WorkflowStatusResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Result | `QK.businessCases.detail(id)` | L4 | `/v1/workflows/{workflow_id}/result` | GET | `workflow_id` path param | — | `WorkflowResultResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow List Active | `QK.workflows.active()` | L4 | `/v1/workflows/active` | GET | `limit`, `offset`, `status` | — | `PaginatedWorkflows` | `X-Tenant-ID`, Bearer JWT | `implemented` | Backend supports pagination; frontend normalizes multiple response shapes. |
| Workflow History | `QK.workflows.history()` | L4 | `/v1/workflows/active` | GET | `limit`, `offset` | — | `PaginatedWorkflows` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend uses same endpoint as active with pagination params. |
| Workflow Types | — | L4 | `/v1/workflows/types` | GET | — | — | `{ workflows: { type, name, description }[] }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Cancel | — | L4 | `/v1/workflows/{workflow_id}` | DELETE | `workflow_id` path param | — | `{ workflow_id, status }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Pause | — | L4 | `/v1/workflows/{workflow_id}/pause` | POST | `workflow_id` path param | `{ user_id, reason }` | `WorkflowPauseResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Resume | — | L4 | `/v1/workflows/{workflow_id}/resume` | POST | `workflow_id` path param | `{ user_id, resume_data }` | `WorkflowResumeResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Workflow Events (SSE) | — | L4 | `/v1/workflows/{workflow_id}/events` | SSE | `workflow_id` path param | — | SSE stream of `WorkflowEvent` | `X-Tenant-ID`, Bearer JWT | `implemented` | Consumed via `EventSource` in `useWorkflows.ts`. |
| Business Case List | `QK.businessCases.list(filters)` | L4 | `/v1/workflows?type=business_case&...` | GET | `type=business_case`, `limit`, `offset`, `status` | — | `PaginatedWorkflows` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Backend OpenAPI spec does not document `?type=` filter on `/v1/workflows`. Route exists in code but spec may lag. |
| Business Case Create | — | L4 | `/v1/workflows` | POST | — | `WorkflowCreateRequest` (type=`business_case`) | `WorkflowCreateResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Business Case Archive | — | L4 | `/v1/workflows/{id}/archive` | POST | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Route not found in OpenAPI spec; may be custom or missing. |
| Intelligence Briefing | `QK.intelligence.briefing(id)` | L4 | `/v1/intelligence/account/{id}/briefing` | GET | `id` path param | — | `AccountBriefing` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Intelligence Deal Readiness | `QK.intelligence.dealReadiness(id)` | L4 | `/v1/intelligence/account/{id}/deal-readiness` | GET | `id` path param | — | `DealReadiness` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Intelligence Pipeline | `QK.intelligence.pipeline()` | L4 | `/v1/intelligence/pipeline-summary` | GET | — | — | `PipelineSummary` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Narrative List | `QK.narratives.list(filters)` | L4 | `/v1/narratives` | GET | `limit`, `offset`, `status`, `account_id` | — | `NarrativeListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Narrative Detail | `QK.narratives.detail(id)` | L4 | `/v1/narratives/{id}` | GET | `id` path param | — | `Narrative` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Narrative Generate | — | L4 | `/v1/narratives/generate` | POST | — | `GenerateNarrativeRequest` | `Narrative` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Narrative Update Status | — | L4 | `/v1/narratives/{id}/status` | PATCH | `id` path param | `{ status }` | `Narrative` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Narrative Delete | — | L4 | `/v1/narratives/{id}` | DELETE | `id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account List | `QK.accounts.list(filters)` | L4 | `/v1/accounts` | GET | `limit`, `offset`, `search`, `industry` | — | `AccountListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Detail | `QK.accounts.detail(id)` | L4 | `/v1/accounts/{id}` | GET | `id` path param | — | `Account` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Activity | `QK.accounts.activity(id)` | L4 | `/v1/accounts/{id}/activity` | GET | `id` path, `since_days` query | — | `AccountActivity` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Sync Status | `QK.accounts.syncStatus` | L4 | `/v1/accounts/sync-status` | GET | — | — | `AccountSyncStatusInfo` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Filters | `QK.accounts.filters` | L4 | `/v1/accounts/filters` | GET | — | — | `FilterOptions` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Create | — | L4 | `/v1/accounts` | POST | — | `CreateAccountParams` | `CreateAccountResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Sync | — | L4 | `/v1/accounts/sync` | POST | — | `SyncAccountsParams` | `SyncResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Account Refresh | — | L4 | `/v1/accounts/{id}/refresh` | POST | `id` path param | — | `Account` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration List | `QK.integrations.list` | L4 | `/v1/integrations` | GET | — | — | `IntegrationListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration Detail | `QK.integrations.detail(provider)` | L4 | `/v1/integrations/{provider}` | GET | `provider` path param | — | `Integration` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration Create/Update | — | L4 | `/v1/integrations/{provider}` | POST | `provider` path param | `IntegrationCreateRequest` | `Integration` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration Delete | — | L4 | `/v1/integrations/{provider}` | DELETE | `provider` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration Test | — | L4 | `/v1/integrations/{provider}/test` | POST | `provider` path param | — | `ConnectionTestResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Integration Sync | — | L4 | `/v1/integrations/{provider}/sync` | POST | `provider` path param | — | `SyncTriggerResult` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Governance Tenants | `QK.governance.tenants` | L4 | `/v1/tenants` | GET | — | — | `Tenant[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Governance Users | `QK.governance.users(tenantId)` | L4 | `/v1/users` | GET | — | — | `User[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Governance Invite User | — | L4 | `/v1/users/invite` | POST | — | `{ email, role, tenant_id }` | `User` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Governance API Keys | `QK.governance.apiKeys(tenantId)` | L4 | `/v1/api-keys` | GET | — | — | `ApiKey[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Governance Delete API Key | — | L4 | `/v1/api-keys/{keyId}` | DELETE | `keyId` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Platform Settings | `QK.platform.settings` | L4 | `/v1/tenant/settings` | GET | — | — | `TenantSettings` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Platform Settings Update | — | L4 | `/v1/tenant/settings` | PATCH | — | `UpdateSettingsPayload` | `TenantSettings` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Billing Subscription | — | L4 | `/v1/billing/subscription` | GET | `customer_id` query | — | `Subscription` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Billing Checkout | — | L4 | `/v1/billing/checkout` | POST | `customer_id` query | — | `CheckoutResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Billing Portal | — | L4 | `/v1/billing/portal` | POST | `customer_id` query | — | `PortalResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Billing Entitlements | — | L4 | `/v1/billing/entitlements` | GET | `customer_id` query | — | `EntitlementsResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Billing Feature Check | — | L4 | `/v1/billing/check-feature` | GET | `feature`, `customer_id` | — | `FeatureCheck` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Agent Stream Chat | — | L4 | `/v1/agent-stream/chat` | POST | — | `{ message, thread_id?, context? }` | SSE stream | `X-Tenant-ID`, Bearer JWT | `implemented` | Consumed by `useAgentEvents.ts` and `AgentEventClient.ts`. |
| C1 Stream | — | L4 | `/v1/c1/stream` | POST | — | `C1Message[]` | SSE stream (`C1StreamChunk`) | `X-Tenant-ID`, Bearer JWT | `implemented` | Thesys C1 generative UI proxy. |
| Analysis ROI | — | L4 | `/v1/analysis/roi` | POST | — | `ROIAnalysisRequest` | `ROIAnalysisResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Analysis Whitespace | — | L4 | `/v1/analysis/whitespace` | POST | — | `WhitespaceAnalysisRequest` | `WhitespaceAnalysisResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Auth Register | — | L4 | `/v1/tenants/register` | POST | — | `RegisterRequest` (Zod) | `RegisterResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/auth/register` via apiClient (L4 proxy rewrites to `/v1/auth/register`). Added backend alias `/v1/auth/register` → tenant registration for compatibility. |
| Auth OIDC Login | — | L4 | `/auth/oidc/{tenantSlug}/login` | GET | `tenantSlug` path param | — | Redirect to IdP | `X-Tenant-ID`, Bearer JWT | `implemented` | Raw `fetch` in `services/authClient.ts`. Path does NOT include `/v1` prefix. |
| Auth OIDC Callback | — | L4 | `/auth/oidc/callback` | GET | `code`, `state` query | — | Sets cookies/tokens | `X-Tenant-ID`, Bearer JWT | `implemented` | Path does NOT include `/v1` prefix. |
| Enrichment Status | `QK.enrichment.status()` | L4 | `/v1/enrichment/status` | GET | — | — | `EnrichmentStatus` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Route inferred from router; verify exact shape. |
| Enrichment Detail | `QK.enrichment.detail(accountId)` | L4 | `/v1/enrichment/{account_id}` | GET | `account_id` path param | — | `EnrichmentResult` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |
| Hypothesis Detail | `QK.hypotheses.detail(id)` | L4 | `/v1/hypotheses/{id}` | GET | `id` path param | — | `ValueHypothesis` | `X-Tenant-ID`, Bearer JWT | `implemented` | Frontend calls `/v1/hypotheses/...` correctly. |
| Hypothesis by Account | `QK.hypotheses.byAccount(id, filters)` | L4 | `/v1/hypotheses/account/{account_id}` | GET | `account_id` path, filters query | — | `ValueHypothesis[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Hypothesis Stats | `QK.hypotheses.stats()` | L4 | — | — | — | — | — | — | `missing` | No dedicated stats endpoint found in L4 backend. |
| Document Export | `QK.documents.export(id)` | L4 | `/v1/tools/export-document` | POST | — | `{ workflow_id, format }` | Blob / file | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Exact export endpoint inferred from tools router. |
| Business Case Export | `QK.documents.businessCase(id)` | L4 | `/v1/cases/{id}/export` | GET | `id` path, `format` query | — | Blob / file | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |

---

## Layer 5 — Ground Truth

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Truth List | `QK.groundTruth.list(filters)` | L5 | `/api/v1/truths` | GET | `status`, `claim_type`, `min_maturity`, `min_confidence`, `is_stale`, `limit`, `offset` | — | `TruthObjectListResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | **FIXED:** Both `.env.example` files now use `VITE_API_BASE=/api/v1`, `VITE_L5_PREFIX=/truths`. Hook paths updated to `/truths/*` (relative to baseURL). Vite proxy rewrites `/api/v1/truths/*` → `/api/v1/*`. |
| Truth Audit | `QK.groundTruth.audit(truthId)` | L5 | `/api/v1/truths/{truth_id}/audit` | GET | `truth_id` path param | — | `ValidationEventResponse[]` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Truth Freshness | `QK.groundTruth.freshnessSummary()` | L5 | `/api/v1/truths/freshness-summary` | GET | — | — | `FreshnessSummaryResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Truth Stale | `QK.groundTruth.stale(filters)` | L5 | `/api/v1/truths/stale` | GET | `limit`, `offset` | — | `TruthObjectListResponse` (subset) | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Maturity Ladder | `QK.groundTruth.maturityLadder()` | L5 | `/api/v1/maturity-ladder` | GET | — | — | `MaturityLadderResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | — |
| Truth Create | — | L5 | `/api/v1/truths` | POST | — | `TruthCreateRequest` | `TruthObjectSummary` | `X-Tenant-ID`, Bearer JWT | `implemented` | Not yet consumed by frontend hooks. |
| Truth Validate | — | L5 | `/api/v1/truths/{truth_id}/validate` | POST | `truth_id` path param | — | `ValidationEventResponse` | `X-Tenant-ID`, Bearer JWT | `implemented` | Not yet consumed by frontend hooks. |
| Truth Delete | — | L5 | `/api/v1/truths/{truth_id}` | DELETE | `truth_id` path param | — | `{ status: string }` | `X-Tenant-ID`, Bearer JWT | `implemented` | Not yet consumed by frontend hooks. |

**✅ Layer 5 Environment Fix Detail (BLOCKER-002 resolved):**
- `frontend/.env.example` and `frontend/client/.env.example` both now use `VITE_API_BASE=/api/v1`, `VITE_L5_PREFIX=/truths`.
- `frontend/client/src/api/client.ts` fallback updated to `API_BASE=/api/v1`.
- `frontend/client/src/hooks/useGroundTruthGovernance.ts` updated to call relative paths (`/truths/*`, `/maturity-ladder`) instead of repeating `/api/v1/truths`.
- `frontend/vite.config.ts` L5 proxy rewrite updated: `/api/v1/truths/*` → `/api/v1/*`.
- Result: baseURL `/api/v1/truths` + path `/truths/...` → full `/api/v1/truths/truths/...` → proxy → `/api/v1/truths/...` → matches L5 backend.

---

## Layer 6 — Benchmarks / Platform

| Frontend Module | Query Key | Backend Owner | Canonical Endpoint | HTTP Method | Request Params | Request Body Schema | Response Schema | Auth / Tenant | Current Status | Notes / Migration Needs |
|-----------------|-----------|---------------|--------------------|-------------|----------------|---------------------|-----------------|---------------|----------------|------------------------|
| Benchmark Datasets | — | L6 | `/v1/benchmarks/datasets` | GET | — | — | `Dataset[]` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | Frontend query key exists (`QK.benchmarks`) but no hook actively consumes L6. |
| Benchmark Compare | — | L6 | `/v1/benchmarks/compare` | POST | — | `{ dataset_ids, metrics }` | `ComparisonResult` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |
| Benchmark Industries | — | L6 | `/v1/benchmarks/industries` | GET | — | — | `Industry[]` | `X-Tenant-ID`, Bearer JWT | `partially-implemented` | — |
| Platform Health | `QK.platform.health` | L6 / L1-L5 | `/health` (per layer) | GET | — | — | `{ status: string }` | Public (no auth) | `partially-implemented` | Frontend defines query key but no active hook found. Each layer exposes its own `/health`. |
| Platform Settings | `QK.platform.settings` | L4 | `/v1/tenant/settings` | GET | — | — | `TenantSettings` | `X-Tenant-ID`, Bearer JWT | `implemented` | Listed under L4 above; repeated here for completeness. |

---

## Cross-Cutting Concerns

### Auth & Tenant Header Contract

| Header | Source | Required | Fallback | Notes |
|--------|--------|----------|----------|-------|
| `Authorization: Bearer <jwt>` | `localStorage.getItem('accessToken')` | Yes (except public paths) | 401 redirect to `/login` | Cleared on 401. OIDC flow sets token. |
| `X-Tenant-ID` | `localStorage.getItem('tenantId')` | Yes | `'default'` | Regex-validated in C1 stream: `/^[a-zA-Z0-9_-]+$/`. |
| `X-Request-ID` | Generated per request | No (client-generated) | `req_{random}` | Used for trace correlation. |

### Error Envelope Contract

Frontend expects this shape on 4xx/5xx (parsed by `ErrorResponseSchema` in `client.ts`):

```json
{
  "message": "string",
  "code": "string",
  "trace_id": "string"
}
```

Backend layers do **not** consistently return this shape. Some return FastAPI default `{"detail": "..."}`. Gateway/BFF should normalize errors to the frontend envelope.

### Response Pagination Contract

Frontend normalizes multiple pagination shapes in `useWorkflows.ts` and `useGroundTruthGovernance.ts`:

```typescript
// Preferred shape (new)
{ items: T[], total: number, limit: number, offset: number, has_more: boolean }

// Legacy shapes supported by frontend
T[]                                    // raw array
{ workflows: T[] }                     // nested workflows
{ items: T[], total, limit, offset }   // without has_more
```

Backend layers use inconsistent pagination. L4 `/workflows/active` now returns the preferred shape. L5 truths return `TruthObjectListResponse` which may differ.

---

## Summary of Critical Gaps

| # | Gap | Severity | Owner | Recommendation |
|---|-----|----------|-------|----------------|
| 1 | **L2 `/jobs/{id}` ≠ `/extract/status/{id}`** | 🔴 High | Backend / Gateway | Add alias or update frontend path. |
| 2 | **L5 env double-prefix risk** | 🟡 Medium | DevOps / Frontend | Standardize `VITE_API_BASE` + `VITE_L5_PREFIX` across env files. |
| 3 | **Error envelope inconsistency** | 🟡 Medium | Gateway / Backend | Normalize all errors to `{ message, code, trace_id }`. |
| 4 | **Pagination shape divergence** | 🟡 Medium | Backend | Standardize on `{ items, total, limit, offset, has_more }`. |
| 5 | **Business Case `?type=` filter not in OpenAPI** | 🟡 Medium | Backend | Update OpenAPI spec for `/v1/workflows` query params. |
| 6 | **Hypothesis stats endpoint missing** | 🟡 Medium | Backend | Implement `/v1/value-hypotheses/stats` or mark stub. |
| 7 | **Evidence / Competitive Intel / ROI routes partially stubbed** | 🟢 Low | Frontend | Add backend integration tests and typed hooks. |
| 8 | **Extraction results endpoint missing** | 🟢 Low | Backend | Add `GET /v1/extract/results/{job_id}` or document why not needed. |
