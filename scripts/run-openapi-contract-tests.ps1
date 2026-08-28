$ErrorActionPreference = "Stop"
$ComposeFile = "infra/compose/docker-compose.backend-integrated.yml"
$Succeeded = $false

Write-Host "==========================================================="
Write-Host "Fabric_4L Contract Tests Runner"
Write-Host "==========================================================="

Write-Host "1. Validating static contracts..."
python scripts/ensure-pytest-collection.py --dir tests/contract --min-tests 330
if ($LASTEXITCODE -ne 0) { throw "Contract test collection failed." }
pytest tests/contract -m "contract_static or contract_static_no_service" -v
if ($LASTEXITCODE -ne 0) { throw "Static contract tests failed." }

try {
    Write-Host "2. Bringing up the real L1-L6 contract stack..."
    docker compose -f $ComposeFile up --build -d
    if ($LASTEXITCODE -ne 0) { throw "Contract stack startup failed." }

    Write-Host "3. Waiting for L1-L6 services to be healthy..."
    python scripts/check-contract-services.py
    if ($LASTEXITCODE -ne 0) { throw "Contract services failed to become healthy." }

    Write-Host "4. Running live cross-layer and OpenAPI contracts..."
    $env:CONTRACT_TEST_STRICT = "1"
    $env:RUN_RUNTIME_CONTRACTS = "1"
    $env:L1_URL = "http://localhost:8001"
    $env:L2_URL = "http://localhost:8002"
    $env:L3_URL = "http://localhost:8003"
    $env:L4_URL = "http://localhost:8004"
    $env:LAYER1_API_URL = "http://localhost:8001"
    $env:LAYER2_API_URL = "http://localhost:8002"
    $env:LAYER3_API_URL = "http://localhost:8003"
    $env:LAYER4_API_URL = "http://localhost:8004"
    $env:LAYER5_API_URL = "http://localhost:8005"
    $env:LAYER6_API_URL = "http://localhost:8006"
    $env:SERVICE_AUTH_SECRET = "dev-local-service-auth-secret-do-not-use-in-production-32c"
    $env:RUNTIME_CONTRACT_TENANT_ID = "00000000-0000-4000-8000-000000000001"
    pytest `
        tests/contract/test_layer_integration.py `
        tests/contract/test_layer_service_entrypoint_smoke.py `
        tests/contract/test_l3_route_alias_parity.py `
        -v
    if ($LASTEXITCODE -ne 0) { throw "Live contract tests failed." }
    $Succeeded = $true
}
finally {
    if (-not $Succeeded) {
        Write-Host "Contract stack diagnostics:"
        docker compose -f $ComposeFile ps --all
        docker compose -f $ComposeFile logs --no-color
    }
    docker compose -f $ComposeFile down -v
}

Write-Host "Contract tests completed successfully."
