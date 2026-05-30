#!/bin/bash
set -e
echo "=== MAKEFILE (coverage) ==="
grep -E 'coverage|cov' Makefile | head -15

echo "=== PYPROJECT COV ==="
grep -rE 'fail_under|coverage' services/*/pyproject.toml | head -20

echo "=== LAYER1 PYPROJECT ==="
cat services/layer1-ingestion/pyproject.toml | grep -A5 'coverage'

echo "=== LAYER2 PYPROJECT ==="
cat services/layer2-extraction/pyproject.toml | grep -A5 'coverage'

echo "=== LAYER3 PYPROJECT ==="
cat services/layer3-knowledge/pyproject.toml | grep -A5 'coverage'

echo "=== LAYER4 PYPROJECT ==="
cat services/layer4-agents/pyproject.toml | grep -A5 'coverage'

echo "=== LAYER5 PYPROJECT ==="
cat services/layer5-ground-truth/pyproject.toml | grep -A5 'coverage'

echo "=== LAYER6 PYPROJECT ==="
cat services/layer6-benchmarks/pyproject.toml | grep -A5 'coverage'

echo "=== API PYPROJECT ==="
cat services/api/pyproject.toml | grep -A5 'coverage'

echo "=== DONE ==="
