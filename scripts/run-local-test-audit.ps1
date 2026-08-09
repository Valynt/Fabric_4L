$ErrorActionPreference = "Stop"

Write-Host "==========================================================="
Write-Host "Fabric_4L Local Test Audit"
Write-Host "==========================================================="

Write-Host "1. Checking Pytest Collections..."
python scripts/ensure-pytest-collection.py tests/contract 330
python scripts/ensure-pytest-collection.py tests/security 600
python scripts/ensure-pytest-collection.py tests/k8s 150

Write-Host "2. Running Security Tests..."
pytest tests/security -v

Write-Host "3. Running K8s Tests..."
pytest tests/k8s -v

Write-Host "4. Running Contract Tests (with infra)..."
powershell -ExecutionPolicy Bypass -File scripts/run-openapi-contract-tests.ps1

Write-Host "==========================================================="
Write-Host "Local Test Audit completed successfully!"
Write-Host "==========================================================="
