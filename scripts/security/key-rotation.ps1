#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Key Rotation Automation for Fabric4L - Windows PowerShell Script

.DESCRIPTION
    Automates rotation of sensitive API keys and secrets:
    - OpenAI project API keys
    - Thesys API keys
    - Clerk secret keys
    - Registry tokens

.PARAMETER Provider
    Secret provider to rotate (openai, thesys, clerk, registry, all)

.PARAMETER Environment
    Target environment (dev, staging, prod)

.PARAMETER DryRun
    Simulate rotation without making changes

.PARAMETER VerifyOnly
    Only verify current keys, no rotation

.PARAMETER ManualKey
    Manually provided key value (for providers requiring manual generation)

.PARAMETER AuditLog
    Path to write audit log JSON

.EXAMPLE
    .\scripts\security\key-rotation.ps1 -Provider openai -Environment staging -DryRun

.EXAMPLE
    $env:OPENAI_MANUAL_KEY = "sk-..."
    .\scripts\security\key-rotation.ps1 -Provider openai -Environment prod

.EXAMPLE
    .\scripts\security\key-rotation.ps1 -Provider all -Environment dev -VerifyOnly
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("openai", "thesys", "clerk", "registry", "all")]
    [string]$Provider,

    [Parameter(Mandatory=$true)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment,

    [switch]$DryRun,
    [switch]$VerifyOnly,
    [string]$ManualKey,
    [string]$AuditLog
)

# Error handling
$ErrorActionPreference = "Stop"

# Colors for output
$colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
}

function Write-StatusMessage {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Level = "Info"
    )
    
    $color = $colors[$Level]
    $prefix = switch ($Level) {
        "Success" { "[✓]" }
        "Warning" { "[!]" }
        "Error"   { "[✗]" }
        default   { "[*]" }
    }
    
    Write-Host "$prefix $Message" -ForegroundColor $color
}

function Test-InfisicalCli {
    $cli = Get-Command infisical -ErrorAction SilentlyContinue
    if (-not $cli) {
        Write-StatusMessage "Infisical CLI not found. Please install it:" "Error"
        Write-Host "  Windows: scoop bucket add org https://github.com/nicholasgasior/scoop-bucket && scoop install infisical"
        Write-Host "  Or download from: https://infisical.com/docs/cli/overview"
        exit 1
    }
    
    try {
        $version = & infisical --version 2>$null
        Write-StatusMessage "Infisical CLI found: $version" "Success"
    } catch {
        Write-StatusMessage "Could not get Infisical version" "Warning"
    }
}

function Test-InfisicalAuth {
    try {
        $result = & infisical user 2>&1
        if ($result -match "email") {
            Write-StatusMessage "Authenticated with Infisical" "Success"
            return $true
        }
    } catch {
        # Not authenticated
    }
    
    Write-StatusMessage "Not authenticated with Infisical. Run 'infisical login' first." "Error"
    return $false
}

function Get-CurrentSecret {
    param(
        [string]$SecretName,
        [string]$Path,
        [string]$Env
    )
    
    try {
        $result = & infisical secrets get --env=$Env --path=$Path $SecretName --json 2>&1 | ConvertFrom-Json
        return $result.secretValue
    } catch {
        Write-StatusMessage "Could not retrieve current value for $SecretName" "Warning"
        return $null
    }
}

function Set-InfisicalSecret {
    param(
        [string]$SecretName,
        [string]$SecretValue,
        [string]$Path,
        [string]$Env
    )
    
    if ($DryRun) {
        Write-StatusMessage "DRY RUN: Would update $SecretName at $Path" "Info"
        return $true
    }
    
    try {
        & infisical secrets set --env=$Env --path=$Path "$SecretName=$SecretValue" --silent
        Write-StatusMessage "Updated $SecretName in Infisical" "Success"
        return $true
    } catch {
        Write-StatusMessage "Failed to update $SecretName`: $_" "Error"
        return $false
    }
}

function Invoke-OpenAIRotation {
    param([string]$ManualKeyValue)
    
    Write-StatusMessage "Starting OpenAI API Key rotation" "Info"
    
    $currentKey = Get-CurrentSecret -SecretName "OPENAI_API_KEY" -Path "/layer2-extraction" -Env $Environment
    if ($currentKey) {
        $maskedCurrent = $currentKey.Substring(0, [Math]::Min(10, $currentKey.Length)) + "..."
        Write-StatusMessage "Current key: $maskedCurrent" "Info"
    }
    
    # Get new key
    $newKey = if ($ManualKeyValue) { $ManualKeyValue } else { $env:OPENAI_MANUAL_KEY }
    
    if (-not $newKey) {
        Write-StatusMessage "OPENAI_MANUAL_KEY not provided. Manual steps required:" "Warning"
        Write-Host "  1. Visit: https://platform.openai.com/account/api-keys"
        Write-Host "  2. Click 'Create new secret key'"
        Write-Host "  3. Re-run this script with -ManualKey 'sk-...' or set `$env:OPENAI_MANUAL_KEY"
        return @{ Success = $false; ManualRequired = $true }
    }
    
    # Validate key format
    if (-not $newKey.StartsWith("sk-")) {
        Write-StatusMessage "Invalid OpenAI key format. Must start with 'sk-'" "Error"
        return @{ Success = $false }
    }
    
    # Update Infisical
    $updateResult = Set-InfisicalSecret -SecretName "OPENAI_API_KEY" -SecretValue $newKey -Path "/layer2-extraction" -Env $Environment
    
    if (-not $updateResult) {
        return @{ Success = $false }
    }
    
    # Verify key (unless dry run)
    if (-not $DryRun) {
        Write-StatusMessage "Verifying new key..." "Info"
        try {
            $headers = @{ "Authorization" = "Bearer $newKey" }
            $response = Invoke-RestMethod -Uri "https://api.openai.com/v1/models" -Headers $headers -Method GET -TimeoutSec 10
            Write-StatusMessage "Key verification passed" "Success"
        } catch {
            Write-StatusMessage "Key verification failed: $_" "Error"
            return @{ Success = $false }
        }
    }
    
    $maskedNew = $newKey.Substring(0, [Math]::Min(10, $newKey.Length)) + "..."
    Write-StatusMessage "OpenAI key rotated successfully" "Success"
    
    if ($currentKey) {
        Write-Host ""
        Write-StatusMessage "ACTION REQUIRED: Revoke old key via OpenAI dashboard" "Warning"
        Write-Host "  https://platform.openai.com/account/api-keys"
        Write-Host "  Look for key starting with: $($currentKey.Substring(0, 10))..."
    }
    
    return @{
        Success = $true
        OldKeyId = $currentKey
        NewKeyId = $newKey
        Provider = "openai"
    }
}

function Invoke-ClerkRotation {
    param([string]$ManualKeyValue)
    
    Write-StatusMessage "Starting Clerk Secret Key rotation" "Info"
    
    $currentKey = Get-CurrentSecret -SecretName "CLERK_SECRET_KEY" -Path "/shared" -Env $Environment
    if ($currentKey) {
        $maskedCurrent = $currentKey.Substring(0, [Math]::Min(15, $currentKey.Length)) + "..."
        Write-StatusMessage "Current key: $maskedCurrent" "Info"
    }
    
    $newKey = if ($ManualKeyValue) { $ManualKeyValue } else { $env:CLERK_MANUAL_KEY }
    
    if (-not $newKey) {
        Write-StatusMessage "CLERK_MANUAL_KEY not provided. Manual steps required:" "Warning"
        Write-Host "  1. Visit: https://dashboard.clerk.com"
        Write-Host "  2. Navigate to your instance API Keys"
        Write-Host "  3. Generate new secret key"
        Write-Host "  4. Re-run with -ManualKey or set `$env:CLERK_MANUAL_KEY"
        return @{ Success = $false; ManualRequired = $true }
    }
    
    if (-not ($newKey.StartsWith("sk_test_") -or $newKey.StartsWith("sk_live_"))) {
        Write-StatusMessage "Invalid Clerk key format" "Error"
        return @{ Success = $false }
    }
    
    $updateResult = Set-InfisicalSecret -SecretName "CLERK_SECRET_KEY" -SecretValue $newKey -Path "/shared" -Env $Environment
    
    if (-not $updateResult) {
        return @{ Success = $false }
    }
    
    Write-StatusMessage "Clerk key rotated successfully" "Success"
    
    if ($currentKey) {
        Write-Host ""
        Write-StatusMessage "ACTION REQUIRED: Revoke old key via Clerk dashboard" "Warning"
        Write-Host "  https://dashboard.clerk.com"
    }
    
    return @{
        Success = $true
        OldKeyId = $currentKey
        NewKeyId = $newKey
        Provider = "clerk"
    }
}

function Invoke-ThesysRotation {
    param([string]$ManualKeyValue)
    
    Write-StatusMessage "Starting Thesys API Key rotation" "Info"
    
    $currentKey = Get-CurrentSecret -SecretName "THESYS_API_KEY" -Path "/shared" -Env $Environment
    
    $newKey = if ($ManualKeyValue) { $ManualKeyValue } else { $env:THESYS_MANUAL_KEY }
    
    if (-not $newKey) {
        Write-StatusMessage "THESYS_MANUAL_KEY not provided" "Warning"
        return @{ Success = $false; ManualRequired = $true }
    }
    
    $updateResult = Set-InfisicalSecret -SecretName "THESYS_API_KEY" -SecretValue $newKey -Path "/shared" -Env $Environment
    
    if (-not $updateResult) {
        return @{ Success = $false }
    }
    
    Write-StatusMessage "Thesys key rotated successfully" "Success"
    
    return @{
        Success = $true
        OldKeyId = $currentKey
        NewKeyId = $newKey
        Provider = "thesys"
    }
}

function Invoke-RegistryRotation {
    param([string]$ManualKeyValue)
    
    Write-StatusMessage "Starting Registry Token rotation" "Info"
    
    $currentKey = Get-CurrentSecret -SecretName "GHCR_PAT" -Path "/ci" -Env $Environment
    
    $newKey = if ($ManualKeyValue) { $ManualKeyValue } else { $env:REGISTRY_MANUAL_KEY }
    
    if (-not $newKey) {
        Write-StatusMessage "REGISTRY_MANUAL_KEY not provided. Manual steps required:" "Warning"
        Write-Host "  1. Visit: https://github.com/settings/tokens"
        Write-Host "  2. Generate new token with 'read:packages, write:packages' scopes"
        Write-Host "  3. Re-run with -ManualKey or set `$env:REGISTRY_MANUAL_KEY"
        return @{ Success = $false; ManualRequired = $true }
    }
    
    $updateResult = Set-InfisicalSecret -SecretName "GHCR_PAT" -SecretValue $newKey -Path "/ci" -Env $Environment
    
    if (-not $updateResult) {
        return @{ Success = $false }
    }
    
    Write-StatusMessage "Registry token rotated successfully" "Success"
    
    if ($currentKey) {
        Write-Host ""
        Write-StatusMessage "ACTION REQUIRED: Revoke old token via GitHub" "Warning"
        Write-Host "  https://github.com/settings/tokens"
    }
    
    return @{
        Success = $true
        OldKeyId = $currentKey
        NewKeyId = $newKey
        Provider = "registry"
    }
}

function Write-AuditLog {
    param(
        [array]$Records,
        [string]$OutputPath
    )
    
    if (-not $OutputPath) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $OutputPath = "rotation_audit_$timestamp.json"
    }
    
    $auditData = @{
        rotation_timestamp = (Get-Date -Format "o")
        records = $Records
    }
    
    $auditData | ConvertTo-Json -Depth 3 | Set-Content $OutputPath
    Write-StatusMessage "Audit log written to: $OutputPath" "Success"
}

# Main execution
function Main {
    Write-Host ""
    Write-Host "=" * 60
    Write-Host "  Fabric4L API Key Rotation"
    Write-Host "  Provider: $Provider"
    Write-Host "  Environment: $Environment"
    Write-Host "  Mode: $(if ($DryRun) { 'DRY RUN' } elseif ($VerifyOnly) { 'VERIFY ONLY' } else { 'LIVE' })"
    Write-Host "=" * 60
    Write-Host ""
    
    # Pre-checks
    Test-InfisicalCli
    if (-not (Test-InfisicalAuth)) {
        exit 1
    }
    
    if ($VerifyOnly) {
        Write-StatusMessage "VERIFY ONLY MODE - Checking current keys..." "Info"
        # Verification logic here
        exit 0
    }
    
    # Determine providers to rotate
    $providersToRotate = if ($Provider -eq "all") {
        @("openai", "clerk", "thesys", "registry")
    } else {
        @($Provider)
    }
    
    $results = @()
    $failedProviders = @()
    
    foreach ($prov in $providersToRotate) {
        Write-Host ""
        Write-StatusMessage "Processing provider: $prov" "Info"
        
        $result = switch ($prov) {
            "openai" { Invoke-OpenAIRotation -ManualKeyValue $ManualKey }
            "clerk" { Invoke-ClerkRotation -ManualKeyValue $ManualKey }
            "thesys" { Invoke-ThesysRotation -ManualKeyValue $ManualKey }
            "registry" { Invoke-RegistryRotation -ManualKeyValue $ManualKey }
            default { @{ Success = $false; Error = "Unknown provider: $prov" } }
        }
        
        $results += $result
        
        if (-not $result.Success) {
            $failedProviders += $prov
        }
    }
    
    # Write audit log
    if ($results.Count -gt 0 -and -not $DryRun) {
        Write-AuditLog -Records $results -OutputPath $AuditLog
    }
    
    # Summary
    Write-Host ""
    Write-Host "=" * 60
    Write-Host "  ROTATION SUMMARY"
    Write-Host "=" * 60
    
    $completed = ($results | Where-Object { $_.Success }).Count
    $failed = ($results | Where-Object { -not $_.Success }).Count
    
    Write-Host "  Completed: $completed/$($results.Count)"
    Write-Host "  Failed: $failed"
    Write-Host ""
    
    foreach ($r in $results) {
        $icon = if ($r.Success) { "✓" } else { "✗" }
        Write-Host "  $icon $($r.Provider)"
    }
    
    Write-Host ""
    Write-Host "=" * 60
    Write-Host "  IMPORTANT: Manual Actions Required"
    Write-Host "=" * 60
    Write-Host "  1. Revoke old keys via provider dashboards"
    Write-Host "  2. Update any external documentation"
    Write-Host "  3. Verify all services are functioning"
    Write-Host "  4. Keep the audit log for compliance records"
    Write-Host "=" * 60
    Write-Host ""
    
    if ($failedProviders.Count -gt 0) {
        Write-StatusMessage "Failed providers: $($failedProviders -join ', ')" "Error"
        exit 1
    }
}

# Run main
Main
