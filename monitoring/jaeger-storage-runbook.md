# Jaeger Trace Storage Runbook (OpenSearch)

## Overview

Jaeger in `k8s/monitoring/jaeger-deployment.yaml` is configured to persist spans in OpenSearch (`SPAN_STORAGE_TYPE=elasticsearch`) instead of volatile in-memory storage.
This ensures traces survive Jaeger pod restarts and rolling deployments.

## Storage backend configuration

- Backend endpoint comes from `ConfigMap/jaeger-storage-config` (`es_server_urls`).
- Auth and TLS materials are read from `Secret/jaeger-storage-credentials`.
- Secret is expected to be injected using the existing Infisical pattern (`infisical.com/inject: "true"`, `infisical.com/path: "/monitoring"`).

Required secret keys:

- `username`
- `password`
- `ca.crt`
- `tls.crt`
- `tls.key`

## Retention and index behavior

Configured retention and index settings:

- `ES_MAX_SPAN_AGE=168h` (7 days query horizon)
- `ES_USE_ALIASES=true`
- `ES_NUM_SHARDS=3`
- `ES_NUM_REPLICAS=1`

Operational recommendation:

1. Apply OpenSearch ISM/ILM policy for `jaeger-span-*` indexes with 7 day retention.
2. Add rollover policy by size/time (for example `30gb` or `24h`) to keep shard sizes stable.
3. Keep at least one replica for historical trace durability.

## Capacity baseline (current deployment)

Jaeger all-in-one resources are tuned for moderate-to-high trace volume:

- Requests: `cpu=1000m`, `memory=3Gi`
- Limits: `cpu=4000m`, `memory=8Gi`

If ingestion spikes or UI query latency increases:

1. Scale OpenSearch data nodes first.
2. Increase Jaeger CPU limit and collector queue capacity.
3. Lower trace sample rate if needed to protect cluster stability.

## Failure modes and response

1. **OpenSearch unavailable / auth failure**
   - Symptom: Jaeger collector errors, missing recent traces.
   - Check: Jaeger logs for ES connection/auth/TLS errors.
   - Action: verify Infisical secret sync and OpenSearch endpoint health.

2. **Retention policy not applied**
   - Symptom: storage growth and high disk watermark events.
   - Check: OpenSearch index lifecycle status for `jaeger-span-*`.
   - Action: apply/repair ISM/ILM policy and force rollover.

3. **TLS trust mismatch**
   - Symptom: handshake failures to OpenSearch.
   - Check: `ca.crt`/client cert rotation timestamps and certificate chain.
   - Action: rotate `jaeger-storage-credentials` and restart Jaeger deployment.

## Verification commands

```bash
kubectl -n monitoring get deployment jaeger -o yaml | grep -E 'SPAN_STORAGE_TYPE|ES_MAX_SPAN_AGE|ES_SERVER_URLS'
kubectl -n monitoring get secret jaeger-storage-credentials -o jsonpath='{.metadata.annotations}'
kubectl -n monitoring logs deploy/jaeger --tail=200
```
