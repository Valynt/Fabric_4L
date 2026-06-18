---
owner: docs-team
status: active
last_reviewed: 2026-06-15
---

# L1–L6 API curl scenario: Account to approved business case

This page documents the canonical curl command sequence that exercises the full Fabric4L value-engine pipeline from ingestion through an approved business case. You can use it to validate a local backend stack, reproduce a golden-path integration test, or understand how the six layers hand off data.

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Who this is for

- **Backend developers** validating layer-to-layer handoffs locally.
- **QA engineers** reproducing the backend-integrated golden path without the Python harness.
- **Integrators** learning the canonical request shape for each layer.

## Prerequisites

- Backend stack running on `localhost:8001` through `localhost:8006`.
  - Start with `docker-compose.backend-integrated.yml` or run `pnpm dev:layer*` individually.
- A tenant and user identity for the required headers.
- The same dev service-auth secret the backend-integrated harness uses.
- `jq` installed if you want to parse JSON responses automatically.
- <span class="vp-badge vp-badge--permission">Required</span> `super_admin` role or equivalent for the validation headers.

## Common environment

Set these variables once. Every later step reuses them.

```bash
export L1=http://localhost:8001
export L2=http://localhost:8002
export L3=http://localhost:8003
export L4=http://localhost:8004
export L5=http://localhost:8005
export L6=http://localhost:8006

export TENANT_ID="tenant-00000000-0000-4000-8000-000000000001"
export USER_ID="user-backend-validation"
export ROLE="super_admin"
export SERVICE_AUTH="dev-local-service-auth-secret-do-not-use-in-production-32c"
export RUN_ID="curl-l1-l6-$(date +%s)"

export ACCOUNT_ID="acme-${RUN_ID}"
export DOCUMENT_ID="doc-${RUN_ID}"
export EVIDENCE_ID="ev-${RUN_ID}"
export FORMULA_ID="formula-${RUN_ID}"
export BENCHMARK_ID="bench-${RUN_ID}"

COMMON_HEADERS=(
  -H "Content-Type: application/json"
  -H "X-Tenant-ID: ${TENANT_ID}"
  -H "X-User-ID: ${USER_ID}"
  -H "X-Role: ${ROLE}"
  -H "X-Organization-ID: ${TENANT_ID}"
  -H "X-Org-ID: ${TENANT_ID}"
  -H "X-Service-Auth: ${SERVICE_AUTH}"
  -H "X-Dev-Tenant-ID: ${TENANT_ID}"
  -H "X-Dev-User-ID: ${USER_ID}"
  -H "X-Validation-Run-ID: ${RUN_ID}"
)
```

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| `super_admin` | Ingest sources, run extractions, create cases, approve assumptions | Organization |
| `service` | Call layer-to-layer endpoints with `X-Service-Auth` | Service-to-service |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> L1 ingestion is asynchronous. Poll the returned run ID until the status is `completed` or `failed`.
- <span class="vp-badge vp-badge--limit">Limit</span> Do not use the `dev-local-service-auth-secret-*` value in production. It is only for local validation.
- <span class="vp-badge vp-badge--limit">Limit</span> Each layer validates the same tenant context. Mismatched `X-Tenant-ID` / `X-Dev-Tenant-ID` headers will be rejected.

## Step-by-step instructions

### 1. L1 — Ingest a source

All source tabs converge on a single intake endpoint. The synchronous response confirms acceptance; the actual processing is durable and asynchronous.

```bash
L1_RESPONSE=$(curl -s "${L1}/api/v1/ingestion/sources" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "account_id": "'"${ACCOUNT_ID}"'",
    "source_type": "notes",
    "title": "Acme Validation Discovery Notes — '"${RUN_ID}"'",
    "content": "Pipeline conversion improved 11 percent after guided value discovery.",
    "external_reference": "'"${DOCUMENT_ID}"'",
    "idempotency_key": "'"${DOCUMENT_ID}"'",
    "requested_outputs": ["fabric_found_summary"]
  }')

echo "${L1_RESPONSE}"

SOURCE_ID=$(echo "${L1_RESPONSE}" | jq -r '.source_id // empty')
RUN_ID_L1=$(echo "${L1_RESPONSE}" | jq -r '.ingestion_run_id // empty')
```

Expected response:

```json
{
  "source_id": "src_...",
  "source_version_id": "srcv_...",
  "ingestion_run_id": "ing_...",
  "status": "accepted",
  "revision": 1
}
```

Poll the async run until it completes:

```bash
curl "${L1}/api/v1/ingestion/runs/${RUN_ID_L1}" \
  "${COMMON_HEADERS[@]}"
```

### 2. L2 — Extract signals

Run extraction against the source returned by L1, then retrieve the generated signals.

```bash
EXTRACTION=$(curl -s "${L2}/api/v1/extractions" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "source_id": "'"${SOURCE_ID}"'",
    "account_id": "'"${ACCOUNT_ID}"'",
    "mode": "curl_l1_l6"
  }')

EXTRACTION_ID=$(echo "${EXTRACTION}" | jq -r '.id // .extraction_id // empty')

curl "${L2}/api/v1/extractions/${EXTRACTION_ID}/signals" \
  "${COMMON_HEADERS[@]}"
```

### 3. L3 — Build graph context

Create a graph context that links the L1 source, L2 signals, and any evidence you will use downstream.

```bash
GRAPH=$(curl -s "${L3}/api/v1/graph/context" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "account_id": "'"${ACCOUNT_ID}"'",
    "source_ids": ["'"${SOURCE_ID}"'"],
    "signal_ids": ["'"${EXTRACTION_ID}"'"],
    "evidence_ids": ["'"${EVIDENCE_ID}"'"]
  }')

GRAPH_ID=$(echo "${GRAPH}" | jq -r '.id // .graph_id // empty')
```

### 4. L4 — Generate hypothesis, ROI, case, approval, and traceability

#### 4.1 Generate a hypothesis

```bash
curl "${L4}/v1/hypotheses" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "account_id": "'"${ACCOUNT_ID}"'",
    "graph_context_id": "'"${GRAPH_ID}"'",
    "require_evidence": true
  }'
```

#### 4.2 Run an ROI analysis

```bash
curl "${L4}/v1/analysis/roi" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "account_id": "'"${ACCOUNT_ID}"'",
    "formula_id": "'"${FORMULA_ID}"'",
    "variables": {
      "annual_revenue": 10000000,
      "conversion_lift_pct": 11,
      "implementation_cost": 125000
    },
    "scenarios": ["conservative", "expected", "optimistic"]
  }'
```

#### 4.3 Create a business case

```bash
CASE=$(curl -s "${L4}/v1/cases" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "account_id": "'"${ACCOUNT_ID}"'",
    "evidence_ids": ["'"${EVIDENCE_ID}"'"],
    "approval_status": "submitted"
  }')

CASE_ID=$(echo "${CASE}" | jq -r '.id // .case_id // empty')
```

#### 4.4 Approve the business case

```bash
curl "${L4}/v1/cases/${CASE_ID}/approval" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "status": "approved",
    "reviewer_id": "'"${USER_ID}"'",
    "decision": "approve"
  }'
```

#### 4.5 Export the approved case

```bash
curl "${L4}/v1/cases/${CASE_ID}/export" \
  "${COMMON_HEADERS[@]}"
```

#### 4.6 Verify traceability back to the raw L1 source

```bash
curl "${L4}/v1/cases/${CASE_ID}/traceability?include_raw_sources=true" \
  "${COMMON_HEADERS[@]}"
```

### 5. L5 — Create and approve a truth assumption

```bash
curl "${L5}/api/v1/truth/assumptions" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "id": "'"${EVIDENCE_ID}"'",
    "account_id": "'"${ACCOUNT_ID}"'",
    "claim": "Conversion improved 11 percent",
    "source_id": "'"${SOURCE_ID}"'",
    "status": "pending_review"
  }'

curl "${L5}/api/v1/truth/assumptions/${EVIDENCE_ID}/decisions" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "status": "approved",
    "reviewer_id": "'"${USER_ID}"'",
    "reason": "source verified"
  }'
```

### 6. L6 — Create a benchmark and evaluate policy

```bash
curl "${L6}/v1/benchmarks" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "id": "'"${BENCHMARK_ID}"'",
    "metric": "conversion_lift_pct",
    "value": 11,
    "source": "curl_l1_l6",
    "effective_date": "2024-01-01",
    "account_id": "'"${ACCOUNT_ID}"'"
  }'

curl "${L6}/v1/benchmarks/policy/evaluate" \
  "${COMMON_HEADERS[@]}" \
  -d '{
    "benchmark_id": "'"${BENCHMARK_ID}"'",
    "formula_id": "'"${FORMULA_ID}"'",
    "account_id": "'"${ACCOUNT_ID}"'"
  }'
```

## Verification checklist

Use this checklist to confirm the pipeline executed correctly.

- [ ] L1 source persists with `account_id` and `source_id` lineage.
- [ ] L2 extraction references `SOURCE_ID` and emits signals.
- [ ] L3 graph context includes `ACCOUNT_ID`, `SOURCE_ID`, and `EXTRACTION_ID`.
- [ ] L4 hypothesis contains `evidence` or `claim` markers.
- [ ] L4 ROI response contains `roi`, `payback`, or `projection`.
- [ ] L4 business case reaches `approved` and `/export` returns a download or export URL.
- [ ] L4 traceability endpoint includes the raw L1 `SOURCE_ID`.
- [ ] L5 assumption decision is `approved`.
- [ ] L6 benchmark policy evaluation returns `benchmark`, `policy`, or `formula` markers.

## Troubleshooting

??? question "Issue: L1 returns 401 or 403"
    **Cause:** The `X-Service-Auth` or `X-Dev-*` headers are missing or mismatched.
    **Resolution:** Confirm the stack is running in dev/validation mode and that `SERVICE_AUTH` matches the secret configured for the backend-integrated test harness.

??? question "Issue: L2 extraction fails with source not found"
    **Cause:** L2 was called before the L1 async run completed, or the wrong ID was passed.
    **Resolution:** Poll the L1 run until `status` is `completed`, and make sure the request uses `source_id` from the L1 response, not `DOCUMENT_ID`.

??? question "Issue: L4 case approval returns 422"
    **Cause:** The case may already be in the target state, or the reviewer is not authorized.
    **Resolution:** Check the case state first with `GET /v1/cases/${CASE_ID}`, then resubmit with a user that has the `super_admin` role.

??? question "Issue: L6 policy evaluation returns empty results"
    **Cause:** The benchmark or formula referenced may not exist in the same tenant.
    **Resolution:** Verify `BENCHMARK_ID` and `FORMULA_ID` were created under the same `TENANT_ID` and that the benchmark `metric` matches the formula variables.

## Related pages

- [API overview](../../api/overview.md)
- [API authentication](../../api/authentication.md)
- [Fabric4L testing guide](./testing.md)
- [System overview](../architecture/system-overview.md)
- [Data flow](../architecture/data-flow.md)

## Escalation path

If the scenario fails after the troubleshooting steps:

1. Capture the full curl command, response body, and `X-Validation-Run-ID`.
2. Check the logs for the failing layer in `docker-compose.backend-integrated.yml`.
3. Open a ticket against the **Platform Engineering** team with severity **S2** if the failure blocks a release gate.

## References

- `tests/backend_integrated/test_backend_integrated_golden_path.py` — L1→L4 golden path assertions.
- `tests/backend_integrated/test_cross_layer_data_flow_validation.py` — L1↔L2↔L3↔L4 handoff plus L5/L6 coverage.
- `docker-compose.backend-integrated.yml` — service URLs and dependency wiring.
- `contracts/openapi/` — canonical OpenAPI specs for L1–L6.
