# API Key Rotation Guide for Fabric4L

This guide documents the complete process for rotating sensitive API keys and secrets in the Fabric4L platform.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Supported Providers](#supported-providers)
- [Rotation Methods](#rotation-methods)
- [Step-by-Step Process](#step-by-step-process)
- [Verification](#verification)
- [Rollback Procedure](#rollback-procedure)
- [Troubleshooting](#troubleshooting)
- [Audit and Compliance](#audit-and-compliance)

## Overview

Key rotation is a critical security practice that limits the exposure window of compromised credentials. Fabric4L implements a structured rotation process with:

- **Atomic updates**: New keys are verified before old keys are revoked
- **Zero-downtime**: Services are restarted gracefully to pick up new keys
- **Full audit trail**: All rotations are logged with timestamps and operator IDs
- **Automated verification**: Keys are tested against live APIs before confirmation

## Prerequisites

### Required Tools

- **Infisical CLI** (v0.20+): For secrets management
- **Python 3.11+**: For rotation scripts
- **kubectl**: For service restarts (production environments)
- **GitHub CLI (gh)**: For issue tracking (optional)

### Required Access

- Infisical project access for `fabric4l`
- GitHub repository write access (for CI/CD rotation)
- Provider dashboard access for manual key generation
- Kubernetes cluster access (for production restarts)

### Installation

```bash
# Install Infisical CLI
# macOS
brew install infisical/get-cli/infisical

# Linux
curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo -E bash
sudo apt-get install -y infisical

# Windows
scoop bucket add org https://github.com/nicholasgasior/scoop-bucket
scoop install infisical

# Login
infisical login
```

## Supported Providers

| Provider | Secret Name | Infisical Path | Rotation Method | Frequency |
|----------|-------------|----------------|-----------------|-----------|
| OpenAI | `OPENAI_API_KEY` | `/layer2-extraction` | Manual + Script | Quarterly |
| Thesys | `THESYS_API_KEY` | `/shared` | Manual + Script | Quarterly |
| Clerk | `CLERK_SECRET_KEY` | `/shared` | Manual + Script | Quarterly |
| GitHub Registry | `GHCR_PAT` | `/ci` | Manual + Script | Semi-annual |

## Rotation Methods

### Method 1: GitHub Actions (Recommended for Production)

Use the automated workflow for scheduled or on-demand rotation:

```bash
# Trigger via GitHub CLI
gh workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=staging \
  --field dry_run=true

# Or trigger with manual key
gh workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=false \
  --field manual_key="sk-..."
```

### Method 2: Local Script (Development/Testing)

Use the Python rotation script for local environments:

```bash
# Dry run
python scripts/security/key_rotation.py \
  --provider openai \
  --env dev \
  --dry-run

# Live rotation with manual key
export OPENAI_MANUAL_KEY="sk-your-new-key-here"
python scripts/security/key_rotation.py \
  --provider openai \
  --env dev

# Rotate all keys
export OPENAI_MANUAL_KEY="sk-..."
export CLERK_MANUAL_KEY="sk_live_..."
export THESYS_MANUAL_KEY="thesys_..."
python scripts/security/key_rotation.py \
  --provider all \
  --env dev
```

### Method 3: PowerShell (Windows)

For Windows environments:

```powershell
# Dry run
.\scripts\security\key-rotation.ps1 -Provider openai -Environment dev -DryRun

# Live rotation
$env:OPENAI_MANUAL_KEY = "sk-..."
.\scripts\security\key-rotation.ps1 -Provider openai -Environment dev

# Verify only
.\scripts\security\key-rotation.ps1 -Provider openai -Environment dev -VerifyOnly
```

## Step-by-Step Process

### 1. Pre-Rotation Checklist

Before starting rotation:

- [ ] Notify team members of upcoming rotation
- [ ] Ensure you have admin access to all provider dashboards
- [ ] Verify current system health (all services green)
- [ ] Confirm backup of current secrets (Infisical versioning)
- [ ] Schedule rotation during low-traffic window (production)

### 2. Generate New Keys

#### OpenAI

1. Visit: https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Name: `fabric4l-{environment}-{date}` (e.g., `fabric4l-prod-2024-01-15`)
4. Copy the key immediately (shown only once)
5. Save securely or set as environment variable:
   ```bash
   export OPENAI_MANUAL_KEY="sk-..."
   ```

#### Clerk

1. Visit: https://dashboard.clerk.com
2. Select your instance
3. Navigate to "API Keys" → "Secret Keys"
4. Click "Add secret key"
5. Copy the new key
6. Set environment variable:
   ```bash
   export CLERK_MANUAL_KEY="sk_live_..."
   ```

#### Thesys

1. Visit Thesys dashboard (internal URL)
2. Navigate to API Keys section
3. Generate new key with appropriate scopes
4. Copy the key
5. Set environment variable:
   ```bash
   export THESYS_MANUAL_KEY="thesys_..."
   ```

#### GitHub Container Registry

1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)" or "Fine-grained token"
3. Required scopes:
   - `read:packages`
   - `write:packages`
   - `delete:packages` (if needed)
4. Set environment variable:
   ```bash
   export REGISTRY_MANUAL_KEY="ghp_..."
   ```

### 3. Execute Rotation

#### For Development Environment

```bash
# Set all manual keys
export OPENAI_MANUAL_KEY="sk-..."
export CLERK_MANUAL_KEY="sk_live_..."
export THESYS_MANUAL_KEY="thesys_..."

# Run rotation
python scripts/security/key_rotation.py \
  --provider all \
  --env dev
```

#### For Staging/Production

Use GitHub Actions for audit trail and approval gates:

```bash
# Trigger workflow
gh workflow run api-key-rotation.yml \
  --field provider=all \
  --field environment=staging \
  --field dry_run=false \
  --field manual_key="sk-..."
```

### 4. Verify New Keys

After rotation, verify all keys are working:

```bash
# Verify specific provider
python scripts/security/verify-keys.py \
  --provider openai \
  --env prod

# Verify all providers
python scripts/security/verify-keys.py \
  --all \
  --env prod \
  --detailed
```

Expected output:
```
============================================================
  API KEY VERIFICATION
  Environment: prod
============================================================

✓ OPENAI - VALID
   Secret: OPENAI_API_KEY
   Value: sk-abc1...xyz9
   Checks: Exists: ✓ | Valid Format: ✓ | Accessible: ✓
   Details:
     - available_models: 47

✓ CLERK - VALID
   Secret: CLERK_SECRET_KEY
   Value: sk_test_dummy_a1b2...x9y0
   Checks: Exists: ✓ | Valid Format: ✓ | Accessible: ✓

============================================================
  SUMMARY
============================================================
  Passed: 4/4
  Failed: 0
```

### 5. Revoke Old Keys

**Critical**: Only revoke old keys after verifying new keys work!

#### OpenAI

1. Visit: https://platform.openai.com/account/api-keys
2. Find the old key (check rotation audit log for key ID)
3. Click the trash icon to delete
4. Confirm deletion

#### Clerk

1. Visit: https://dashboard.clerk.com
2. Go to API Keys → Secret Keys
3. Find the old key
4. Click "Revoke"

#### Thesys

1. Visit Thesys dashboard
2. Navigate to API Keys
3. Revoke the old key

#### GitHub

1. Visit: https://github.com/settings/tokens
2. Find the old token
3. Click "Delete"
4. Confirm deletion

### 6. Post-Rotation Verification

Run comprehensive checks:

```bash
# Run smoke tests
make verify

# Check service health
kubectl get pods -n value-fabric

# Test API endpoints
curl -H "Authorization: Bearer $(infisical secrets get --env=prod --path=/shared JWT_SECRET --json | jq -r .secretValue)" \
  https://api.fabric4l.com/health

# Verify Clerk authentication (frontend)
# Access the app and confirm login works
```

## Verification

### Automated Verification

The `verify-keys.py` script performs:

1. **Existence check**: Confirms secret exists in Infisical
2. **Format validation**: Validates key structure (prefixes, length)
3. **API accessibility**: Makes live API calls to verify key works

### Manual Verification Checklist

- [ ] All services show healthy status
- [ ] API requests succeed with new keys
- [ ] Authentication flows work (Clerk)
- [ ] LLM calls succeed (OpenAI)
- [ ] No errors in service logs
- [ ] CI/CD pipelines can access registry

### Service-Specific Checks

```bash
# Layer 2 Extraction (OpenAI)
kubectl logs -n value-fabric deployment/layer2-extraction --tail=100 | grep -i "openai\|error"

# Layer 4 Agents (Clerk auth)
kubectl logs -n value-fabric deployment/layer4-agents --tail=100 | grep -i "auth\|clerk\|error"

# API Gateway (Clerk)
kubectl logs -n value-fabric deployment/api-gateway --tail=100 | grep -i "jwt\|clerk\|error"
```

## Rollback Procedure

If rotation causes issues:

### Immediate Rollback

1. **Stop the rotation** if still in progress
2. **Restore from Infisical backup**:
   ```bash
   # Infisical keeps version history - contact admin to restore
   # Or manually re-enter the old key if you have it saved
   ```

### Manual Rollback Steps

1. Retrieve old key from secure backup
2. Update Infisical with old key:
   ```bash
   infisical secrets set --env=prod --path=/layer2-extraction \
     OPENAI_API_KEY="sk-old-key-here"
   ```
3. Restart affected services:
   ```bash
   kubectl rollout restart deployment/layer2-extraction -n value-fabric
   ```
4. Verify services recover
5. Investigate why new key failed

### GitHub Actions Rollback

If the workflow is running:

1. Cancel the workflow run
2. Check current Infisical values
3. Manually restore if needed
4. Create incident report issue

## Troubleshooting

### Common Issues

#### "OPENAI_MANUAL_KEY not provided"

**Cause**: Environment variable not set before running script

**Solution**:
```bash
export OPENAI_MANUAL_KEY="sk-..."
# Then re-run the rotation command
```

#### "Failed to authenticate with Infisical"

**Cause**: Infisical CLI not logged in or token expired

**Solution**:
```bash
infisical login
# Or use universal auth:
export INFISICAL_CLIENT_ID="..."
export INFISICAL_CLIENT_SECRET="..."
```

#### "Key verification failed: 401 Unauthorized"

**Cause**: Invalid key format or key not yet activated by provider

**Solution**:
1. Double-check key was copied correctly
2. Wait 30 seconds and retry (some providers have propagation delay)
3. Verify key in provider dashboard is active
4. Check if key has required scopes/permissions

#### "Service restart failed"

**Cause**: Kubernetes connection issue or deployment not found

**Solution**:
```bash
# Check cluster access
kubectl cluster-info

# Check deployment exists
kubectl get deployments -n value-fabric

# Manual restart if needed
kubectl rollout restart deployment/{service} -n value-fabric
```

### Debug Mode

Run with verbose logging:

```bash
python scripts/security/key_rotation.py \
  --provider openai \
  --env dev \
  --verbose
```

### Getting Help

1. Check recent audit logs:
   ```bash
   ls -la rotation_audit_*.json | tail -5
   ```

2. Review GitHub Actions logs:
   ```bash
   gh run list --workflow=api-key-rotation.yml --limit=5
   ```

3. Create support issue:
   ```bash
   gh issue create \
     --title "[SUPPORT] Key rotation assistance needed" \
     --body "Describe the issue here" \
     --label "security,support"
   ```

## Audit and Compliance

### Audit Log Format

Each rotation generates an audit log:

```json
{
  "rotation_timestamp": "2024-01-15T10:30:00Z",
  "records": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "provider": "openai",
      "environment": "prod",
      "key_id": "sk-abc123...",
      "old_key_id": "sk-old456...",
      "status": "completed",
      "rotated_by": "github-actions",
      "verification_passed": true
    }
  ]
}
```

### Retention Policy

- Audit logs: 365 days (stored as GitHub Actions artifacts)
- Infisical secret history: 90 days
- Provider dashboard logs: Per provider policy

### Compliance Checklist

After each rotation, ensure:

- [ ] Audit log generated and uploaded
- [ ] Old keys revoked within 24 hours
- [ ] Team notified of rotation completion
- [ ] Any incidents documented
- [ ] Documentation updated if process changed

### Reporting

Quarterly rotation summary for compliance:

```bash
# Generate rotation report
python -c "
import json
import glob

logs = glob.glob('rotation_audit_*.json')
for log in logs[-4:]:  # Last 4 rotations
    with open(log) as f:
        data = json.load(f)
        print(f'Rotation: {data[\"rotation_timestamp\"]}')
        for r in data['records']:
            print(f'  - {r[\"provider\"]}: {r[\"status\"]}')
"
```

---

## Quick Reference

### Command Cheat Sheet

```bash
# Rotate single provider
export PROVIDER_KEY="..."
python scripts/security/key_rotation.py --provider {openai|clerk|thesys|registry} --env {dev|staging|prod}

# Verify keys
python scripts/security/verify-keys.py --all --env prod --detailed

# Trigger GitHub workflow
gh workflow run api-key-rotation.yml --field provider=all --field environment=staging --field dry_run=false

# Check service status
kubectl get pods -n value-fabric

# View recent logs
kubectl logs -n value-fabric deployment/{service} --tail=100

# Infisical secret get
infisical secrets get --env=prod --path=/shared CLERK_SECRET_KEY

# Infisical secret set
infisical secrets set --env=prod --path=/shared CLERK_SECRET_KEY="sk_live_..."
```

### Provider Dashboard URLs

| Provider | URL |
|----------|-----|
| OpenAI | https://platform.openai.com/account/api-keys |
| Clerk | https://dashboard.clerk.com |
| GitHub | https://github.com/settings/tokens |

### Emergency Contacts

- Security Team: security@fabric4l.com
- DevOps On-Call: Check PagerDuty rotation
- Infisical Support: https://infisical.com/support

---

**Last Updated**: 2024-01-15  
**Document Version**: 1.0  
**Review Cycle**: Quarterly
