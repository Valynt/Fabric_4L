#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${RELEASE_SMOKE_COMPOSE_FILE:-infra/compose/docker-compose.release-smoke.yml}"
ARTIFACT_DIR="${RELEASE_SMOKE_ARTIFACT_DIR:-artifacts/release_smoke}"
PROJECT_NAME="${RELEASE_SMOKE_PROJECT_NAME:-fabric4l-release-smoke-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}}"
STACK_TIMEOUT="${RELEASE_SMOKE_STACK_TIMEOUT:-900s}"
PYTEST_TIMEOUT="${RELEASE_SMOKE_PYTEST_TIMEOUT:-300s}"
PYTEST_BIN="${PYTEST:-pytest}"
PYTEST_TARGET="${RELEASE_SMOKE_PYTEST_TARGET:-tests/backend_integrated/test_release_environment_smoke_validation.py}"
PYTEST_MARKER="${RELEASE_SMOKE_PYTEST_MARKER:-release_smoke}"
PYTEST_EVIDENCE_NAME="${RELEASE_SMOKE_PYTEST_EVIDENCE_NAME:-release_smoke}"

mkdir -p "$ARTIFACT_DIR/logs"

fail() {
  echo "❌ release-smoke: $*" >&2
  exit 1
}

if [ ! -f "$COMPOSE_FILE" ]; then
  fail "compose file '$COMPOSE_FILE' is missing"
fi

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker CLI is required for release-smoke validation; no mock or skip fallback is allowed"
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is required for release-smoke validation"
fi

if ! command -v timeout >/dev/null 2>&1; then
  fail "GNU timeout is required to bound release-smoke validation"
fi

compose() {
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

capture_diagnostics() {
  local status=$?
  set +e
  compose ps --all > "$ARTIFACT_DIR/logs/compose_ps.txt" 2>&1
  compose logs --no-color > "$ARTIFACT_DIR/logs/compose_logs.txt" 2>&1
  compose down -v --remove-orphans > "$ARTIFACT_DIR/logs/compose_down.txt" 2>&1
  set -e
  exit "$status"
}
trap capture_diagnostics EXIT

echo "→ release-smoke: validating compose config ($COMPOSE_FILE)"
compose config > "$ARTIFACT_DIR/compose_config.resolved.yml"

echo "→ release-smoke: starting full L1–L6 stack (project=$PROJECT_NAME, timeout=$STACK_TIMEOUT)"
timeout "$STACK_TIMEOUT" docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build --wait

echo "→ release-smoke: probing service readiness"
export RELEASE_SMOKE_EVIDENCE="$ARTIFACT_DIR/service_readiness.json"
export BACKEND_VALIDATION_HTTP_TIMEOUT="${BACKEND_VALIDATION_HTTP_TIMEOUT:-3}"
python scripts/ci/probe_release_smoke_services.py

echo "→ release-smoke: running backend-integrated pytest target '$PYTEST_TARGET' with marker '$PYTEST_MARKER' (timeout=$PYTEST_TIMEOUT)"
export BACKEND_VALIDATION_RUN_ID="${BACKEND_VALIDATION_RUN_ID:-release-smoke-${GITHUB_SHA:-local}}"
export LAYER1_API_URL="${LAYER1_API_URL:-http://localhost:8001}"
export LAYER2_API_URL="${LAYER2_API_URL:-http://localhost:8002}"
export LAYER3_API_URL="${LAYER3_API_URL:-http://localhost:8003}"
export LAYER4_API_URL="${LAYER4_API_URL:-http://localhost:8004}"
export LAYER5_API_URL="${LAYER5_API_URL:-http://localhost:8005}"
export LAYER6_API_URL="${LAYER6_API_URL:-http://localhost:8006}"

timeout "$PYTEST_TIMEOUT" "$PYTEST_BIN" \
  "$PYTEST_TARGET" \
  -m "$PYTEST_MARKER" \
  -v \
  --tb=short \
  --junitxml="$ARTIFACT_DIR/${PYTEST_EVIDENCE_NAME}_junit.xml" \
  | tee "$ARTIFACT_DIR/logs/${PYTEST_EVIDENCE_NAME}_pytest.log"

echo "✅ release-smoke: full L1–L6 stack validation passed"
