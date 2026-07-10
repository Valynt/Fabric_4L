#!/usr/bin/env bash
set -euo pipefail

COMMITS=${1:-5}
if ! [[ "$COMMITS" =~ ^[0-9]+$ ]] || [ "$COMMITS" -lt 1 ]; then
  echo "Usage: $0 [positive-integer-commit-count]" >&2
  exit 2
fi

BASE_REF="HEAD~${COMMITS}"
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
  echo "Not enough history to inspect ${COMMITS} commits from HEAD." >&2
  exit 2
fi

echo "== Recent commit window =="
git log --oneline --no-decorate "${BASE_REF}..HEAD"

echo
changed_files=$(git diff --name-only "${BASE_REF}..HEAD")
if [ -z "$changed_files" ]; then
  echo "No changed files detected in the selected commit window."
  exit 0
fi

echo "== Changed files (${COMMITS} commits) =="
printf '%s\n' "$changed_files"

echo
run_root_js_checks=false
run_web_checks=false
run_python_checks=false

if printf '%s\n' "$changed_files" | rg -q '^(apps/web/|packages/|services/|package.json|pnpm-lock.yaml)'; then
  run_root_js_checks=true
fi
if printf '%s\n' "$changed_files" | rg -q '^apps/web/'; then
  run_web_checks=true
fi
if printf '%s\n' "$changed_files" | rg -q '(^scripts/ci/|^\.github/workflows/|\.py$)'; then
  run_python_checks=true
fi

run_step() {
  local label="$1"
  shift
  echo "== ${label} =="
  if "$@"; then
    echo "PASS: ${label}"
  else
    echo "WARN: ${label} failed (continuing for broad signal collection)" >&2
  fi
}

if [ "$run_root_js_checks" = true ]; then
  run_step "Monorepo tests" pnpm test
  run_step "Monorepo typecheck" pnpm typecheck
fi

if [ "$run_web_checks" = true ]; then
  run_step "Web lint" pnpm --filter ./apps/web run lint
fi

if [ "$run_python_checks" = true ]; then
  run_step "Default scope contract" node scripts/ci/check_default_scope.mjs
  run_step "Workflow reference consistency" python3 scripts/ci/check_workflow_references.py --workflow-glob '*.yml'
  run_step "Build/promotion artifact contract" python3 scripts/ci/validate_promotion_artifact_contract.py --build-workflow .github/workflows/build-deploy.yml --promotion-workflow .github/workflows/environment-promotion.yml
fi

echo
echo "Regression guard completed for last ${COMMITS} commits."
