<!-- Migrated from docs/data-intelligence-layer.md during legacy path cleanup. -->

> **Audit note (2026-07-18):** The API endpoint inventory below is stale. Examples: product portfolio paths have moved to `/api/v1/products/matching/signals` and `/api/v1/products/analytics/*`, competitive-intel paths are under `/api/v1/competitive/*`, evidence library paths are under `/api/v1/evidence/*`, and value-hypothesis routes use the `/v1/hypotheses` prefix. Cross-check against the current Layer 3/4 route files before relying on this document.

# Data Intelligence Layer (DIL) — Architecture & API Reference

The Data Intelligence Layer extends the Value Fabric with structured intelligence services that transform raw signals and account data into actionable sales intelligence. It spans Layer 3 (Knowledge Graph) and Layer 4 (Agent Services), providing a unified pipeline from data ingestion through narrative delivery.

## Architecture Overview

The DIL is organized into three functional phases, each building on the previous one to create a complete intelligence pipeline.

| Phase | Name | Services | Layer |
|-------|------|----------|-------|
| Phase 1 | Data Foundation | Product Portfolio, Account Enrichment, Evidence Library | L3 + L4 |
| Phase 2 | Intelligence Processing | Value Hypothesis Engine, Competitive Intel, ROI Calculator | L3 + L4 |
| Phase 3 | Delivery & Orchestration | Narrative Builder, Intelligence Orchestrator | L4 |

## Data Flow

The intelligence pipeline follows a directed flow from raw data to delivered narratives:

```
Account Enrichment (L4)
        │
        ▼
Signal Detection ──► Product Portfolio (L3) ──► Value Hypotheses (L4)
                            │                          │
                            ▼                          ▼
                    Competitive Intel (L3)    ROI Calculator (L3)
                            │                          │
                            └──────────┬───────────────┘
                                       ▼
                              Evidence Library (L3)
                                       │
                                       ▼
                             Narrative Builder (L4)
                                       │
                                       ▼
                        Intelligence Orchestrator (L4)
                                       │
                                       ▼
                           Account Briefing / Deal Readiness
```

## Phase 1 — Data Foundation

### 1.1 Product Portfolio Graph (L3)

**Service:** `product_service.py` | **Routes:** `/api/v1/products`

The Product Portfolio Graph manages the product catalog as a Neo4j graph, enabling capability-based matching between products and detected pain signals. Each Product node connects to Feature nodes and Capability nodes, forming the bridge between what the product does and what problems it solves.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/products` | POST | Create a product |
| `/api/v1/products` | GET | List products with pagination |
| `/api/v1/products/{id}` | GET | Get product details |
| `/api/v1/products/{id}` | PUT | Update a product |
| `/api/v1/products/{id}` | DELETE | Delete a product |
| `/api/v1/products/{id}/features` | POST | Add a feature |
| `/api/v1/products/{id}/features/{fid}` | DELETE | Remove a feature |
| `/api/v1/products/{id}/capabilities` | POST | Link a capability |
| `/api/v1/products/{id}/capabilities/{cid}` | DELETE | Unlink a capability |
| `/api/v1/products/match-signals` | POST | Match signals to products via capabilities |
| `/api/v1/products/portfolio-summary` | GET | Portfolio analytics |
| `/api/v1/products/capability-coverage` | GET | Capability gap analysis |

### 1.2 Account Enrichment Pipeline (L4)

**Service:** `enrichment_orchestrator.py` | **Routes:** `/api/v1/enrichment`

The Account Enrichment Pipeline automatically enriches account records from multiple external sources. It uses a staleness-based approach to determine when re-enrichment is needed and supports both single-account and batch operations.

**Enrichment Sources:**
- **SEC EDGAR** — Financial data, revenue, employee count for public companies
- **Web Crawl** — Technology stack detection from company websites
- **Domain Lookup** — Executive contacts and company metadata
- **News Scan** — Recent news and press releases

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/enrichment/enrich` | POST | Enrich a single account |
| `/api/v1/enrichment/batch` | POST | Batch enrich multiple accounts |
| `/api/v1/enrichment/status` | GET | Get enrichment status for tenant |

### 1.3 Evidence Library (L3)

**Service:** `case_study_service.py` | **Routes:** `/api/v1/evidence`

The Evidence Library stores case studies, success stories, and quantified outcomes as Evidence nodes in the knowledge graph. These are used by the Narrative Builder and ROI Calculator to support value claims with real-world proof points.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/evidence` | POST | Create evidence |
| `/api/v1/evidence` | GET | List evidence |
| `/api/v1/evidence/{id}` | GET | Get evidence details |
| `/api/v1/evidence/{id}` | PUT | Update evidence |
| `/api/v1/evidence/{id}` | DELETE | Delete evidence |
| `/api/v1/evidence/search` | GET | Full-text search |
| `/api/v1/evidence/by-industry` | GET | Group by industry |
| `/api/v1/evidence/by-product` | GET | Group by product |
| `/api/v1/evidence/bulk-import` | POST | Bulk import |

## Phase 2 — Intelligence Processing

### 2.1 Value Hypothesis Engine (L4)

**Service:** `value_hypothesis_engine.py` | **Routes:** `/api/v1/value-hypotheses`

The Value Hypothesis Engine generates and manages value hypotheses by traversing `Signal → Capability → Product` paths in the knowledge graph. Each hypothesis represents a quantified value proposition linking a detected pain signal to a product capability.

**Ranking Strategies:**

| Strategy | Description |
|----------|-------------|
| `impact` | Rank by estimated financial impact |
| `confidence` | Rank by confidence score |
| `balanced` | Weighted composite of all factors |
| `evidence` | Rank by number of supporting evidence items |
| `recency` | Rank by creation date (newest first) |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/value-hypotheses/generate` | POST | Generate hypotheses for an account |
| `/api/v1/value-hypotheses/{id}` | GET | Get a hypothesis |
| `/api/v1/value-hypotheses/account/{id}` | GET | List account hypotheses |
| `/api/v1/value-hypotheses/{id}/validate` | POST | Validate a hypothesis |
| `/api/v1/value-hypotheses/{id}` | DELETE | Delete a hypothesis |
| `/api/v1/value-hypotheses/account/{id}/summary` | GET | Hypothesis summary |

### 2.2 Competitive Intelligence Analyzer (L3)

**Service:** `competitive_intel_service.py` | **Routes:** `/api/v1/competitive-intel`

The Competitive Intelligence Analyzer manages competitor profiles, battlecards, and win/loss records in the knowledge graph. It provides landscape analysis with win rates, overlap scores, and threat-level assessments.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/competitive-intel/competitors` | POST | Add a competitor |
| `/api/v1/competitive-intel/competitors` | GET | List competitors |
| `/api/v1/competitive-intel/competitors/{id}` | GET | Get competitor |
| `/api/v1/competitive-intel/competitors/{id}` | PUT | Update competitor |
| `/api/v1/competitive-intel/competitors/{id}` | DELETE | Delete competitor |
| `/api/v1/competitive-intel/battlecards` | POST | Create battlecard |
| `/api/v1/competitive-intel/battlecards/{cid}/{pid}` | GET | Get battlecard |
| `/api/v1/competitive-intel/win-loss` | POST | Record win/loss |
| `/api/v1/competitive-intel/landscape` | GET | Analyze landscape |
| `/api/v1/competitive-intel/win-loss-summary` | GET | Win/loss summary |

### 2.3 ROI Calculator Service (L3)

**Service:** `roi_calculator_service.py` | **Routes:** `/api/v1/roi`

The ROI Calculator provides a pure financial math engine for computing NPV, IRR, payback period, and multi-year projections. It supports three standard scenarios and custom configurations, with template management for reusable calculation setups.

**Standard Scenarios:**

| Scenario | Revenue Multiplier | Cost Multiplier | Adoption Rate |
|----------|-------------------|-----------------|---------------|
| Conservative | 0.7 | 1.2 | 0.6 |
| Moderate | 1.0 | 1.0 | 0.8 |
| Aggressive | 1.3 | 0.85 | 0.95 |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/roi/calculate` | POST | Calculate ROI |
| `/api/v1/roi/compare` | POST | Compare scenarios |
| `/api/v1/roi/templates` | POST | Create template |
| `/api/v1/roi/templates` | GET | List templates |
| `/api/v1/roi/calculations` | POST | Save calculation |
| `/api/v1/roi/calculations/{id}` | GET | Get calculation |
| `/api/v1/roi/calculations` | GET | List calculations |
| `/api/v1/roi/benchmarks/{industry}` | GET | Industry benchmarks |

## Phase 3 — Delivery & Orchestration

### 3.1 Narrative Builder Service (L4)

**Service:** `narrative_builder_service.py` | **Routes:** `/api/v1/narratives`

The Narrative Builder generates structured sales narratives from assembled intelligence data. It uses template-based generation with customizable tone and audience presets, producing seven standard sections that can be included or excluded per request.

**Tone Presets:** Executive, Technical, Financial, Consultative

**Audience Presets:** C-Suite, VP/Director, Technical Buyer, Champion, Evaluation Committee

**Narrative Sections:**

| Section | Content Source |
|---------|---------------|
| Executive Summary | Account context + top hypotheses |
| Pain Points | Signal graph data |
| Value Hypotheses | Hypothesis engine (ranked) |
| Competitive Positioning | Battlecards + win/loss data |
| ROI Projection | Scenario comparison |
| Evidence | Industry-matched case studies |
| Next Steps | Custom or default recommendations |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/narratives/generate` | POST | Generate a narrative |
| `/api/v1/narratives` | GET | List narratives |
| `/api/v1/narratives/{id}` | GET | Get a narrative |
| `/api/v1/narratives/{id}/status` | PATCH | Update status |
| `/api/v1/narratives/{id}` | DELETE | Delete a narrative |

### 3.2 Intelligence Orchestrator (L4)

**Service:** `intelligence_orchestrator.py` | **Routes:** `/api/v1/intelligence`

The Intelligence Orchestrator provides cross-layer endpoints that assemble intelligence from all DIL services into unified deliverables. It computes a weighted deal readiness score and provides pipeline-level analytics.

**Deal Readiness Components:**

| Component | Weight | Description |
|-----------|--------|-------------|
| Enrichment Complete | 15% | Account data enriched |
| Signals Identified | 15% | Pain signals detected |
| Hypotheses Generated | 20% | Value hypotheses created |
| Hypotheses Validated | 10% | Hypotheses confirmed with prospect |
| Competitive Intel | 10% | Competitor data available |
| ROI Calculated | 15% | Financial model completed |
| Evidence Matched | 10% | Case studies identified |
| Narrative Generated | 5% | Sales narrative created |

**Readiness Labels:**

| Score Range | Label |
|-------------|-------|
| 0.00 – 0.19 | Not Ready |
| 0.20 – 0.39 | Early Stage |
| 0.40 – 0.59 | Developing |
| 0.60 – 0.79 | Prepared |
| 0.80 – 1.00 | Deal Ready |

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/intelligence/account/{id}/briefing` | GET | Full account briefing |
| `/api/v1/intelligence/account/{id}/deal-readiness` | GET | Deal readiness score |
| `/api/v1/intelligence/pipeline-summary` | GET | Pipeline intelligence |

## Multi-Tenancy

All DIL services enforce tenant isolation. Every Neo4j node includes a `tenant_id` property, and all queries filter by tenant. The tenant context is extracted from the request state (set by authentication middleware) or from the `X-Tenant-ID` header as a fallback.

## Testing

The DIL includes comprehensive unit and integration tests organized by phase:

| Test File | Layer | Phase | Tests |
|-----------|-------|-------|-------|
| `test_dil_phase1.py` | L3 | 1 | Product service, case study service, data models |
| `test_enrichment.py` | L4 | 1 | Enrichment orchestrator, source handlers, route models |
| `test_dil_phase2.py` | L3 | 2 | Competitive intel, ROI calculator, financial math |
| `test_value_hypothesis.py` | L4 | 2 | Hypothesis engine, ranking, CRUD |
| `test_dil_phase3.py` | L4 | 3 | Narrative builder, intelligence orchestrator, cross-service integration |

All tests use mock Neo4j drivers and do not require external services. Run with:

```bash
# L3 tests
cd services/layer3-knowledge
python3 -m pytest tests/test_dil_phase1.py tests/test_dil_phase2.py --noconftest -v

# L4 tests
cd services/layer4-agents
python3 -m pytest tests/test_enrichment.py tests/test_value_hypothesis.py tests/test_dil_phase3.py --noconftest -v
```
