# Jaeger Storage and Recovery Runbook

## Storage modes

- **Local/dev (Docker Compose):** `jaegertracing/all-in-one` uses `SPAN_STORAGE_TYPE=badger` with `BADGER_EPHEMERAL=false` and durable volume `jaeger-data:/badger`.
- **Shared envs (staging/prod on Kubernetes):** `jaegertracing/all-in-one` uses `SPAN_STORAGE_TYPE=elasticsearch` (OpenSearch-compatible endpoint) via `ConfigMap/jaeger-storage-config` and `Secret/jaeger-storage-credentials`.

## Retention and TTL

- **Local/dev Badger TTL:** `BADGER_SPAN_STORE_TTL=336h` (14 days).
- **Staging/prod OpenSearch/Elasticsearch TTL:** Jaeger sets `ES_USE_ILM=true` and `ES_ILM_POLICY_NAME=jaeger-hot-7d`; enforce lifecycle retention in the backing cluster for `jaeger-span*` indices.

## Recovery expectations

- Restarting Jaeger pods/containers should not delete historical traces while they are within TTL/ILM retention windows.
- In-flight spans buffered in memory can be lost during abrupt termination.

## Staging validation: trace continuity across restart

1. Generate a known trace in staging (from any Layer service instrumented with OTLP).
2. Record the trace ID from Jaeger UI (`/jaeger`) or API query.
3. Restart Jaeger:
   - `kubectl -n monitoring rollout restart deployment/jaeger`
   - `kubectl -n monitoring rollout status deployment/jaeger --timeout=180s`
4. Query for the same trace ID after readiness returns.
5. Confirm the trace is still present and span tree is intact.

If the trace is missing, validate OpenSearch/Elasticsearch credentials, ILM/index policy, and Jaeger readiness on admin port `14269`.
