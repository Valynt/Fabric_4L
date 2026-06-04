# Value Fabric — Providers

This document catalogs every external service, API, database, and infrastructure provider used across the Value Fabric platform. Each entry includes its role, the layer(s) that consume it, and any relevant configuration notes.

---

## LLM / AI Providers

### OpenAI

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Entity extraction, relationship extraction, confidence scoring |
| **Models** | `gpt-4o` (primary), `gpt-4o-mini` (cost-optimized) |
| **Embedding model** | `text-embedding-3-large` (1,536 dimensions) |
| **API style** | Function calling with strict schema; temperature 0.0 |
| **Rate limit** | 1,000 LLM calls/min |
| **Config env vars** | `OPENAI_API_KEY`, `L2_OPENAI_MODEL`, `L2_LLM_PROVIDER` |

**Pricing (per 1M tokens):**

| Model | Input | Output |
|-------|-------|--------|
| GPT-4o | $2.50 | $10.00 |
| GPT-4o-mini | $0.15 | $0.60 |

### Anthropic

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Alternative LLM provider for entity and relationship extraction |
| **Models** | `claude-3-5-sonnet` (primary), `claude-3-5-haiku` (cost-optimized) |
| **Config env vars** | `ANTHROPIC_API_KEY`, `L2_ANTHROPIC_MODEL`, `L2_LLM_PROVIDER` |

**Pricing (per 1M tokens):**

| Model | Input | Output |
|-------|-------|--------|
| Claude 3.5 Sonnet | $3.00 | $15.00 |
| Claude 3.5 Haiku | $0.80 | $4.00 |

> **Provider switching:** Set `L2_LLM_PROVIDER=openai` or `L2_LLM_PROVIDER=anthropic`. The shared `LLMClient` in `layer2-extraction/src/shared/llm_client.py` handles both providers with automatic retry and exponential backoff.

---

## Vector / Embedding Providers

### Neo4j Native Vector Indexes

| Property | Value |
|----------|-------|
| **Used by** | Layer 3 (Knowledge Graph) |
| **Purpose** | Native Neo4j `VECTOR` indexes for semantic entity search and retrieval |
| **Vector dimensions** | Configured by `EMBEDDING_DIMENSION` |
| **Status** | Active |

### pgvector (PostgreSQL Extension)

| Property | Value |
|----------|-------|
| **Used by** | Not used by current Layer 3 retrieval paths |
| **Purpose** | Reserved future PostgreSQL vector backend option |
| **Vector dimensions** | Not provisioned |
| **Status** | Inactive |

### sentence-transformers

| Property | Value |
|----------|-------|
| **Used by** | Layer 3 (Knowledge Graph) |
| **Purpose** | Local embedding generation for entity indexing |
| **Default model** | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| **Config env vars** | `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE` |
| **Status** | Active |

---

## Graph Database

### Neo4j

| Property | Value |
|----------|-------|
| **Used by** | Layer 3 (Knowledge Graph) |
| **Purpose** | Primary knowledge graph storage; GraphRAG traversal; community detection |
| **Version** | 5.x (Enterprise recommended; Community compatible) |
| **Driver** | `neo4j>=5.15` async Python driver |
| **Graph Data Science** | Leiden community detection (`GDS`) |
| **Config env vars** | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `NEO4J_MAX_POOL_SIZE` |
| **Default values** | `bolt://localhost:7687`, `neo4j`, `password`, `valuefabric`, `50` |

**Indexes:**

| Type | Purpose |
|------|---------|
| Vector index | Entity embeddings (cosine similarity) |
| Full-text index | Keyword search across entity properties |
| B-tree index | Filtering by type, confidence, date |
| Unique constraints | Entity deduplication |

---

## Relational Database

### PostgreSQL

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion), Layer 4 (Agents — checkpoint/resume) |
| **Purpose** | Crawl job state, audit logs, agent workflow checkpoints, semantic layer metadata |
| **Extensions** | None required for current Layer 3 vector search |
| **ORM** | SQLAlchemy (async) |

---

## Message Queue / Task Queue

### Redis

| Property | Value |
|----------|-------|
| **Used by** | Layers 1, 2, 4 |
| **Purpose** | Celery task broker; embedding cache (TTL: 7 days); LLM call queuing |
| **Celery workers** | Async workers for extraction pipeline stages |
| **Rate limiting** | Used to enforce per-domain crawl rates in Layer 1 |

### Celery

| Property | Value |
|----------|-------|
| **Used by** | Layers 1, 2 |
| **Purpose** | Distributed task queue for crawling and extraction pipeline stages |
| **Broker** | Redis |

---

## Object Storage

### MinIO / AWS S3

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | Raw document storage, Markdown output storage, audit artifacts |
| **Local dev** | MinIO (S3-compatible) via Docker Compose |
| **Production** | AWS S3 (Terraform-provisioned) |

---

## Web Scraping

### Playwright (async)

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | Headless browser-based web crawling for JavaScript-rendered pages |
| **Compliance** | robots.txt enforced; Crawl-delay respected; PII detection before storage |

---

## PII Detection

### Microsoft Presidio

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | Detect and redact PII (SSN, credit cards, phone numbers, email addresses) |
| **Threshold** | Block pages with > 3 PII entities |
| **Accuracy target** | > 95% |

---

## External Data Sources

### SEC EDGAR

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | Public company filings: 10-K, 10-Q, earnings call transcripts |
| **Access** | Free public API (`https://efts.sec.gov`, `https://data.sec.gov`) |

### NewsAPI

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | News mentions for tracked companies |
| **Priority** | Level 3 (lower priority data source) |

### LinkedIn

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion) |
| **Purpose** | Company page content for persona and capability enrichment |
| **Priority** | Level 3 (lower priority data source) |

---

## Industry Standards & Ontologies

### APQC Process Classification Framework (PCF) v7.4

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Map extracted Capabilities to standard process codes |
| **Method** | Embedding-based similarity search (threshold: 0.8) |

### BIAN Service Landscape v11.0

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Optional mapping for financial services capabilities |

### FIBO Ontology

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Optional ontology for financial industry entities |

### PROV-O (W3C Provenance Ontology)

| Property | Value |
|----------|-------|
| **Used by** | Layers 2, 4 |
| **Purpose** | Provenance metadata on all RDF triples and agent actions |
| **Library** | `rdflib>=7.1.0` |

### OWL / RDF (Turtle format)

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | Serialization format for extracted knowledge |
| **Validation** | Apache Jena |

---

## AI Orchestration

### LangGraph

| Property | Value |
|----------|-------|
| **Used by** | Layer 4 (Agents) |
| **Purpose** | State machine orchestration for multi-step AI workflows |
| **Features** | Checkpointing, human-in-the-loop gates, workflow persistence |
| **Status** | Planned |

### LangChain

| Property | Value |
|----------|-------|
| **Used by** | Layer 2 (Extraction) |
| **Purpose** | `RecursiveCharacterTextSplitter` for semantic document chunking |
| **Chunk size** | 2,000 tokens with 200-token overlap |

---

## Document Generation

### python-docx / python-pptx

| Property | Value |
|----------|-------|
| **Used by** | Layer 4 (Agents) |
| **Purpose** | Generate DOCX and PPTX business case documents |

### WeasyPrint

| Property | Value |
|----------|-------|
| **Used by** | Layer 4 (Agents) |
| **Purpose** | HTML-to-PDF conversion for business case documents |

### Jinja2

| Property | Value |
|----------|-------|
| **Used by** | Layer 4 (Agents) |
| **Purpose** | Document generation templates |

---

## API Framework

### FastAPI

| Property | Value |
|----------|-------|
| **Used by** | Layers 2, 3, 4 |
| **Purpose** | RESTful API server for each layer |
| **Standards** | `/v1/` prefix, OpenAPI spec auto-generated at `/docs` |

---

## Observability

### Prometheus

| Property | Value |
|----------|-------|
| **Used by** | All layers |
| **Purpose** | Metrics collection: query latency, cache hit rates, API uptime, worker throughput |

### OpenTelemetry

| Property | Value |
|----------|-------|
| **Used by** | All layers |
| **Purpose** | Distributed tracing across layer boundaries |

### Structured JSON Logging

| Property | Value |
|----------|-------|
| **Used by** | All layers |
| **Purpose** | Machine-parseable logs for log aggregation and alerting |

---

## Formula Evaluation

### numexpr

| Property | Value |
|----------|-------|
| **Used by** | Layer 4 (Agents) |
| **Purpose** | Safe evaluation of ROI formula strings (e.g., `({hours_saved} * {hourly_rate}) - {impl_cost}`) |
| **Security** | Sandboxed evaluation — no arbitrary code execution |

---

## Infrastructure & Deployment

### Docker / Docker Compose

| Property | Value |
|----------|-------|
| **Used by** | All layers (local development and CI) |
| **Purpose** | Container orchestration for local development and testing |
| **Files** | `docker-compose.full.yml`, `docker-compose.full.yml`, per-layer `docker-compose.yml` |

### Kubernetes

| Property | Value |
|----------|-------|
| **Used by** | All layers (production) |
| **Purpose** | Production container orchestration |
| **Manifests** | `infrastructure/` directory |

### Terraform (AWS)

| Property | Value |
|----------|-------|
| **Used by** | Layer 1 (Ingestion), Infrastructure |
| **Purpose** | Cloud infrastructure provisioning (AWS) |
| **Resources** | S3 buckets, ECS/EKS clusters, RDS PostgreSQL, ElastiCache Redis |

---

## CI/CD

### GitHub Actions

| Property | Value |
|----------|-------|
| **Purpose** | Continuous integration, smoke gate validation, scheduled tests |
| **Workflows** | `smoke-gate.yml` — 6-stage cross-layer integration test runs on every PR to `main` and daily at 02:00 UTC |

### Smoke Gate Script

| Property | Value |
|----------|-------|
| **File** | `scripts/smoke/production_smoke.py` |
| **Stages** | L2 health, L3 health + Neo4j, L4 health + Postgres, L2→L3 extract-ingest, L3 graph query, L3 hybrid search |
| **Artifacts** | JSON pass/fail report in `artifacts/smoke-report-*.json` |

---

## Provider Configuration Summary

| Provider | Layer(s) | Environment Variable(s) |
|----------|----------|------------------------|
| OpenAI | L2 | `OPENAI_API_KEY`, `L2_OPENAI_MODEL`, `L2_LLM_PROVIDER` |
| Anthropic | L2 | `ANTHROPIC_API_KEY`, `L2_ANTHROPIC_MODEL`, `L2_LLM_PROVIDER` |
| Neo4j | L3 | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `NEO4J_MAX_POOL_SIZE` |
| Legacy vector provider config | L3 compatibility only | `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT` |
| sentence-transformers | L3 | `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE` |
| Redis | L1, L2, L4 | `REDIS_URL` |
| PostgreSQL | L1, L4 | `DATABASE_URL` |
| MinIO / S3 | L1 | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` |
| Layer 3 API | L2 | `LAYER3_API_URL`, `LAYER3_API_KEY` |
| NewsAPI | L1 | `NEWSAPI_KEY` |

> **Security:** All credentials must be provided via environment variables. No secrets may be hardcoded in source code.

---

*Document Version: 1.0*
*Last Updated: April 2026*
