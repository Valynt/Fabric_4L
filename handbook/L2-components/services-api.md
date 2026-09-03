# L2 Component — services-api

## Purpose

FastAPI gateway / BFF (`services/api/`). The only public ingress to backend services. Enforces
backend-authoritative authorization snapshots, tenant/account scope, and request context before
delegating to layers. 24 verified routers. Fail-closed on any scope uncertainty (R-6).

## Owned journey stages / behaviors

- J-1 / BEH-01 — `app/routers/accounts.py`, `auth.py`, `clerk_auth.py`, `clerk_webhooks.py`
- J-2–J-4 / BEH-02 — `app/routers/intelligence.py`, `hypotheses.py`, `context_engine.py`
- J-5 / BEH-03 — `app/routers/drivers.py`
- J-6–J-7 / BEH-04 — `app/routers/calculator.py`
- J-6 / BEH-05 — `app/routers/evidence.py`, `benchmarks.py`
- J-8 / BEH-06 — `app/routers/value_cases.py`
- J-9 / BEH-08 — `app/routers/reviews.py`, `versioning.py`, `governance.py`
- J-10 / BEH-09 — `app/routers/realization.py`
- Cross-cutting / agent ops — `app/routers/agents.py`, `jobs.py`, `layer_delegation.py`,
  `layer_proxy.py`, `api_keys.py`, `privacy.py`, `usage.py`, `product_endpoints.py`

## Key verified paths

- `services/api/app/main.py` — application entry
- `services/api/app/routers/` — all HTTP routers listed above
- `services/api/app/{clients,core,models,repositories,services,tests}/` — support layers
- `services/api/app/shared_bootstrap.py`, `app/logging_config.py`
- `services/api/migrations/`
- `services/api/src/gdpr/` — secondary GDPR package
- Root: `README.md`, `AGENTS.md`, `Dockerfile`, `pyproject.toml`

## Dependencies

- Delegates to `services/layer1-ingestion` … `layer7-billing` via internal clients; ingress to
  layers flows through this gateway (gateway-only ingress policy).
- Contracts published in `contracts/openapi/fabric-4l-api.json` (runtime OpenAPI is authoritative).
- Frontend consumer: `apps/web` via the frontend contracts in `contracts/frontend/`.

## Primary gates

- **AG-05** tenant-isolation-and-behavior — authorization-snapshot validation, account-scope
  enforcement, hostile same-ID/cross-ID tests.
- **AG-04** security-gates — route authentication/authorization checks, undocumented-route rejection.
- **AG-03** contract-compliance — runtime OpenAPI generation and client drift checks.
