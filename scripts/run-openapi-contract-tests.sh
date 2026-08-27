#!/bin/bash
set -e

COMPOSE_FILE="infra/compose/docker-compose.backend-integrated.yml"

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

echo "1. Validating static contracts..."
# First ensure we have the minimum number of tests.
python3 scripts/ensure-pytest-collection.py --dir tests/contract --min-tests 330
pytest tests/contract -m "contract_static or contract_static_no_service" -v

echo "2. Bringing up the real L1-L6 contract stack..."
docker compose -f "$COMPOSE_FILE" up --build -d

echo "3. Waiting for L1-L6 services to be healthy..."
python3 scripts/check-contract-services.py

echo "4. Running live cross-layer and OpenAPI contracts..."
export CONTRACT_TEST_STRICT=1
export RUN_RUNTIME_CONTRACTS=1
export L1_URL=http://localhost:8001
export L2_URL=http://localhost:8002
export L3_URL=http://localhost:8003
export L4_URL=http://localhost:8004
export LAYER1_API_URL=http://localhost:8001
export LAYER2_API_URL=http://localhost:8002
export LAYER3_API_URL=http://localhost:8003
export LAYER4_API_URL=http://localhost:8004
export LAYER5_API_URL=http://localhost:8005
export LAYER6_API_URL=http://localhost:8006
export SERVICE_AUTH_SECRET=dev-local-service-auth-secret-do-not-use-in-production-32c
export RUNTIME_CONTRACT_TENANT_ID=00000000-0000-4000-8000-000000000001
pytest \
  tests/contract/test_layer_integration.py \
  tests/contract/test_layer_service_entrypoint_smoke.py \
  tests/contract/test_l3_route_alias_parity.py \
  -v

echo "5. Contract tests completed successfully; teardown runs via EXIT trap."
