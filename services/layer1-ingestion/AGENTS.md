# AGENTS — services/layer1-ingestion (L1, port 8001)

Scoped instructions; universal rules live in the root `AGENTS.md`.

## Responsibility

Playwright crawling, Celery jobs, Redis queues, PostgreSQL state,
compliance-aware ingestion. Do not move logic across layers.

## Canonical runtime path

`services/layer1-ingestion/src/layer1_ingestion/` — all net-new logic lands
here (see `docs/reference/layer-runtime-path-governance.md`). API routes:
`services/layer1-ingestion/src/layer1_ingestion/api/routes/`.

## Layer rules

- Preserve job lifecycle semantics; do not bypass queue/state management.
- Keep crawling, extraction preparation, compliance, and source tracking separate.
- Ingestion jobs are tenant-scoped; queue payload tenant IDs never override
  authenticated tenant context; missing tenant context fails closed.
- Preserve provenance metadata for downstream layers.

## Validation

```bash
make test-layer1
make lint-layer1
make typecheck-layer1
pytest tests/tenancy/test_worker_tenant_scope.py
```
