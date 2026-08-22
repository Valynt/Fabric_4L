#!/usr/bin/env pwsh
# Generate secrets for Value Fabric security hardening
# Usage: .\generate-secrets.ps1 [output_file]

param(
    [string]$OutputFile = "generated-secrets.txt"
)

$secrets = @()

function Generate-HexSecret {
    param([int]$Bytes = 32)
    $bytes = New-Object byte[] $Bytes
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ''
}

Write-Host "Generating Value Fabric Security Secrets" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# API Key Cache Secret
$apiKeyCacheSecret = Generate-HexSecret -Bytes 32
$secrets += "# API Key Cache Secret (for HMAC-SHA256 key fingerprinting)"
$secrets += "API_KEY_CACHE_SECRET=$apiKeyCacheSecret"
$secrets += ""
Write-Host "✓ API_KEY_CACHE_SECRET generated" -ForegroundColor Green

# JWT Secret (legacy HS256 support during migration)
$jwtSecret = Generate-HexSecret -Bytes 32
$secrets += "# JWT Secret (legacy HS256 - deprecated, use RS256 keys instead)"
$secrets += "JWT_SECRET=$jwtSecret"
$secrets += ""
Write-Host "✓ JWT_SECRET generated (legacy)" -ForegroundColor Yellow

# Service Auth Secret (for inter-service authentication)
$serviceAuthSecret = Generate-HexSecret -Bytes 32
$secrets += "# Service Auth Secret (for X-Service-Auth header between internal services)"
$secrets += "SERVICE_AUTH_SECRET=$serviceAuthSecret"
$secrets += ""
Write-Host "✓ SERVICE_AUTH_SECRET generated" -ForegroundColor Green

# Redis Password
$redisPassword = Generate-HexSecret -Bytes 16
$secrets += "# Redis Password"
$secrets += "REDIS_PASSWORD=$redisPassword"
$secrets += ""
Write-Host "✓ REDIS_PASSWORD generated" -ForegroundColor Green

# Credentials Master Key (Fernet - 32 bytes URL-safe base64 = 43 chars)
Add-Type -AssemblyName System.Security
$fernetKeyBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($fernetKeyBytes)
# Layer 4 validates this as URL-safe Base64 of 32 bytes and only accepts
# 43- or 44-character values. Convert to URL-safe alphabet and strip any
# padding so a 32-byte input yields a 43-character key (never 45).
$fernetKey = [Convert]::ToBase64String($fernetKeyBytes).
    Replace("+", "-").
    Replace("/", "_").
    TrimEnd("=")
if ($fernetKey.Length -notin 43, 44) {
    throw "CREDENTIALS_MASTER_KEY must be 43 or 44 characters, got $($fernetKey.Length)"
}
$secrets += "# Credentials Master Key (Fernet - 32 bytes URL-safe base64-encoded)"
$secrets += "CREDENTIALS_MASTER_KEY=$fernetKey"
Write-Host "✓ CREDENTIALS_MASTER_KEY generated ($($fernetKey.Length) chars)" -ForegroundColor Green

# Write to file
$secrets | Out-File -FilePath $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "✓ All secrets written to: $OutputFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Red
Write-Host "- Store this file securely (1Password, Vault, etc.)" -ForegroundColor Yellow
Write-Host "- Never commit secrets to version control" -ForegroundColor Yellow
Write-Host "- For K8s: Use External Secrets Operator or Sealed Secrets" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Load secrets into your secret manager"
Write-Host "  2. Reference them in your .env or K8s manifests"
Write-Host "  3. Also run ./generate-jwt-keys.sh for RSA key pair"
