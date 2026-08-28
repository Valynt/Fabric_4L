# Layer 4: Agentic Workflow Engine
> Routing/versioning reference: see the canonical [Service Routing and API Version Matrix](../../docs/reference/service-routing-and-api-version-matrix.md).

> Runtime path governance: net-new Layer 4 logic must go to the canonical `services/layer4-agents/src/layer4_agents/` package. See [`docs/reference/layer-runtime-path-governance.md`](../../docs/reference/layer-runtime-path-governance.md).

LangGraph-powered agentic workflow layer for the Value Fabric platform.

## Overview

Layer 4 transforms structured knowledge into actionable business intelligence through AI agent workflows:

- **LangGraph Workflow Engine**: State-machine orchestrated agent graphs
- **ROI Calculator**: Formula-based value quantification
- **Whitespace Analysis**: Gap detection between needs and capabilities  
- **Business Case Generator**: Automated ROI-driven document generation
- **Tool Registry**: 24+ reusable skills for agents

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export OPENAI_API_KEY=sk-...
export NEO4J_URI=bolt://localhost:7687
export REDIS_URL=redis://localhost:6379
export LAYER1_API_URL=https://layer1-ingestion.value-fabric.svc.cluster.local:8000
export LAYER2_API_URL=https://layer2-extraction.value-fabric.svc.cluster.local:8000
export LAYER3_API_URL=https://layer3-knowledge.value-fabric.svc.cluster.local:8001
export LAYER5_API_URL=https://layer5-ground-truth.value-fabric.svc.cluster.local:8005
export LAYER4_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/layer4_agents

# Optional: enable only when HTTPS is terminated by an enforced service mesh mTLS path
export SERVICE_MESH_MTLS_ENABLED=true

# Run database migrations
alembic upgrade head

# Run tests
pytest tests/ -v

# Start API server
uvicorn layer4_agents.api.main:app --reload
```


## Canonical namespace and compatibility timeline

- Runtime/deployment entrypoint remains `uvicorn layer4_agents.api.main:app` (from `services/layer4-agents/src/layer4_agents/api/main.py`).
- Canonical Python import namespace for Layer 4 is `layer4_agents.*`.
- `services/layer4-agents/src/{api,agents,engine,workflows,services,...}` top-level packages are deprecated compatibility shims only.
- New code must import `layer4_agents.*`; CI rejects duplicate top-level implementation files via `scripts/ci/check_duplicate_source_trees.py`.

## Package placement rule (`integration` vs `interfaces`/`adapters`/`services`)

Layer 4 splits cross-cutting code by its role. The rule:

| Destination | What lives here | Example |
|---|---|---|
| `layer4_agents/integration/` | Cross-layer client adapters that talk to other services (L1/L2/L3/L5), plus the `connectors/` subpackage for external CRM provider connectors | `integration/layer1_client.py` |
| `layer4_agents/integration/connectors/` | External-system connector implementations — provider-specific CRM connectors (`providers/hubspot`, `providers/salesforce`) and their shared `core/` primitives (protocols, errors, observations, state reducer, types) | `integration/connectors/factory.py` |
| `layer4_agents/interfaces/` | Abstract/protocol interfaces that define contracts without implementation | `interfaces/*.py` |
| `layer4_agents/adapters/` | Adapters that translate provider/system outputs into canonical Layer 4 shapes | `adapters/*.py` |
| `layer4_agents/services/` | Long-lived application services (scheduling, sync orchestration, crypto) | `services/*.py` |

Guidance:

- **Cross-layer clients** that call L1/L2/L3/L5 live under `integration/` (previously some jointly moved to `integration/` from the legacy `integrations/` facade).
- **Pure public-interface definitions** with no external coupling belong in `interfaces/`.
- **Provider configuration, mapping, and translation logic** belongs in `adapters/`.
- **Orchestration/service logic** (jobs, schedulers, sync services) belongs in `services/`.
- The legacy `layer4_agents/integrations/` package and its re-export shims have been **removed**. All connector code lives under `integration/connectors/`; there is no compatibility alias. Layer 4 is pre-production with no external consumers of the old path, so no compatibility shims are preserved — imports must use `integration/connectors/`.

## Architecture

```
src/layer4_agents/
├── models/          # Agent state, workflow configs, tool schemas
├── workflows/       # LangGraph workflow definitions
├── tools/           # 24 skill implementations
├── engine/          # Core workflow execution engine
└── api/             # FastAPI REST endpoints
```

## Agent Runtime

Layer 4 uses LangGraph as the workflow runtime. The dependency is declared in
`services/layer4-agents/pyproject.toml` through `langgraph` and
`langgraph-checkpoint-postgres`; runtime code uses the canonical
`services/layer4-agents/src/layer4_agents/` package.

Startup flows through `layer4_agents.api.startup.build_lifespan()`, which
creates `CheckpointConfig.create_saver()`, `StateManager`, and
`OrchestrationController`. Workflow execution enters
`OrchestrationController.execute_workflow()`, resolves workflow classes through
`create_workflow()`, then executes `BaseWorkflow.run(...)`.

`BaseWorkflow._build_graph()` builds a LangGraph `StateGraph`,
`BaseWorkflow.compile()` injects checkpoint and interrupt configuration, and
`BaseWorkflow.run()` executes the compiled graph with `compiled.ainvoke(...)`.
`CHECKPOINT_DATABASE_URL` backs the production `AsyncPostgresSaver`; tests use
LangGraph `InMemorySaver` for real graph execution without Postgres.

Observability is carried by `Layer4LifecycleLogger`, `Layer4EventContext`,
workflow Prometheus metrics, stuck-workflow detection, and checkpoint
corruption/replay metrics using `workflow_id`, `run_id`, `trace_id`, and
`tenant_id`. See
[`docs/architecture/agent-runtime.md`](../../docs/architecture/agent-runtime.md)
for the complete runtime path.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/workflows` | Create workflow instance |
| `POST /v1/workflows/{id}/run` | Execute workflow |
| `POST /v1/analysis/roi` | Quick ROI calculation |
| `POST /v1/analysis/whitespace` | Gap analysis |
| `POST /v1/cases` | Generate business case |

### WebSocket authentication (header-only)

Layer 4 WebSocket endpoints are **header-auth only**. Clients must provide JWTs
using the `Sec-WebSocket-Protocol` header in canonical bearer format:

```text
Sec-WebSocket-Protocol: base64url.bearer.authorization, <jwt>
```

Security constraints:

- Query-parameter tokens such as `?token=<jwt>` are rejected.
- Missing or malformed `Sec-WebSocket-Protocol` auth headers are rejected with
  policy-violation close code `1008`.
- Tenant ownership is validated after authentication (workflow/prospect must
  belong to the authenticated tenant).

## Workflows

1. **ROICalculator**: Calculates ROI from formulas with prospect data
2. **Whitespace**: Identifies gaps between needs and capabilities
3. **BusinessCase**: Generates full business case documents
4. **Orchestrator**: Multi-agent coordination

## Tools (24 Skills)

- **Knowledge** (6): `query_graph`, `semantic_search`, `get_entity`, etc.
- **Calculation** (4): `evaluate_formula`, `calculate_roi`, etc.
- **CRM** (4): `get_prospect_data`, `update_opportunity`, etc.
- **Generation** (4): `generate_section`, `create_chart`, etc.
- **Integration** (4): `send_notification`, `create_task`, etc.
- **Utility** (2): `validate_input`, `format_currency`


## Workflow State Dependencies (Platform Contract)

Layer 4 orchestration follows the platform-level workflow state contract: `docs/reference/workflow-state-contract.md`.

For orchestration requests, Layer 4 must carry and/or resolve:

- `content_id` (upstream Layer 1 artifact identity)
- `extraction_job_id` (upstream Layer 2 execution identity)
- `graph_sync_status` (downstream Layer 3 sync gate: `pending | syncing | succeeded | failed`)
- `truth_approval_status` (Layer 5 governance gate: `pending | approved | rejected`)
- `correlation_id` + `trace_id` (cross-layer lineage and tracing)

Dependency-aware state behavior:

- Use `waiting_dependency` when upstream/downstream gate states are unresolved.
- Transition to `running` only when required dependency states are satisfied.
- Transition to `failed_terminal` for non-retryable dependency failures (for example `graph_sync_status=failed` with no retry policy, or `truth_approval_status=rejected` for gated flows).
- Use `retrying` for retryable dependency and tool failures according to retry budget.

## Company Knowledge → Layer 3 Ingestion Flow

When a company profile is approved, Layer 4 sync uses the canonical Layer 3 `POST /v1/ingest` route (not temporary signal persistence). The integration enforces contract handling on both sides:

- Layer 4 builds and validates a structured ingest request payload before dispatch.
- Layer 4 validates the Layer 3 ingest response schema before accepting success.
- Tenant and auth headers (`X-Tenant-ID`, `Authorization`, `X-Service-Auth`) are passed through unchanged into the ingestion call.
- Contract mismatch responses are treated as sync failures and surfaced for retry/triage.


## Middleware Order Contract

Layer 4 installs middleware in a deterministic, contract-checked order:

1. `configure_observability(...)` installs the canonical correlation middleware (single source for request ID/trace headers).
2. `configure_middleware(...)` installs governance, security, and CORS middleware.

Request/correlation IDs are intentionally sourced once from the shared observability middleware. All responses must expose stable trace headers (`X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID`) with the same value for a given request. Startup contract tests assert this behavior to prevent middleware drift.

## Database Migrations

Layer 4 uses Alembic for database schema management.

```bash
# Apply all pending migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current
```

### Environment Variables

- `LAYER4_DATABASE_URL`: Database connection string (PostgreSQL with asyncpg for runtime, psycopg2 for migrations)
- `CHECKPOINT_DATABASE_URL`: Fallback database URL for checkpoint database
- `LAYER4_OIDC_STATE_STORE_BACKEND`: OIDC state backend (`redis` default; `memory` for non-production only)
- `LAYER4_OIDC_STATE_TTL_SECONDS`: Strict TTL for OIDC state records (default: `300`)

### Schema Tables

The initial migration creates tables for:
- **Tenant Governance**: tenants, users, api_keys, tenant_isolation_tier_history
- **CRM Accounts**: accounts, account_sync_status
- **Billing**: billing_customers, billing_subscriptions, billing_webhook_events, billing_usage_events, billing_invoices, billing_invoice_items, billing_charges

### Stripe Webhook Reliability Guarantees

- Webhook signatures are verified before any persistence or business logic is run.
- Stripe events are persisted to `billing_webhook_events` keyed by `event.id` with inbox state (`status`, `attempt_count`, `last_error`, `next_retry_at`, `processed_at`, `payload_hash`).
- Idempotency scope is `event.id` and applies per Stripe account/event stream; duplicate deliveries are safely re-entrant even when concurrent workers race on the same event row.
- Duplicate deliveries with already-processed `event.id` are acknowledged idempotently and do not re-run side effects.
- Business handling runs asynchronously from request handling, with retryable failures marked for bounded exponential backoff and terminal failures moved to a final `failed` state.
- Durable retry queue processing is supported via `process_due_webhook_retries(...)`, which dequeues due `retryable` rows, applies backoff, and leaves poison messages in durable DLQ state (`status=failed`) with audit logs.
- Operational metrics are emitted as structured logs under `billing.webhook.metric.{accepted|processed|duplicate|retried|failed}` plus audit records like `billing.webhook.dlq_routed`.
- **Integrations**: integrations

All tables include `tenant_id` for multi-tenant isolation via Row-Level Security (RLS).

## License

## Secure service-to-service configuration

- Production/staging **must** configure explicit `LAYER{1,2,3,5}_API_URL` values; insecure HTTP defaults are not used.
- Canonical path is HTTPS to in-cluster service FQDNs (for example, `https://layer1-ingestion.value-fabric.svc.cluster.local:8000`).
- Service-mesh HTTP exceptions are allowed only when `SERVICE_MESH_MTLS_ENABLED=true` and mesh-level mTLS is enforced.
- Local development can use HTTP endpoints only with explicit `ALLOW_INSECURE_SERVICE_HTTP_IN_DEVELOPMENT=true`.

Proprietary - Value Fabric Enterprise Platform


## Migration reproducibility reference

- `docs/reference/migration-reproducibility-invariants.md` (mandatory migration invariants and incident-state reconstruction)
