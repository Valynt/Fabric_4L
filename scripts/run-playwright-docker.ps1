<#
.SYNOPSIS
    Run Playwright E2E tests inside Docker for the Value Fabric frontend.

.DESCRIPTION
    Builds and runs the Playwright test container with live source mounting.
    Supports headless, headed, and Playwright UI mode on Windows hosts.
    The -Live switch targets the separately-running Docker-hosted frontend
    from infra/compose/docker-compose.live.yml instead of starting a new frontend server.

.PARAMETER Build
    Build or rebuild the Docker image. Do this after changing dependencies.

.PARAMETER TestProject
    Playwright project to run (contracts, journeys, backend-integrated, etc.).
    Default: contracts. Ignored when -Live is used (live mode runs the
    backend-integrated suite via pnpm run test:e2e:live).

.PARAMETER UiMode
    Launch Playwright UI mode (interactive web UI on http://localhost:9323).

.PARAMETER Headed
    Run tests in headed mode (requires X11/VNC; limited support on Windows Docker).
    Most users should use -UiMode instead for interactive debugging.

.PARAMETER BackendUrl
    URL of the backend API for backend-integrated tests.
    Example: http://host.docker.internal:8004
    Ignored when -Live is used (live mode uses http://layer4:8000 internally).

.PARAMETER FrontendUrl
    URL of the frontend under test.
    Default: http://localhost:3001
    Ignored when -Live is used (live mode uses http://frontend:3001 internally).

.PARAMETER ExtraArgs
    Additional arguments passed to the Playwright CLI.

.PARAMETER Live
    Run tests against the live Docker-hosted frontend from infra/compose/docker-compose.live.yml.
    Requires the live stack to be running. Sets mocks to false and uses internal
    Docker network addresses (frontend:3001, layer4:8000).

.PARAMETER P0
    When used with -Live, run the P0 validation subset (test:e2e:live:p0)
    instead of the full live suite.

.PARAMETER GoldenPath
    When used with -Live, run the golden-path validation subset
    (test:e2e:live:golden-path).

.EXAMPLE
    .\scripts\run-playwright-docker.ps1 -Build

.EXAMPLE
    .\scripts\run-playwright-docker.ps1 -TestProject contracts

.EXAMPLE
    .\scripts\run-playwright-docker.ps1 -TestProject backend-integrated -BackendUrl http://host.docker.internal:8004

.EXAMPLE
    .\scripts\run-playwright-docker.ps1 -TestProject contracts -UiMode

.EXAMPLE
    # Run full live validation against the Docker-hosted frontend
    .\scripts\run-playwright-docker.ps1 -Live

.EXAMPLE
    # Run P0 live validation against the Docker-hosted frontend
    .\scripts\run-playwright-docker.ps1 -Live -P0

.EXAMPLE
    # Interactive UI mode against the live Docker-hosted frontend
    .\scripts\run-playwright-docker.ps1 -Live -UiMode
#>
param(
    [switch]$Build,
    [string]$TestProject = "contracts",
    [switch]$UiMode,
    [switch]$Headed,
    [string]$BackendUrl = "",
    [string]$FrontendUrl = "",
    [string]$ExtraArgs = "",
    [switch]$Live,
    [switch]$P0,
    [switch]$GoldenPath
)

$ErrorActionPreference = "Stop"

# Determine compose file and container name based on mode
if ($Live) {
    $ComposeFile = [System.IO.Path]::Combine($PSScriptRoot, "..", "infra", "compose", "docker-compose.playwright-live.yml")
    $ContainerName = "vf-playwright-live"
} else {
    $ComposeFile = [System.IO.Path]::Combine($PSScriptRoot, "..", "infra", "compose", "docker-compose.playwright.yml")
    $ContainerName = "vf-playwright"
}

# Verify Docker Desktop is responsive
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker does not appear to be running. Please start Docker Desktop and try again."
    exit 1
}

# Build image if requested
if ($Build) {
    Write-Host "=== Building Playwright Docker image ===" -ForegroundColor Cyan
    docker compose -f $ComposeFile build playwright
    Write-Host "=== Build complete ===" -ForegroundColor Green
    return
}

# Live mode: verify the live stack is running and healthy
if ($Live) {
    Write-Host "=== Live mode: verifying infra/compose/docker-compose.live.yml stack ===" -ForegroundColor Cyan

    $frontendContainer = docker ps --filter "name=vf-live-frontend" --format "{{.Names}}" 2>$null
    if (-not $frontendContainer) {
        Write-Error "Live frontend container (vf-live-frontend) is not running.`nPlease start the live stack first:`n  docker compose -f infra/compose/docker-compose.live.yml up -d --wait"
        exit 1
    }

    $frontendHealth = docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $frontendContainer 2>$null
    if ($frontendHealth -ne "healthy" -and $frontendHealth -ne "running") {
        Write-Error "Live frontend container is not healthy (state: $frontendHealth).`nPlease wait for the stack to become healthy:`n  docker compose -f infra/compose/docker-compose.live.yml ps`n  docker compose -f infra/compose/docker-compose.live.yml logs -f frontend"
        exit 1
    }

    $liveNetwork = docker network ls --filter "name=live-network" --format "{{.Name}}" 2>$null
    if (-not $liveNetwork) {
        Write-Error "Docker network 'live-network' does not exist.`nPlease start the live stack first:`n  docker compose -f infra/compose/docker-compose.live.yml up -d --wait"
        exit 1
    }

    Write-Host "Live stack verified: vf-live-frontend is $frontendHealth on live-network" -ForegroundColor Green
    Write-Host ""
}

# Prepare environment variables for docker compose
if ($Live) {
    $env:PLAYWRIGHT_BASE_URL = "http://frontend:3001"
    $env:PLAYWRIGHT_LIVE_FRONTEND_URL = "http://frontend:3001"
    $env:PLAYWRIGHT_BACKEND_URL = "http://layer4:8000"
    $env:PLAYWRIGHT_LIVE_MODE = "true"
} else {
    $env:PLAYWRIGHT_BASE_URL = if ($FrontendUrl) { $FrontendUrl } else { "http://localhost:3001" }
    if ($BackendUrl) { $env:PLAYWRIGHT_BACKEND_URL = $BackendUrl }
}

# Construct the command to run inside the container
if ($Live) {
    if ($P0) {
        $PlaywrightCmd = "pnpm run test:e2e:live:p0"
    } elseif ($GoldenPath) {
        $PlaywrightCmd = "pnpm run test:e2e:live:golden-path"
    } else {
        $PlaywrightCmd = "pnpm run test:e2e:live"
    }
    if ($UiMode) {
        $PlaywrightCmd += " --ui-host=0.0.0.0 --ui-port=9323"
    } elseif ($Headed) {
        $PlaywrightCmd += " --headed"
    }
} else {
    $PlaywrightCmd = "pnpm exec playwright test --project=$TestProject"
    if ($UiMode) {
        $PlaywrightCmd += " --ui-host=0.0.0.0 --ui-port=9323"
    } elseif ($Headed) {
        $PlaywrightCmd += " --headed"
    }
}

if ($ExtraArgs) {
    $PlaywrightCmd += " $ExtraArgs"
}

Write-Host ""
Write-Host "=== Running Playwright in Docker ===" -ForegroundColor Cyan
if ($Live) {
    Write-Host "Mode       : LIVE (Docker-hosted frontend)"
    Write-Host "Frontend   : http://frontend:3001 (vf-live-frontend on live-network)"
    Write-Host "Backend    : http://layer4:8000"
} else {
    Write-Host "Project    : $TestProject"
    Write-Host "Frontend   : $($env:PLAYWRIGHT_BASE_URL)"
    if ($BackendUrl) { Write-Host "Backend    : $BackendUrl" }
}
Write-Host "Command    : $PlaywrightCmd"
Write-Host ""

# Run the container (--service-ports exposes compose ports for UI mode)
docker compose -f $ComposeFile run --rm --service-ports playwright sh -c "$PlaywrightCmd"

$ExitCode = $LASTEXITCODE

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "=== Tests passed ===" -ForegroundColor Green
} else {
    Write-Host "=== Tests failed (exit code $ExitCode) ===" -ForegroundColor Red
}

# Print result locations
$ReportPath = [System.IO.Path]::Combine($PSScriptRoot, "..", "playwright-report", "index.html")
$JunitPath  = [System.IO.Path]::Combine($PSScriptRoot, "..", "e2e-results", "junit.xml")

Write-Host ""
Write-Host "Results:" -ForegroundColor Cyan
if (Test-Path $ReportPath) {
    Write-Host "  HTML Report : $ReportPath"
}
if (Test-Path $JunitPath) {
    Write-Host "  JUnit XML   : $JunitPath"
}
Write-Host ""

exit $ExitCode
