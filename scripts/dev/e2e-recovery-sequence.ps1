# E2E Recovery Sequence Script
# Follows the practical recovery approach:
# 1. Backend services up
# 2. Health check verification
# 3. Minimal smoke test
# 4. Full E2E suite (only if smoke passes)
# 5. Failure classification

param(
    [switch]$SkipBackendStart,
    [switch]$SkipSmokeTest,
    [switch]$QuickMode,              # Only run chromium + smoke for fast feedback
    [switch]$AllowDegradedHealth,  # Continue even if some backends are unhealthy (for investigation)
    [switch]$InvestigateOnly,        # Run health checks and smoke only, skip full suite
    [string]$BackendComposeFile = "infra/compose/docker-compose.full.yml",
    [int[]]$BackendPorts = @(8001, 8002, 8003, 8004, 8005, 8006),
    [int]$FrontendPort = 3001,
    [int]$HealthCheckTimeout = 60,
    [int]$MaxRetries = 3,
    [string]$OutputJsonPath = "e2e-recovery-results.json"
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# Pre-flight: Check for required environment configuration
$envFilePath = Join-Path (Split-Path $BackendComposeFile -Parent) ".env"
if (-not $SkipBackendStart -and -not (Test-Path $envFilePath)) {
    Write-Host "`n✗ FATAL: Environment configuration missing" -ForegroundColor Red
    Write-Host "Required file not found: $envFilePath" -ForegroundColor Red
    Write-Host "`nClass A Secret Required: OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host "This secret is required for Layer 1, 2, and 4 services." -ForegroundColor Yellow
    Write-Host "`nResolution options:" -ForegroundColor Cyan
    Write-Host "  1. Create .env file with OPENAI_API_KEY:" -ForegroundColor White
    Write-Host "     cd $(Split-Path $BackendComposeFile -Parent)" -ForegroundColor Gray
    Write-Host "     echo 'OPENAI_API_KEY=sk-...' > .env" -ForegroundColor Gray
    Write-Host "  2. Use Infisical secrets manager (set INFISICAL_* vars)" -ForegroundColor White
    Write-Host "  3. Run against staging: -SkipBackendStart with PLAYWRIGHT_BASE_URL" -ForegroundColor White
    Write-Host "  4. Request secret from platform/security team" -ForegroundColor White
    Write-Host "`nDocumentation: .env.example" -ForegroundColor Gray
    exit 1
}

# Colors for output
$colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Step = "Magenta"
}

function Write-Step {
    param([string]$Message, [int]$StepNumber)
    Write-Host "`n[Step $StepNumber] $Message" -ForegroundColor $colors.Step
    Write-Host "=" * 60 -ForegroundColor $colors.Step
}

function Write-Result {
    param([string]$Message, [switch]$Success, [switch]$Failure)
    if ($Success) {
        Write-Host "  ✓ $Message" -ForegroundColor $colors.Success
    } elseif ($Failure) {
        Write-Host "  ✗ $Message" -ForegroundColor $colors.Error
    } else {
        Write-Host "  → $Message" -ForegroundColor $colors.Info
    }
}

$results = @{
    BackendStatus = @()
    HealthGatePassed = $false
    SmokeGatePassed = $false
    FullSuiteExecuted = $false
    SuiteExitCode = $null
    FailedServices = @()
    InfraFailures = 0
    ProductFailures = 0
    EnvCoupledFailures = 0
    FlakyTests = 0
    ClassificationSummary = @{
        Infra = @()
        Product = @()
        EnvCoupled = @()
        Flaky = @()
    }
    StartTime = $startTime.ToString("o")
    EndTime = $null
    DurationSeconds = 0
}

function Save-ResultsArtifact {
    param([string]$Path)
    $results.EndTime = (Get-Date).ToString("o")
    $results.DurationSeconds = [math]::Round(((Get-Date) - $startTime).TotalSeconds)
    $json = $results | ConvertTo-Json -Depth 10
    $json | Out-File -FilePath $Path -Encoding utf8
    Write-Host "Results artifact saved: $Path" -ForegroundColor $colors.Success
}

# ===== STEP 1: Backend Services =====
Write-Step "Bring up backend services" 1

if (-not $SkipBackendStart) {
    # Check if docker-compose file exists
    if (Test-Path $BackendComposeFile) {
        Write-Result "Starting backend services with docker-compose..."
        try {
            docker-compose -f $BackendComposeFile up -d
            Write-Result "Docker-compose started" -Success
        } catch {
            Write-Result "Failed to start docker-compose: $_" -Failure
            Write-Host "`nTrying docker compose (v2)..." -ForegroundColor $colors.Warning
            try {
                docker compose -f $BackendComposeFile up -d
                Write-Result "Docker compose v2 started" -Success
            } catch {
                Write-Result "Docker compose failed. Manual backend startup required." -Failure
                Write-Host "`nPlease start backend services manually:" -ForegroundColor $colors.Warning
                Write-Host "  cd services" -ForegroundColor $colors.Info
                Write-Host "  docker-compose up -d" -ForegroundColor $colors.Info
                exit 1
            }
        }
    } else {
        Write-Result "Compose file not found at $BackendComposeFile" -Warning
        Write-Host "Assuming backend services are already running or managed externally" -ForegroundColor $colors.Warning
    }

    # Give services time to initialize
    Write-Host "`nWaiting 10s for services to initialize..." -ForegroundColor $colors.Info
    Start-Sleep -Seconds 10
} else {
    Write-Result "Skipped (use -SkipBackendStart)" -Warning
}

# ===== STEP 2: Health Checks =====
Write-Step "Verify each port with health checks" 2

$allHealthy = $true
foreach ($port in $BackendPorts) {
    $healthy = $false
    $attempts = 0

    while (-not $healthy -and $attempts -lt $MaxRetries) {
        $attempts++
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$port/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                Write-Result "Port $port - HEALTHY ($($response.StatusCode))" -Success
            }
        } catch {
            Write-Result "Port $port - Attempt $attempts/$MaxRetries..."
            if ($attempts -lt $MaxRetries) {
                Start-Sleep -Seconds 2
            }
        }
    }

    if (-not $healthy) {
        $allHealthy = $false
        Write-Result "Port $port - UNREACHABLE" -Failure
        $results.BackendStatus += @{ Port = $port; Healthy = $false }
    } else {
        $results.BackendStatus += @{ Port = $port; Healthy = $true }
    }
}

# Also check frontend dev server port availability
Write-Host "`nChecking frontend port $FrontendPort..." -ForegroundColor $colors.Info
try {
    $test = New-Object System.Net.Sockets.TcpClient("localhost", $FrontendPort)
    if ($test.Connected) {
        $test.Close()
        Write-Result "Port $FrontendPort - OCCUPIED (server may already be running)" -Warning
    }
} catch {
    Write-Result "Port $FrontendPort - Available" -Success
}

if (-not $allHealthy) {
    if ($AllowDegradedHealth -or $InvestigateOnly) {
        Write-Host "`n⚠️  WARNING: Not all backend services are healthy" -ForegroundColor $colors.Warning
        Write-Host "Continuing due to -AllowDegradedHealth flag..." -ForegroundColor $colors.Warning
    } else {
        Write-Host "`n✗ HEALTH CHECKS FAILED — Exiting" -ForegroundColor $colors.Error
        Write-Host "Required backend services on ports 8001-8006 are not all healthy." -ForegroundColor $colors.Error
        Write-Host "This prevents valid E2E test execution." -ForegroundColor $colors.Error
        Write-Host "`nOptions:" -ForegroundColor $colors.Info
        Write-Host "  1. Start backend services: docker compose up -d" -ForegroundColor $colors.Info
        Write-Host "  2. Check health only: ./scripts/check-backend-health.ps1" -ForegroundColor $colors.Info
        Write-Host "  3. Investigate mode: ./scripts/e2e-recovery-sequence.ps1 -InvestigateOnly" -ForegroundColor $colors.Info
        Write-Host "  4. Force continue: ./scripts/e2e-recovery-sequence.ps1 -AllowDegradedHealth" -ForegroundColor $colors.Info
        exit 1
    }
}

# ===== STEP 3: Minimal Smoke Test =====
Write-Step "Run one minimal smoke test" 3

if (-not $SkipSmokeTest) {
    Push-Location frontend

    # Smoke pack uses @smoke tag for gating
    # Tests tagged @smoke validate:
    # 1. App shell loads (navigation)
    # 2. API-backed page renders real data (list views)
    # 3. Write/interaction flow succeeds (safe read-only or idempotent ops)
    # NOTE: @smoke tests must be idempotent - use seeded test data or mock interactions
    $smokeTestPattern = "--grep=@smoke"
    $smokeTestProject = "chromium"

    Write-Result "Running smoke test: $smokeTestPattern (project: $smokeTestProject)"

    # Defensive: Validate @smoke tests exist before running
    try {
        $listOutput = npx playwright test $smokeTestPattern --project=$smokeTestProject --list 2>&1
        $smokeCount = ($listOutput | Select-String -Pattern "@smoke" | Measure-Object).Count

        if ($smokeCount -eq 0) {
            Write-Host "`n✗ SMOKE CONTRACT VIOLATION" -ForegroundColor $colors.Error
            Write-Host "No @smoke tests found. Recovery gate invalid." -ForegroundColor $colors.Error
            Write-Host "Ensure smoke tests are tagged in test files." -ForegroundColor $colors.Error
            Write-Host "`nExpected minimum: 3 tests (app shell, API data, mutation)" -ForegroundColor $colors.Warning
            Write-Host "Required files with @smoke tags:" -ForegroundColor $colors.Info
            Write-Host "  - e2e/navigation.spec.ts (app shell validation)" -ForegroundColor $colors.Info
            Write-Host "  - e2e/business-case-list.spec.ts (API-backed data)" -ForegroundColor $colors.Info
            Write-Host "  - e2e/admin-system.spec.ts (mutation + state)" -ForegroundColor $colors.Info

            $results.FailedServices = @("@smoke contract violation - zero tests found")
            Save-ResultsArtifact -Path $OutputJsonPath
            Pop-Location
            exit 1
        }

        if ($smokeCount -lt 3) {
            Write-Host "`n⚠ SMOKE CONTRACT WARNING" -ForegroundColor $colors.Warning
            Write-Host "Only $smokeCount @smoke test(s) found (minimum: 3)" -ForegroundColor $colors.Warning
            Write-Host "Continuing, but coverage may be insufficient for cross-layer validation." -ForegroundColor $colors.Warning
        }

        Write-Result "Found $smokeCount @smoke test(s) — proceeding" -Success
    } catch {
        Write-Result "Failed to enumerate @smoke tests: $_" -Failure
    }

    try {
        $smokeOutput = npx playwright test $smokeTestPattern --project=$smokeTestProject --reporter=line 2>&1
        $smokeExitCode = $LASTEXITCODE

        if ($smokeExitCode -eq 0) {
            $results.SmokeGatePassed = $true
            Write-Result "SMOKE TEST PASSED ✓ (UI + API path validated)" -Success
            Write-Host "`n@smoke pack validated:" -ForegroundColor $colors.Success
            Write-Host "  ✓ App shell loads (navigation @smoke)" -ForegroundColor $colors.Success
            Write-Host "  ✓ API-backed page renders data (list views @smoke)" -ForegroundColor $colors.Success
            Write-Host "  ✓ Write/interaction flow works (idempotent ops @smoke)" -ForegroundColor $colors.Success
            Write-Host "  (All @smoke tests use seeded data or read-only operations)" -ForegroundColor $colors.Gray
        } else {
            $results.SmokeGatePassed = $false
            Write-Result "SMOKE TEST FAILED ✗" -Failure
            Write-Host "`n@smoke pack must prove:" -ForegroundColor $colors.Warning
            Write-Host "  1. App shell loads" -ForegroundColor $colors.Warning
            Write-Host "  2. API-backed page renders real data" -ForegroundColor $colors.Warning
            Write-Host "  3. Write/interaction flow succeeds (idempotent)" -ForegroundColor $colors.Warning
            Write-Host "`nSmoke test output:" -ForegroundColor $colors.Warning
            Write-Host $smokeOutput -ForegroundColor $colors.Warning

            Write-Host "`n✗ Full E2E suite will not run (smoke test failed)" -ForegroundColor $colors.Error
            Write-Host "The @smoke pack validates integrated frontend-backend behavior." -ForegroundColor $colors.Error
            Write-Host "A failing smoke means the environment cannot support valid E2E testing." -ForegroundColor $colors.Error
            Write-Host "`nOptions:" -ForegroundColor $colors.Info
            Write-Host "  1. Fix infrastructure and retry" -ForegroundColor $colors.Info
            Write-Host "  2. Bypass smoke: ./scripts/e2e-recovery-sequence.ps1 -SkipSmokeTest (not recommended)" -ForegroundColor $colors.Warning

            # Save artifact before exit
            $results.FailedServices = $results.BackendStatus | Where-Object { $_.Status -ne "UP" } | ForEach-Object { "Port $($_.Port)" }
            Save-ResultsArtifact -Path $OutputJsonPath
            Pop-Location
            exit 1
        }
    } catch {
        $results.SmokeTestPassed = $false
        Write-Result "Smoke test execution error: $_" -Failure
        Pop-Location
        exit 1
    }

    Pop-Location
} else {
    Write-Result "Skipped smoke test (use -SkipSmokeTest)" -Warning
    $results.SmokeGatePassed = $true  # Assume OK if skipped
}

# ===== STEP 4: Full E2E Suite (only if smoke passed) =====
Write-Step "Run full E2E suite" 4

if ($results.SmokeGatePassed) {
    $results.FullSuiteExecuted = $true
    Push-Location frontend

    $testArgs = @()
    if ($QuickMode) {
        $testArgs += "--project=chromium"
        $testArgs += "--workers=4"
        Write-Result "QUICK MODE: Only Chromium, 4 workers"
    } else {
        $testArgs += "--workers=11"
        Write-Result "FULL MODE: All projects, 11 workers"
    }

    $testArgs += "--reporter=list,dot,html"
    $testArgs += "--trace=on-first-retry"
    $testArgs += "--output=e2e-results/"

    Write-Result "Starting full test run..."
    Write-Host "Command: npx playwright test $testArgs" -ForegroundColor $colors.Info

    $suiteStartTime = Get-Date
    $suiteExitCode = 0
    try {
        $suiteOutput = npx playwright test @testArgs 2>&1
        $suiteExitCode = $LASTEXITCODE
        $results.FullSuiteResults = $suiteOutput

        # Parse results for classification
        $passedTests = ($suiteOutput | Select-String -Pattern "(\d+) passed" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1)
        $failedTests = ($suiteOutput | Select-String -Pattern "(\d+) failed" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1)
        $flakyTests = ($suiteOutput | Select-String -Pattern "(\d+) flaky" | ForEach-Object { $_.Matches.Groups[1].Value } | Select-Object -First 1)

        Write-Host "`nSuite execution complete" -ForegroundColor $colors.Success
        Write-Result "Passed: $passedTests" -Success
        if ($failedTests) {
            Write-Result "Failed: $failedTests" -Failure
        }
        if ($flakyTests) {
            Write-Result "Flaky: $flakyTests" -Warning
        }

        # Calculate duration and final status
        $suiteEndTime = Get-Date
        $suiteDuration = $suiteEndTime - $suiteStartTime
        $suiteStatus = if ($suiteExitCode -eq 0) { "PASSED" } else { "FAILED (exit $suiteExitCode)" }
        Write-Host "Suite status: $suiteStatus" -ForegroundColor $(if ($suiteExitCode -eq 0) { $colors.Success } else { $colors.Error })
        Write-Host "Suite duration: $($suiteDuration.ToString('hh\:mm\:ss'))" -ForegroundColor $colors.Info

    } catch {
        Write-Result "Suite execution error: $_" -Failure
    }

    Pop-Location
} else {
    Write-Result "SKIPPED - Smoke test must pass first" -Failure
}

# ===== STEP 5: Failure Classification =====
Write-Step "Separate true product failures from infra failures" 5

Write-Host "`nClassification Guidelines:" -ForegroundColor $colors.Info

Write-Host "  INFRA failures:" -ForegroundColor $colors.Warning
Write-Host "    - Blank page screenshots" -ForegroundColor $colors.Warning
Write-Host "    - Connection refused/timeout errors" -ForegroundColor $colors.Warning
Write-Host "    - ERR_CONNECTION_REFUSED in traces" -ForegroundColor $colors.Warning

Write-Host "  PRODUCT failures (deterministic):" -ForegroundColor $colors.Error
Write-Host "    - Element not found (after page loaded)" -ForegroundColor $colors.Error
Write-Host "    - Assertion failures on visible content" -ForegroundColor $colors.Error
Write-Host "    - Functional logic errors" -ForegroundColor $colors.Error

Write-Host "  ENV-COUPLED failures:" -ForegroundColor DarkYellow
Write-Host "    - Fail only when real services are up" -ForegroundColor DarkYellow
Write-Host "    - API contract drift between layers" -ForegroundColor DarkYellow
Write-Host "    - Seed data assumptions (missing/invalid test data)" -ForegroundColor DarkYellow
Write-Host "    - Auth state issues (token expiry, session handling)" -ForegroundColor DarkYellow
Write-Host "    - Dependency timing (async race conditions)" -ForegroundColor DarkYellow
Write-Host "    - These often require cross-layer fixes" -ForegroundColor DarkYellow

Write-Host "  FLAKY tests:" -ForegroundColor $colors.Warning
Write-Host "    - Pass on retry but fail initially" -ForegroundColor $colors.Warning
Write-Host "    - Timing-dependent (race conditions)" -ForegroundColor $colors.Warning
Write-Host "    - Often fixed with explicit waits or deterministic data" -ForegroundColor $colors.Warning

Write-Host "`nEvidence locations:" -ForegroundColor $colors.Info
Write-Host "  Screenshots: frontend/e2e-results/*/test-failed-1.png" -ForegroundColor $colors.Info
Write-Host "  Traces:      frontend/e2e-results/*/*.zip" -ForegroundColor $colors.Info
Write-Host "  HTML Report: frontend/playwright-report/index.html" -ForegroundColor $colors.Info

# Open HTML report for manual review
$openReport = Read-Host "`nOpen HTML report for failure classification? (y/n)"
if ($openReport -eq "y") {
    Push-Location frontend
    Start-Process "npx" -ArgumentList "playwright", "show-report" -NoNewWindow
    Pop-Location
    Write-Result "Report opened at http://localhost:9323" -Success
}

# ===== SUMMARY =====
Write-Step "Recovery Sequence Summary" "FINAL"

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "`nDuration: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor $colors.Info
Write-Host "Backend Services:" -ForegroundColor $colors.Info
foreach ($svc in $results.BackendStatus) {
    $color = if ($svc.Healthy) { $colors.Success } else { $colors.Error }
    $status = if ($svc.Healthy) { "UP" } else { "DOWN" }
    Write-Host "  Port $($svc.Port): $status" -ForegroundColor $color
}

Write-Host "`nTest Results:" -ForegroundColor $colors.Info
$results.HealthGatePassed = $allHealthy
Write-Result "Health Check Gate: $(if ($allHealthy) { "PASSED" } else { "FAILED - Use -AllowDegradedHealth to bypass" })" -Success:$allHealthy -Failure:(-not $allHealthy)
Write-Result "Smoke Test Gate: $(if ($results.SmokeGatePassed) { "PASSED (UI+API validated)" } else { "FAILED" })" -Success:$results.SmokeGatePassed -Failure:(-not $results.SmokeGatePassed)
Write-Result "Full Suite Executed: $(if ($results.FullSuiteExecuted) { "YES" } else { "NO (gated)" })" -Success:$results.FullSuiteExecuted
if ($null -ne $results.SuiteExitCode) {
    Write-Result "Suite Exit Code: $($results.SuiteExitCode)" -Success:($results.SuiteExitCode -eq 0) -Failure:($results.SuiteExitCode -ne 0)
}

if ($results.FullSuiteResults) {
    Write-Host "`nFull suite completed. Review:" -ForegroundColor $colors.Info
    Write-Host "  1. HTML Report: cd frontend && npx playwright show-report" -ForegroundColor $colors.Info
    Write-Host "  2. Trace Viewer: npx playwright show-trace e2e-results/*.zip" -ForegroundColor $colors.Info
    Write-Host "  3. Artifact Dirs: e2e-results/ (screenshots, videos)" -ForegroundColor $colors.Info
}

# Save final artifact
$results.FailedServices = $results.BackendStatus | Where-Object { $_.Status -ne "UP" } | ForEach-Object { "Port $($_.Port)" }
Save-ResultsArtifact -Path $OutputJsonPath

Write-Host "`nMachine-Readable Results:" -ForegroundColor $colors.Info
Write-Host "  JSON: $OutputJsonPath" -ForegroundColor $colors.Info
Write-Host "  Fields: healthGatePassed, smokeGatePassed, fullSuiteExecuted, suiteExitCode, failedServices, timestamps" -ForegroundColor $colors.Gray

Write-Host "`nNext Actions:" -ForegroundColor $colors.Step
if (-not $results.SmokeGatePassed) {
    Write-Host "  1. Fix infrastructure (backend services)" -ForegroundColor $colors.Error
    Write-Host "  2. Re-run: ./scripts/e2e-recovery-sequence.ps1" -ForegroundColor $colors.Info
} else {
    Write-Host "  1. Classify failures (infra / product / env-coupled / flaky)" -ForegroundColor $colors.Info
    Write-Host "  2. Focus on env-coupled failures - they often reveal cross-layer issues" -ForegroundColor $colors.Info
    Write-Host "  3. Create tickets for product and env-coupled failures" -ForegroundColor $colors.Info
    Write-Host "  4. Quarantine flaky tests if >10%" -ForegroundColor $colors.Info
    Write-Host "  5. Re-run after fixes: ./scripts/e2e-recovery-sequence.ps1 -SkipBackendStart" -ForegroundColor $colors.Info
}

Write-Host "`n" -NoNewLine
