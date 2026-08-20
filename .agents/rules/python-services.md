# Python Backend Services Rule

All backend services (Layer 1 through Layer 6) adhere to strict service boundaries.

## Architecture
- **Layer 1 (Ingestion, Port 8001)**: Playwright crawling, Celery jobs, Redis queues, PostgreSQL state.
- **Layer 2 (Extraction, Port 8002)**: Pydantic v2 extraction, RDF/OWL provenance, structured entities.
- **Layer 3 (Knowledge, Port 8003)**: Neo4j, GraphRAG, hybrid retrieval, pgvector.
- **Layer 4 (Agents, Port 8004)**: LangGraph workflows, ROI engine, agent orchestration.
- **Layer 5 (Ground Truth, Port 8005)**: TruthObject validation, maturity ladder.
- **Layer 6 (Benchmarks, Port 8006)**: Peer comparison, statistical validation.

## Standards
- FastAPI routes must declare explicit Pydantic v2 `response_model` and typed parameters.
- Shared logic lives under `packages/shared/src/value_fabric/shared/`.
- Never bypass service boundaries or access another layer's internal database directly.
