#!/bin/bash
set -e

COMPOSE_FILE="infra/compose/docker-compose.contract.yml"

cleanup() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ]; then
    echo "Contract stack diagnostics (exit $status):"
    docker compose -f "$COMPOSE_FILE" ps --all || true
    docker compose -f "$COMPOSE_FILE" logs --no-color || true
  fi
  docker compose -f "$COMPOSE_FILE" down -v || true
  exit "$status"
}
trap cleanup EXIT

echo "==========================================================="
echo "Fabric_4L Contract Tests Runner"
echo "==========================================================="

echo "1. Bringing up Contract Testing Infrastructure..."
docker compose -f "$COMPOSE_FILE" up --build -d

echo "2. Waiting for services to be healthy..."
python3 scripts/check-contract-services.py

echo "3. Running Contract Tests..."
# First ensure we have the minimum number of tests
python3 scripts/ensure-pytest-collection.py --dir tests/contract --min-tests 330

# Run the actual tests
export CONTRACT_TEST_STRICT=1
pytest tests/contract -v

echo "4. Contract tests completed successfully; teardown runs via EXIT trap."
