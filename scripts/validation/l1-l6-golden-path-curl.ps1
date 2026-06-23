# L1-L6 golden-path API scenario
# Exercises the full Fabric_4L value-engine pipeline via Invoke-RestMethod/curl.
# Source: .windsurf/plans/l1-l6-api-curl-scenario-b653b2.md

param(
    [string]$L1 = $env:LAYER1_API_URL ? $env:LAYER1_API_URL : "http://localhost:8001",
    [string]$L2 = $env:LAYER2_API_URL ? $env:LAYER2_API_URL : "http://localhost:8002",
    [string]$L3 = $env:LAYER3_API_URL ? $env:LAYER3_API_URL : "http://localhost:8003",
    [string]$L4 = $env:LAYER4_API_URL ? $env:LAYER4_API_URL : "http://localhost:8004",
    [string]$L5 = $env:LAYER5_API_URL ? $env:LAYER5_API_URL : "http://localhost:8005",
    [string]$L6 = $env:LAYER6_API_URL ? $env:LAYER6_API_URL : "http://localhost:8006",
    [string]$TenantId = $env:FABRIC_TENANT_ID ? $env:FABRIC_TENANT_ID : "tenant-00000000-0000-4000-8000-000000000001",
    [string]$UserId = $env:FABRIC_USER_ID ? $env:FABRIC_USER_ID : "user-backend-validation",
    [string]$Role = $env:FABRIC_ROLE ? $env:FABRIC_ROLE : "super_admin",
    [string]$ServiceAuth = $env:SERVICE_AUTH_SECRET ? $env:SERVICE_AUTH_SECRET : "dev-local-service-auth-secret-do-not-use-in-production-32c",
    [string]$RunId = $env:BACKEND_VALIDATION_RUN_ID ? $env:BACKEND_VALIDATION_RUN_ID : ("curl-l1-l6-" + ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()))
)

$AccountId = "acme-$RunId"
$DocumentId = "doc-$RunId"
$EvidenceId = "ev-$RunId"
$FormulaId = "formula-$RunId"
$BenchmarkId = "bench-$RunId"

function Headers {
    return @{
        "Content-Type" = "application/json"
        "X-Tenant-ID" = $TenantId
        "X-User-ID" = $UserId
        "X-Role" = $Role
        "X-Organization-ID" = $TenantId
        "X-Org-ID" = $TenantId
        "X-Service-Auth" = $ServiceAuth
        "X-Dev-Tenant-ID" = $TenantId
        "X-Dev-User-ID" = $UserId
        "X-Validation-Run-ID" = $RunId
    }
}

function ApiCall($Method, $Uri, $Body) {
    if ($Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers (Headers) -Body $Body -ContentType "application/json"
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers (Headers)
}

Write-Host "=== L1-L6 Golden Path API Scenario ==="
Write-Host "Run ID: $RunId"
Write-Host "Tenant: $TenantId"
Write-Host "Account: $AccountId"
Write-Host "Document: $DocumentId"
Write-Host ""

Write-Host "=== L1: Ingest source ==="
# Canonical unified source intake (Notes / Web / Audio / CRM / PDF / Meeting).
# Synchronous response only confirms acceptance; downstream layers process async.
$source = ApiCall POST "$L1/api/v1/ingestion/sources" (ConvertTo-Json -Depth 4 @{
    account_id = $AccountId
    source_type = "notes"
    title = "Acme Validation Discovery Notes — $RunId"
    content = "Pipeline conversion improved 11 percent after guided value discovery."
    external_reference = $DocumentId
    idempotency_key = $DocumentId
    requested_outputs = @("fabric_found_summary")
})
$source | ConvertTo-Json -Depth 4
$sourceId = $source.source_id ? $source.source_id : $null
$runIdL1 = $source.ingestion_run_id ? $source.ingestion_run_id : $null

if ($runIdL1) {
    Write-Host "=== L1: Poll ingestion run (best effort) ==="
    for ($i = 0; $i -lt 5; $i++) {
        $run = ApiCall GET "$L1/api/v1/ingestion/runs/$runIdL1"
        $run | ConvertTo-Json -Depth 4
        $status = ($run.status ? $run.status : "").ToString().ToLower()
        if ($status -match "ready|failed|cancelled|needs_input|needs_review") { break }
        Start-Sleep -Seconds 1
    }
}
Write-Host ""

Write-Host "=== L2: Extraction ==="
$extraction = ApiCall POST "$L2/api/v1/extractions" (ConvertTo-Json -Depth 4 @{
    source_id = $DocumentId
    account_id = $AccountId
    mode = "curl_l1_l6"
})
$extraction | ConvertTo-Json -Depth 4
$extractionId = $extraction.id ? $extraction.id : ($extraction.extraction_id ? $extraction.extraction_id : $DocumentId)

Write-Host "Signals:"
ApiCall GET "$L2/api/v1/extractions/${extractionId}/signals" | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L3: Knowledge Graph ==="
$graph = ApiCall POST "$L3/api/v1/graph/context" (ConvertTo-Json -Depth 4 @{
    account_id = $AccountId
    source_ids = @($DocumentId)
    signal_ids = @($extractionId)
    evidence_ids = @($EvidenceId)
})
$graph | ConvertTo-Json -Depth 4
$graphId = $graph.id ? $graph.id : ($graph.graph_id ? $graph.graph_id : $AccountId)
Write-Host ""

Write-Host "=== L4: Hypothesis ==="
ApiCall POST "$L4/v1/hypotheses" (ConvertTo-Json -Depth 4 @{
    account_id = $AccountId
    graph_context_id = $graphId
    require_evidence = $true
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L4: ROI Analysis ==="
ApiCall POST "$L4/v1/analysis/roi" (ConvertTo-Json -Depth 4 @{
    account_id = $AccountId
    formula_id = $FormulaId
    variables = @{
        annual_revenue = 10000000
        conversion_lift_pct = 11
        implementation_cost = 125000
    }
    scenarios = @("conservative", "expected", "optimistic")
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L4: Business Case ==="
$case = ApiCall POST "$L4/v1/cases" (ConvertTo-Json -Depth 4 @{
    account_id = $AccountId
    evidence_ids = @($EvidenceId)
    approval_status = "submitted"
})
$case | ConvertTo-Json -Depth 4
$caseId = $case.id ? $case.id : $case.case_id
Write-Host ""

Write-Host "=== L4: Approval ==="
ApiCall POST "$L4/v1/cases/${caseId}/approval" (ConvertTo-Json -Depth 4 @{
    status = "approved"
    reviewer_id = $UserId
    decision = "approve"
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L4: Export ==="
ApiCall GET "$L4/v1/cases/${caseId}/export" | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L4: Traceability ==="
ApiCall GET "$L4/v1/cases/${caseId}/traceability?include_raw_sources=true" | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L5: Ground Truth Assumption ==="
ApiCall POST "$L5/api/v1/truth/assumptions" (ConvertTo-Json -Depth 4 @{
    id = $EvidenceId
    account_id = $AccountId
    claim = "Conversion improved 11 percent"
    source_id = $DocumentId
    status = "pending_review"
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L5: Assumption Decision ==="
ApiCall POST "$L5/api/v1/truth/assumptions/${EvidenceId}/decisions" (ConvertTo-Json -Depth 4 @{
    status = "approved"
    reviewer_id = $UserId
    reason = "source verified"
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L6: Benchmark ==="
ApiCall POST "$L6/v1/benchmarks" (ConvertTo-Json -Depth 4 @{
    id = $BenchmarkId
    metric = "conversion_lift_pct"
    value = 11
    source = "curl_l1_l6"
    effective_date = "2024-01-01"
    account_id = $AccountId
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== L6: Benchmark Policy ==="
ApiCall POST "$L6/v1/benchmarks/policy/evaluate" (ConvertTo-Json -Depth 4 @{
    benchmark_id = $BenchmarkId
    formula_id = $FormulaId
    account_id = $AccountId
}) | ConvertTo-Json -Depth 4
Write-Host ""

Write-Host "=== Scenario complete ==="
Write-Host "Run ID: $RunId"
Write-Host "Account ID: $AccountId"
Write-Host "Case ID: $caseId"
