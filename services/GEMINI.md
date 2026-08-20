# Backend Services Rules (services/)

This directory houses the six microservice layers of Value Fabric.

## Requirements
- Respect layer boundaries: L1 Ingestion, L2 Extraction, L3 Knowledge Graph, L4 Agents, L5 Ground Truth, L6 Benchmarks.
- Maintain multi-tenant isolation via authenticated context and PostgreSQL RLS.
- Use Pydantic v2 models and typed FastAPI route handlers.
- Never write cross-service database queries directly; use service API contracts.
- Run validation before and after changes:
  ```bash
  make lint
  make typecheck
  make test
  ```
