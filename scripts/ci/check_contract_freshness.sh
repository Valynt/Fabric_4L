#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

OPENAPI_FILES=(
  "contracts/openapi/layer1-ingestion.json"
  "contracts/openapi/layer2-extraction.json"
  "contracts/openapi/layer3-knowledge.json"
  "contracts/openapi/layer4-agents.json"
  "contracts/openapi/layer5-ground-truth.json"
  "contracts/openapi/layer6-benchmarks.json"
  "contracts/openapi/fabric-4l-api.json"
)

GENERATED_TYPE_GLOBS=(
  "apps/web/src/api/generated"
)

printf '== Contract freshness gate ==\n'
printf 'Repository: %s\n' "$ROOT_DIR"

printf '\n== Regenerating OpenAPI source-of-truth files ==\n'
python3 scripts/export_openapi.py

printf '\n== Verifying required OpenAPI files exist ==\n'
for spec in "${OPENAPI_FILES[@]}"; do
  if [[ ! -s "$spec" ]]; then
    printf 'Missing or empty OpenAPI contract: %s\n' "$spec" >&2
    exit 1
  fi
  python3 -m json.tool "$spec" >/dev/null
  printf 'Verified %s\n' "$spec"
done

printf '\n== Regenerating frontend generated DTO types ==\n'
(
  cd apps/web
  pnpm run generate:types
)

printf '\n== Checking for generated contract drift ==\n'
if ! git diff --exit-code -- "${OPENAPI_FILES[@]}" "${GENERATED_TYPE_GLOBS[@]}"; then
  cat >&2 <<'EOF'

Contract freshness drift detected.

Run the following commands from the repository root and commit the resulting generated artifacts:

  python3 scripts/export_openapi.py
  cd apps/web && pnpm run generate:types

The committed OpenAPI JSON and frontend generated DTO types must remain deterministic outputs of the current backend service sources.
EOF
  exit 1
fi

printf '\n== Contract shape integrity checks ==\n'
python3 scripts/ci/check_l1_target_schema.py
python3 scripts/ci/check_targets_stats_named_schema.py
python3 scripts/ci/check_generated_jsonvalue_absent.py
python3 scripts/ci/check_clerk_tenant_response_exported.py

printf '\nContract freshness gate passed: OpenAPI contracts and generated frontend DTO types are current.\n'
