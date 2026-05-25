# API Key Rotation Automation - Implementation Summary

## Overview

This document summarizes the complete API key rotation automation implementation for Fabric4L, covering the rotation of OpenAI, Thesys, Clerk, and Registry tokens.

## Deliverables Created

### 1. Core Rotation Scripts

| File | Purpose | Platform |
|------|---------|----------|
| `scripts/security/key_rotation.py` | Main Python rotation engine with provider abstractions | Cross-platform |
| `scripts/security/key-rotation.ps1` | PowerShell version for Windows environments | Windows |
| `scripts/security/rotation-runbook.sh` | Interactive bash runbook for guided rotation | Unix/Linux/macOS |
| `scripts/security/verify-keys.py` | Post-rotation verification script | Cross-platform |

### 2. CI/CD Integration

| File | Purpose |
|------|---------|
| `.github/workflows/api-key-rotation.yml` | GitHub Actions workflow for automated rotation |

### 3. Documentation

| File | Purpose |
|------|---------|
| `docs/security/key-rotation-guide.md` | Comprehensive rotation guide with all procedures |
| `docs/security/key-rotation-checklist.md` | Step-by-step checklist for manual execution |
| `docs/security/KEY_ROTATION_SUMMARY.md` | This summary document |

## Architecture

### Provider Abstraction

The rotation system uses a provider pattern:

```
SecretProvider (abstract base)
├── OpenAIProvider
├── ThesysProvider
├── ClerkProvider
└── RegistryTokenProvider
```

Each provider implements:
- `generate_new_key()` - Create or accept new key
- `revoke_old_key()` - Disable old credentials
- `verify_key()` - Test key against live API
- `get_affected_services()` - Services requiring restart

### Atomic Rotation Workflow

```
┌─────────────────┐
│  Get Current    │
│    Key ID       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Generate New    │────▶│  Manual Input   │
│     Key         │     │  (for external  │
└────────┬────────┘     │   providers)   │
         │              └─────────────────┘
         ▼
┌─────────────────┐
│ Update Infisical│
│   (atomic)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Verify New     │──── Success ────▶ Revoke Old
│    Key Works    │                    Key
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Restart        │
│   Services      │
└─────────────────┘
```

## Security Features

### Key Protection

- **Masked Logging**: All keys are masked in logs (only first/last 6-10 chars shown)
- **Environment Variables**: Keys passed via env vars, never hardcoded
- **GitHub Secrets**: Workflow uses `::add-mask::` to prevent secret exposure
- **Audit Trail**: Every rotation logged with timestamp, operator, key IDs

### Atomic Operations

- **Verify Before Revoke**: New keys tested before old keys are revoked
- **Infisical Updates**: Atomic secret updates via Infisical API
- **Rollback Ready**: Old key IDs tracked for emergency restoration

### Access Control

- **Environment Protection**: Production rotations require confirmation
- **OIDC Authentication**: GitHub Actions uses OIDC for Infisical access
- **Approval Gates**: Production environment requires manual approval

## Usage Patterns

### Pattern 1: Interactive Runbook (Recommended for First-Time)

```bash
./scripts/security/rotation-runbook.sh
```

**Best for**: Learning the process, development environments, one-off rotations

### Pattern 2: Direct Script Execution

```bash
export OPENAI_MANUAL_KEY="sk-..."
python scripts/security/key_rotation.py --provider openai --env prod
```

**Best for**: Automation, CI/CD integration, scripting

### Pattern 3: GitHub Actions

```bash
gh workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=false \
  --field manual_key="sk-..."
```

**Best for**: Production, audit trail, team visibility

### Pattern 4: PowerShell (Windows)

```powershell
$env:OPENAI_MANUAL_KEY = "sk-..."
.\scripts\security\key-rotation.ps1 -Provider openai -Environment prod
```

**Best for**: Windows native environments, PowerShell automation

## Verification

### Automated Verification

```bash
# Verify all keys
python scripts/security/verify-keys.py --all --env prod --detailed

# Verify specific provider
python scripts/security/verify-keys.py --provider openai --env prod
```

Verification checks:
1. Secret exists in Infisical
2. Key format is valid (prefix, length)
3. API access works (live test)

### Manual Verification Checklist

See `docs/security/key-rotation-checklist.md` for complete manual verification steps.

## Provider-Specific Notes

### OpenAI

- **Rotation Method**: Manual (dashboard) + Script (Infisical update)
- **Key Format**: `sk-...` (51 characters)
- **Verification**: Tests against `/v1/models` endpoint
- **Dashboard**: https://platform.openai.com/account/api-keys

### Clerk

- **Rotation Method**: Manual (dashboard) + Script (Infisical update)
- **Key Format**: `sk_test_...` or `sk_live_...`
- **Verification**: Tests JWKS endpoint
- **Dashboard**: https://dashboard.clerk.com
- **Impact**: Affects all authenticated services

### Thesys

- **Rotation Method**: Manual (dashboard) + Script (Infisical update)
- **Key Format**: Provider-specific (typically `thesys_...` or long string)
- **Verification**: Format validation only (API-specific verification TBD)
- **Dashboard**: Internal URL

### GitHub Registry

- **Rotation Method**: Manual (GitHub settings) + Script (Infisical update)
- **Key Format**: `ghp_...` or `github_pat_...`
- **Verification**: Tests GitHub Packages API
- **Dashboard**: https://github.com/settings/tokens
- **Impact**: CI/CD pipelines, container pulls

## Integration Points

### Infisical Paths

| Secret | Path | Environment |
|--------|------|-------------|
| `OPENAI_API_KEY` | `/layer2-extraction` | dev, staging, prod |
| `CLERK_SECRET_KEY` | `/shared` | dev, staging, prod |
| `THESYS_API_KEY` | `/shared` | dev, staging, prod |
| `GHCR_PAT` | `/ci` | dev, staging, prod |

### Affected Services

| Provider | Services to Restart |
|----------|---------------------|
| OpenAI | layer2-extraction, layer4-agents |
| Clerk | api-gateway, layer1-ingestion, layer2-extraction, layer3-knowledge, layer4-agents |
| Thesys | layer1-ingestion |
| Registry | CI/CD pipelines (no runtime services) |

## Scheduled Rotation

The GitHub Actions workflow is configured for quarterly rotation:

```yaml
schedule:
  - cron: '0 3 1 */3 *'  # 3 AM UTC, first day of quarter
```

Rotation frequency by provider:
- **OpenAI**: Quarterly (every 3 months)
- **Clerk**: Quarterly
- **Thesys**: Quarterly
- **Registry**: Semi-annual (every 6 months)

## Audit and Compliance

### Audit Log Format

```json
{
  "rotation_timestamp": "2024-01-15T10:30:00Z",
  "records": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "provider": "openai",
      "environment": "prod",
      "key_id": "sk-abc...",
      "old_key_id": "sk-old...",
      "status": "completed",
      "rotated_by": "github-actions",
      "verification_passed": true
    }
  ]
}
```

### Retention

- Audit logs: 365 days (GitHub Actions artifacts)
- Infisical history: 90 days
- Provider dashboard logs: Per provider policy

## Success Criteria Verification

| Criterion | Implementation | Verification |
|-----------|---------------|------------|
| New keys generated securely | Manual generation via provider dashboards | Provider dashboard confirmation |
| Infisical updated | `infisical secrets set` via CLI/API | `verify-keys.py` checks existence |
| Old keys revoked | Manual revocation via provider dashboards | Dashboard shows key deleted/revoked |
| No service downtime | Rolling restarts via kubectl | `kubectl rollout status` checks |
| Auditable process | JSON audit logs with timestamps | Check `rotation_audit_*.json` files |

## Quick Start Guide

### For First-Time Users

1. Read: `docs/security/key-rotation-guide.md`
2. Run: `./scripts/security/rotation-runbook.sh`
3. Follow the interactive prompts

### For Experienced Users

```bash
# Rotate all keys in dev
export OPENAI_MANUAL_KEY="sk-..."
export CLERK_MANUAL_KEY="sk_live_..."
export THESYS_MANUAL_KEY="thesys_..."
export REGISTRY_MANUAL_KEY="ghp_..."

python scripts/security/key_rotation.py --provider all --env dev

# Verify
python scripts/security/verify-keys.py --all --env dev
```

### For Production

```bash
# Use GitHub Actions for audit trail
git workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=true  # Test first

# Then live
git workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=false \
  --field manual_key="sk-..."
```

## Troubleshooting

### Common Issues

1. **"Manual key not provided"**
   - Set the appropriate `*_MANUAL_KEY` environment variable
   - See provider-specific setup in the guide

2. **"Failed to authenticate with Infisical"**
   - Run `infisical login`
   - Check `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET`

3. **"Key verification failed"**
   - Verify key was copied correctly
   - Check provider dashboard for key status
   - Wait 30 seconds for propagation (some providers)

4. **"Service restart failed"**
   - Verify kubectl access: `kubectl cluster-info`
   - Check deployment exists: `kubectl get deployments -n value-fabric`

### Getting Help

- **Documentation**: `docs/security/key-rotation-guide.md`
- **Checklist**: `docs/security/key-rotation-checklist.md`
- **Support**: security@fabric4l.com
- **Issues**: Create GitHub issue with `security` label

## Future Enhancements

Potential improvements for future iterations:

1. **Automated Key Generation**: Integrate with provider APIs for true automated rotation
2. **Key Expiration Alerts**: Proactive notifications 7 days before rotation due
3. **Rollback Automation**: One-command rollback to previous keys
4. **Integration Tests**: Post-rotation smoke tests for critical paths
5. **Slack Notifications**: Real-time rotation status updates
6. **Metrics Dashboard**: Track rotation frequency and success rates

## Maintenance

### Regular Reviews

- **Quarterly**: Review rotation logs and success rates
- **Semi-annual**: Update provider URLs and procedures
- **Annual**: Full runbook review and testing

### Updates Required When

- New API provider added to stack
- Infisical path structure changes
- Provider dashboard URLs change
- Service names change in Kubernetes

---

**Implementation Date**: 2024-01-15  
**Version**: 1.0  
**Maintained By**: DevOps Security Team

For questions or issues, refer to the detailed guide at `docs/security/key-rotation-guide.md`.
