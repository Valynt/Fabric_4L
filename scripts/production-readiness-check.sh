#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
cd "${ROOT_DIR}"

FAILED_STEP="startup"

fail() {
  local message="$1"
  echo "FAIL: ${message}" >&2
  exit 1
}

on_error() {
  local exit_code=$?
  echo "FAIL: Production readiness check failed during '${FAILED_STEP}' (exit ${exit_code})." >&2
  exit "${exit_code}"
}
trap on_error ERR

run_step() {
  local label="$1"
  shift
  FAILED_STEP="${label}"
  echo "${label}..."
  "$@"
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || fail "Required command '${command_name}' is not installed or not on PATH."
}

require_make_target() {
  local target="$1"
  make -n "${target}" >/dev/null 2>&1 || fail "Required make target '${target}' is not available."
}

check_placeholder_secrets() {
  local rendered
  rendered="$(mktemp)"
  kustomize build k8s/envs/prod > "${rendered}"

  if grep -i -n -E 'changeme|replace_me|password[[:space:]]*[:=][[:space:]]*(password|changeme|replace_me|placeholder)' "${rendered}"; then
    rm -f "${rendered}"
    fail "Placeholder secrets or forbidden secret literals found in rendered production manifests."
  fi

  rm -f "${rendered}"
}

coverage_check() {
  local layer="$1"
  local threshold="${2:-}"

  [[ -d "${layer}" ]] || fail "Coverage layer '${layer}' does not exist."
  [[ -d "${layer}/tests" ]] || fail "Coverage layer '${layer}' has no tests directory."

  echo "  Checking ${layer}..."
  if [[ -n "${threshold}" ]]; then
    (cd "${layer}" && "${PYTHON_BIN}" -m pytest --cov --cov-report=term-missing --cov-fail-under="${threshold}")
  else
    (cd "${layer}" && "${PYTHON_BIN}" -m pytest --cov --cov-report=term-missing)
  fi
}

check_coverage_thresholds() {
  coverage_check services/layer1-ingestion
  coverage_check services/layer2-extraction
  coverage_check services/layer3-knowledge
  coverage_check services/layer4-agents
  coverage_check services/layer5-ground-truth
  coverage_check services/layer6-benchmarks
}

echo "=== Fabric_4L Production Readiness Check ==="

FAILED_STEP="preflight command validation"
require_command gitleaks
require_command pip-audit
require_command pnpm
require_command make
require_command "${PYTHON_BIN}"
require_command kubectl
require_command kustomize
require_command docker
require_command grep
require_make_target lint
require_make_target typecheck
require_make_target test
require_make_target contract-tests
require_make_target security-smoke
require_make_target check-migration-heads
require_make_target docker-build

run_step "1. Secret scan" gitleaks detect --source . -v
run_step "2. Python dependency audit" pip-audit
run_step "3. Node dependency audit and verified security backports" \
  python scripts/ci/check_node_security_backports.py --audit \
  --project-dir apps/web --audit-report-output frontend-audit.json
run_step "4. Python lint" make lint
run_step "5. Frontend lint" pnpm --dir apps/web run lint
run_step "6. Typecheck" make typecheck
run_step "7. Unit tests" make test
run_step "8. Contract tests" make contract-tests
run_step "9. Security tests" make security-smoke
run_step "10. Migration heads" make check-migration-heads
run_step "11. K8s dry-run" kubectl apply --dry-run=client -k k8s/base/
run_step "12. Placeholder secrets check" check_placeholder_secrets
run_step "13. Docker build" make docker-build
run_step "14. Coverage check" check_coverage_thresholds

echo "=== ALL CHECKS PASSED ==="
echo "Ready for production deployment"
