#!/bin/bash
set -e

echo "==========================================================="
echo "Fabric_4L Local Test Audit"
echo "==========================================================="

echo "1. Checking Pytest Collections..."
python3 scripts/ensure-pytest-collection.py tests/contract 330
python3 scripts/ensure-pytest-collection.py tests/security 600
python3 scripts/ensure-pytest-collection.py tests/k8s 150

echo "2. Running Security Tests..."
pytest tests/security -v

echo "3. Running K8s Tests..."
pytest tests/k8s -v

echo "4. Running Contract Tests (with infra)..."
bash scripts/run-openapi-contract-tests.sh

echo "==========================================================="
echo "Local Test Audit completed successfully!"
echo "==========================================================="
