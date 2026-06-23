#!/usr/bin/env bash
# L1-L6 golden-path API scenario
# Exercises the full Fabric_4L value-engine pipeline via curl.
# Source: .windsurf/plans/l1-l6-api-curl-scenario-b653b2.md

set -euo pipefail

L1=${LAYER1_API_URL:-http://localhost:8001}
L2=${LAYER2_API_URL:-http://localhost:8002}
L3=${LAYER3_API_URL:-http://localhost:8003}
L4=${LAYER4_API_URL:-http://localhost:8004}
L5=${LAYER5_API_URL:-http://localhost:8005}
L6=${LAYER6_API_URL:-http://localhost:8006}

TENANT_ID=${FABRIC_TENANT_ID:-"tenant-00000000-0000-4000-8000-000000000001"}
USER_ID=${FABRIC_USER_ID:-"user-backend-validation"}
ROLE=${FABRIC_ROLE:-"super_admin"}
SERVICE_AUTH=${SERVICE_AUTH_SECRET:-"dev-local-service-auth-secret-do-not-use-in-production-32c"}
RUN_ID=${BACKEND_VALIDATION_RUN_ID:-"curl-l1-l6-$(date +%s)"}

ACCOUNT_ID=${ACCOUNT_ID:-"acme-${RUN_ID}"}
DOCUMENT_ID=${DOCUMENT_ID:-"doc-${RUN_ID}"}
EVIDENCE_ID=${EVIDENCE_ID:-"ev-${RUN_ID}"}
FORMULA_ID=${FORMULA_ID:-"formula-${RUN_ID}"}
BENCHMARK_ID=${BENCHMARK_ID:-"bench-${RUN_ID}"}

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

curl_json() {
  local method=$1
  local url=$2
  shift 2
  curl -sS -X "${method}" "${url}" "${COMMON_HEADERS[@]}" "$@"
}

echo "=== L1-L6 Golden Path API Scenario ==="
echo "Run ID: ${RUN_ID}"
echo "Tenant: ${TENANT_ID}"
echo "Account: ${ACCOUNT_ID}"
echo "Document: ${DOCUMENT_ID}"
echo ""

echo "=== L1: Ingest source ==="
# Canonical unified source intake (Notes / Web / Audio / CRM / PDF / Meeting).
# Synchronous response only confirms acceptance; downstream layers process async.
SOURCE=$(curl_json POST "${L1}/api/v1/ingestion/sources" \
  -d "{
    \"account_id\": \"${ACCOUNT_ID}\",
    \"source_type\": \"notes\",
    \"title\": \"Acme Validation Discovery Notes — ${RUN_ID}\",
    \"content\": \"Pipeline conversion improved 11 percent after guided value discovery.\",
    \"external_reference\": \"${DOCUMENT_ID}\",
    \"idempotency_key\": \"${DOCUMENT_ID}\",
    \"requested_outputs\": [\"fabric_found_summary\"]
  }")
echo "Source response: ${SOURCE}" | jq . || echo "${SOURCE}"
SOURCE_ID=$(echo "${SOURCE}" | jq -r '.source_id // empty')
RUN_ID_L1=$(echo "${SOURCE}" | jq -r '.ingestion_run_id // empty')

if [[ -n "${RUN_ID_L1}" ]]; then
  echo "=== L1: Poll ingestion run (best effort) ==="
  for _ in {1..5}; do
    RUN=$(curl_json GET "${L1}/api/v1/ingestion/runs/${RUN_ID_L1}")
    echo "Run state: ${RUN}" | jq . || echo "${RUN}"
    [[ "$(echo "${RUN}" | jq -r '.status // empty' | tr '[:upper:]' '[:lower:]')" =~ (ready|failed|cancelled|needs_input|needs_review) ]] && break
    sleep 1
  done
fi
echo ""

echo "=== L2: Extraction ==="
EXTRACTION=$(curl_json POST "${L2}/api/v1/extractions" \
  -d "{
    \"source_id\": \"${DOCUMENT_ID}\",
    \"account_id\": \"${ACCOUNT_ID}\",
    \"mode\": \"curl_l1_l6\"
  }")
echo "Extraction response: ${EXTRACTION}" | jq . || echo "${EXTRACTION}"
EXTRACTION_ID=$(echo "${EXTRACTION}" | jq -r '.id // .extraction_id // "${DOCUMENT_ID}"')

echo "Signals:"
curl_json GET "${L2}/api/v1/extractions/${EXTRACTION_ID}/signals" | jq . || true
echo ""

echo "=== L3: Knowledge Graph ==="
GRAPH=$(curl_json POST "${L3}/api/v1/graph/context" \
  -d "{
    \"account_id\": \"${ACCOUNT_ID}\",
    \"source_ids\": [\"${DOCUMENT_ID}\"],
    \"signal_ids\": [\"${EXTRACTION_ID}\"],
    \"evidence_ids\": [\"${EVIDENCE_ID}\"]
  }")
echo "Graph context: ${GRAPH}" | jq . || echo "${GRAPH}"
GRAPH_ID=$(echo "${GRAPH}" | jq -r '.id // .graph_id // "${ACCOUNT_ID}"')
echo ""

echo "=== L4: Hypothesis ==="
curl_json POST "${L4}/v1/hypotheses" \
  -d "{
    \"account_id\": \"${ACCOUNT_ID}\",
    \"graph_context_id\": \"${GRAPH_ID}\",
    \"require_evidence\": true
  }" | jq . || true
echo ""

echo "=== L4: ROI Analysis ==="
curl_json POST "${L4}/v1/analysis/roi" \
  -d "{
    \"account_id\": \"${ACCOUNT_ID}\",
    \"formula_id\": \"${FORMULA_ID}\",
    \"variables\": {
      \"annual_revenue\": 10000000,
      \"conversion_lift_pct\": 11,
      \"implementation_cost\": 125000
    },
    \"scenarios\": [\"conservative\", \"expected\", \"optimistic\"]
  }" | jq . || true
echo ""

echo "=== L4: Business Case ==="
CASE=$(curl_json POST "${L4}/v1/cases" \
  -d "{
    \"account_id\": \"${ACCOUNT_ID}\",
    \"evidence_ids\": [\"${EVIDENCE_ID}\"],
    \"approval_status\": \"submitted\"
  }")
echo "Case response: ${CASE}" | jq . || echo "${CASE}"
CASE_ID=$(echo "${CASE}" | jq -r '.id // .case_id')
echo ""

echo "=== L4: Approval ==="
curl_json POST "${L4}/v1/cases/${CASE_ID}/approval" \
  -d "{
    \"status\": \"approved\",
    \"reviewer_id\": \"${USER_ID}\",
    \"decision\": \"approve\"
  }" | jq . || true
echo ""

echo "=== L4: Export ==="
curl_json GET "${L4}/v1/cases/${CASE_ID}/export" | jq . || true
echo ""

echo "=== L4: Traceability ==="
curl_json GET "${L4}/v1/cases/${CASE_ID}/traceability?include_raw_sources=true" | jq . || true
echo ""

echo "=== L5: Ground Truth Assumption ==="
curl_json POST "${L5}/api/v1/truth/assumptions" \
  -d "{
    \"id\": \"${EVIDENCE_ID}\",
    \"account_id\": \"${ACCOUNT_ID}\",
    \"claim\": \"Conversion improved 11 percent\",
    \"source_id\": \"${DOCUMENT_ID}\",
    \"status\": \"pending_review\"
  }" | jq . || true
echo ""

echo "=== L5: Assumption Decision ==="
curl_json POST "${L5}/api/v1/truth/assumptions/${EVIDENCE_ID}/decisions" \
  -d "{
    \"status\": \"approved\",
    \"reviewer_id\": \"${USER_ID}\",
    \"reason\": \"source verified\"
  }" | jq . || true
echo ""

echo "=== L6: Benchmark ==="
curl_json POST "${L6}/v1/benchmarks" \
  -d "{
    \"id\": \"${BENCHMARK_ID}\",
    \"metric\": \"conversion_lift_pct\",
    \"value\": 11,
    \"source\": \"curl_l1_l6\",
    \"effective_date\": \"2024-01-01\",
    \"account_id\": \"${ACCOUNT_ID}\"
  }" | jq . || true
echo ""

echo "=== L6: Benchmark Policy ==="
curl_json POST "${L6}/v1/benchmarks/policy/evaluate" \
  -d "{
    \"benchmark_id\": \"${BENCHMARK_ID}\",
    \"formula_id\": \"${FORMULA_ID}\",
    \"account_id\": \"${ACCOUNT_ID}\"
  }" | jq . || true
echo ""

echo "=== Scenario complete ==="
echo "Run ID: ${RUN_ID}"
echo "Account ID: ${ACCOUNT_ID}"
echo "Case ID: ${CASE_ID}"
