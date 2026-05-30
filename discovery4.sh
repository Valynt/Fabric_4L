#!/bin/bash
set -e
echo "=== FRONTEND COVERAGE ==="
grep -A5 'coverage' apps/web/package.json || true

echo "=== REPORTS ==="
ls -1 reports/*.md | head -10 || true

echo "=== LAYER5 FAIL_UNDER ==="
grep 'fail_under' services/layer5-ground-truth/pyproject.toml || true

echo "=== LAYER6 FAIL_UNDER ==="
grep 'fail_under' services/layer6-benchmarks/pyproject.toml || true

echo "=== LAYER7 FAIL_UNDER ==="
grep 'fail_under' services/layer7-billing/pyproject.toml || true

echo "=== BILLING FAIL_UNDER ==="
grep 'fail_under' services/billing/pyproject.toml || true

echo "=== SECURITY TEST COUNT ==="
ls -1 tests/security/*.py | wc -l

echo "=== CONTRACT TEST COUNT ==="
ls -1 tests/contract/*.py | wc -l

echo "=== INTEGRATION TEST COUNT ==="
ls -1 tests/integration/*.py | wc -l

echo "=== E2E TEST COUNT ==="
ls -1 tests/e2e/*.py | wc -l

echo "=== DONE ==="
