# Layer 5 Observability Schema (Ground Truth)

## Purpose

This reference defines the **governed observability contract** for Layer 5 state validation and Layer 3 KG sync operations.

Any rename/removal of keys, metric names, or metric labels in this document requires explicit governance review.

## Required structured log keys

All validation-transition and KG-sync outcome logs MUST include:

- `request_id`
- `tenant_id`
- `truth_object_id`
- `transition`
- `sync_status`

### Semantics

- `request_id`: Correlation identifier propagated from request/middleware context. Use `null` only when no request context exists.
- `tenant_id`: Authenticated tenant UUID from runtime context.
- `truth_object_id`: Layer 5 truth object UUID.
- `transition`: Canonical transition name (examples: `extracted->supported`, `approved->kg_sync`).
- `sync_status`: KG sync lifecycle status (examples: `pending`, `success`, `failed`, `disabled`, `not_attempted`).

## Metric contract

### Validation latency

- **Name:** `layer5_validation_latency_seconds`
- **Type:** Histogram
- **Labels:** `transition`

### Transition failures

- **Name:** `layer5_validation_transition_failures_total`
- **Type:** Counter
- **Labels:** `transition`, `reason`

### KG sync outcomes

- **Name:** `layer5_kg_sync_outcomes_total`
- **Type:** Counter
- **Labels:** `sync_status`, `transition`

## Linked runtime instrumentation points

- `services/layer5-ground-truth/src/layer5_ground_truth/services/state_machine.py`
- `services/layer5-ground-truth/src/layer5_ground_truth/integration/layer3_client.py`
- `services/layer5-ground-truth/src/metrics/prometheus_metrics.py`

## Governance links (dashboards / alerts / runbooks)

- Alert source-of-truth matrix: `docs/runbooks/operational/alerting-source-of-truth.md`
- Stale ground-truth runbook: `docs/troubleshooting/runbooks/application/stale-ground-truth.md`

Dashboards and alerts referencing Layer 5 validation/sync observability MUST align to this schema.
