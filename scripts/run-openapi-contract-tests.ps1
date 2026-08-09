$ErrorActionPreference = "Stop"

Write-Host "==========================================================="
Write-Host "Fabric_4L Contract Tests Runner"
Write-Host "==========================================================="

Write-Host "1. Bringing up Contract Testing Infrastructure..."
docker compose -f infra/compose/docker-compose.contract.yml up --build -d

Write-Host "2. Waiting for services to be healthy..."
python scripts/check-contract-services.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Services failed to become healthy. Tearing down..."
    docker compose -f infra/compose/docker-compose.contract.yml down -v
    exit 1
}

Write-Host "3. Running Contract Tests..."
# First ensure we have the minimum number of tests
python scripts/ensure-pytest-collection.py tests/contract 330
if ($LASTEXITCODE -ne 0) {
    Write-Error "Test collection failed. Tearing down..."
    docker compose -f infra/compose/docker-compose.contract.yml down -v
    exit 1
}

# Run the actual tests
$env:CONTRACT_TEST_STRICT="1"
pytest tests/contract -v
$testExitCode = $LASTEXITCODE

Write-Host "4. Tearing down Infrastructure..."
docker compose -f infra/compose/docker-compose.contract.yml down -v

if ($testExitCode -ne 0) {
    Write-Error "Contract tests failed!"
    exit $testExitCode
}

Write-Host "Contract tests completed successfully!"
