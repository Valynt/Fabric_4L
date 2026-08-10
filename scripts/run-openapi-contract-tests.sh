#!/bin/bash
set -e

echo "==========================================================="
echo "Fabric_4L Contract Tests Runner"
echo "==========================================================="

echo "1. Bringing up Contract Testing Infrastructure..."
docker compose -f infra/compose/docker-compose.contract.yml up --build -d

echo "2. Waiting for services to be healthy..."
python3 scripts/check-contract-services.py

echo "3. Running Contract Tests..."
# First ensure we have the minimum number of tests
python3 scripts/ensure-pytest-collection.py tests/contract 330

# Run the actual tests
export CONTRACT_TEST_STRICT=1
pytest tests/contract -v

echo "4. Tearing down Infrastructure..."
docker compose -f infra/compose/docker-compose.contract.yml down -v

echo "Contract tests completed successfully!"
