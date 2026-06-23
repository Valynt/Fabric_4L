# Queue Topology

This runbook records the confirmed Celery and Redis queue topology for Value
Fabric background jobs.

## Components

| Component | Runtime | Broker/backend | Worker command |
| --- | --- | --- | --- |
| L1 ingestion tasks | `layer1_ingestion.shared.tasks` | `REDIS_URL` via L1 settings | `celery -A layer1_ingestion.shared.tasks worker` |
| L1 scheduled cleanup | `layer1_ingestion.shared.tasks` beat schedule | `REDIS_URL` via L1 settings | `celery -A layer1_ingestion.shared.tasks beat` |
| L2 extraction tasks | `layer2_extraction.shared.tasks` | `REDIS_URL` | `celery -A layer2_extraction.shared.tasks worker` |

## Queues

| Layer | Queue | Purpose |
| --- | --- | --- |
| L1 | `default` | Default Celery queue for ingestion pipeline tasks and beat schedule dispatch |
| L1 | `ingestion` | Reserved L1 ingestion queue consumed by constrained workers |
| L1 | `processing` | Reserved L1 processing queue consumed by constrained workers |
| L1 | `layer1_dlq` | Dead-letter queue name for L1 failures |
| L2 | `default` | Default queue for extraction tasks |
| L2 | `layer2_dlq` | Dead-letter queue name for L2 failures |

## Tenant Context

L1 task dispatch uses server-controlled tenant context. API routes enqueue jobs
with `process_scraping_job.delay(str(job.id), str(job.tenant_id))`. Celery task
entrypoints convert that value to a UUID and call database session helpers with
`require_tenant=True` before reading or mutating tenant-owned state.

L1 to L2 extraction dispatch includes `tenant_id` in the extraction payload.
Layer 2 rejects `run_extraction_task` calls when the config payload does not
include `tenant_id`.

## Retry And Dead-Letter Policy

The Celery apps use JSON serialization, UTC timestamps, one-hour task time
limits, late acknowledgements, worker-lost rejection, and three retries for
normal tasks.

Layer 1 outbox dispatch uses `MAX_DISPATCH_ATTEMPTS = 5`; after attempts are
exhausted, the outbox row is marked with a dead-letter status. The configured
DLQ queue names are still part of the queue topology and are validated by
`pnpm test:queues`.

## Idempotency

L1 immediate execution requests support a caller-provided idempotency key. The
API stores a Redis key scoped by tenant, target, and idempotency key, using
`nx=True` and a 24-hour TTL. Duplicate requests return the existing tenant-owned
job when present.

## Operations

Check static queue configuration:

```bash
pnpm test:queues
```

Check live compose service state:

```bash
docker compose ps
```

Inspect a running L1 worker:

```bash
celery -A layer1_ingestion.shared.tasks inspect ping
```

The inspect command must be run in an environment with the same `REDIS_URL` as
the workers.
