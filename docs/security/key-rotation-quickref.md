# API Key Rotation - Quick Reference Card

## 🚀 Fastest Path to Rotation

### Development Environment (Quick)

```bash
# 1. Get new keys from dashboards (see URLs below)
export OPENAI_MANUAL_KEY="sk-..."

# 2. Run rotation
python scripts/security/key_rotation.py --provider openai --env dev

# 3. Verify
python scripts/security/verify-keys.py --provider openai --env dev

# 4. Revoke old key via dashboard
```

### Production Environment (Safe)

```bash
# 1. Trigger workflow (starts with approval gate)
git workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=false \
  --field manual_key="sk-..."

# 2. Monitor GitHub Actions for completion
gh run watch

# 3. Verify after completion
python scripts/security/verify-keys.py --all --env prod

# 4. Revoke old key via dashboard
```

## 📋 Provider Dashboard URLs

| Provider | URL | Key Prefix |
|----------|-----|------------|
| **OpenAI** | https://platform.openai.com/account/api-keys | `sk-` |
| **Clerk** | https://dashboard.clerk.com | `sk_test_` / `sk_live_` |
| **Thesys** | Internal dashboard | `thesys_` or long string |
| **GitHub** | https://github.com/settings/tokens | `ghp_` / `github_pat_` |

## 🔧 Common Commands

### Rotation Commands

```bash
# Interactive runbook (recommended first-time)
./scripts/security/rotation-runbook.sh

# Rotate single provider
export OPENAI_MANUAL_KEY="sk-..."
python scripts/security/key_rotation.py --provider openai --env prod

# Rotate all providers
export OPENAI_MANUAL_KEY="sk-..."
export CLERK_MANUAL_KEY="sk_live_..."
export THESYS_MANUAL_KEY="thesys_..."
export REGISTRY_MANUAL_KEY="ghp_..."
python scripts/security/key_rotation.py --provider all --env dev

# Dry run (no actual changes)
python scripts/security/key_rotation.py --provider openai --env prod --dry-run

# PowerShell (Windows)
$env:OPENAI_MANUAL_KEY="sk-..."
.\scripts\security\key-rotation.ps1 -Provider openai -Environment prod
```

### Verification Commands

```bash
# Verify all keys
python scripts/security/verify-keys.py --all --env prod --detailed

# Verify specific provider
python scripts/security/verify-keys.py --provider openai --env prod

# Verify and output to file
python scripts/security/verify-keys.py --all --env prod --output verify-results.json
```

### GitHub Actions

```bash
# Trigger workflow
git workflow run api-key-rotation.yml \
  --field provider=openai \
  --field environment=prod \
  --field dry_run=true

# List recent runs
gh run list --workflow=api-key-rotation.yml --limit=5

# Watch current run
gh run watch
```

### Infisical Commands

```bash
# Get current secret
infisical secrets get --env=prod --path=/shared CLERK_SECRET_KEY

# Set new secret
infisical secrets set --env=prod --path=/shared CLERK_SECRET_KEY="sk_live_..."

# List secrets at path
infisical secrets --env=prod --path=/shared
```

### Kubernetes Commands

```bash
# Check service health
kubectl get pods -n value-fabric

# View logs
kubectl logs -n value-fabric deployment/api-gateway --tail=100
kubectl logs -n value-fabric deployment/layer2-extraction --tail=100
kubectl logs -n value-fabric deployment/layer4-agents --tail=100

# Restart service
kubectl rollout restart deployment/api-gateway -n value-fabric

# Watch rollout
kubectl rollout status deployment/api-gateway -n value-fabric --timeout=300s
```

## 🎯 Environment Variable Reference

| Provider | Environment Variable | Example |
|----------|---------------------|---------|
| OpenAI | `OPENAI_MANUAL_KEY` | `sk-abc123...` |
| Clerk | `CLERK_MANUAL_KEY` | `sk_test_dummy_abc123...` |
| Thesys | `THESYS_MANUAL_KEY` | `thesys_abc123...` |
| Registry | `REGISTRY_MANUAL_KEY` | `ghp_abc123...` |

## 📁 File Locations

| File | Path |
|------|------|
| Python rotation script | `scripts/security/key_rotation.py` |
| PowerShell script | `scripts/security/key-rotation.ps1` |
| Bash runbook | `scripts/security/rotation-runbook.sh` |
| Verification script | `scripts/security/verify-keys.py` |
| GitHub workflow | `.github/workflows/api-key-rotation.yml` |
| Full guide | `docs/security/key-rotation-guide.md` |
| Checklist | `docs/security/key-rotation-checklist.md` |
| This quickref | `docs/security/key-rotation-quickref.md` |

## ⚡ One-Liners

```bash
# Rotate + verify in one command
export OPENAI_MANUAL_KEY="sk-..." && \
python scripts/security/key_rotation.py --provider openai --env dev && \
python scripts/security/verify-keys.py --provider openai --env dev

# Check all services health after rotation
kubectl get pods -n value-fabric && \
kubectl logs -n value-fabric deployment/api-gateway --tail=50 | grep -i error && \
kubectl logs -n value-fabric deployment/layer2-extraction --tail=50 | grep -i error

# Find recent audit logs
ls -lt rotation_audit_*.json | head -5

# View latest audit log
cat $(ls -t rotation_audit_*.json | head -1) | jq '.'
```

## 🆘 Emergency Commands

```bash
# Check current key exists
infisical secrets get --env=prod --path=/layer2-extraction OPENAI_API_KEY

# Quick service health check
kubectl get pods -n value-fabric -o wide

# Check for auth errors in logs
kubectl logs -n value-fabric deployment/api-gateway --tail=100 | grep -i "auth\|401\|403\|clerk"

# Restart all affected services (Clerk rotation)
kubectl rollout restart deployment/api-gateway -n value-fabric && \
kubectl rollout restart deployment/layer1-ingestion -n value-fabric && \
kubectl rollout restart deployment/layer2-extraction -n value-fabric && \
kubectl rollout restart deployment/layer3-knowledge -n value-fabric && \
kubectl rollout restart deployment/layer4-agents -n value-fabric
```

## 📊 Verification Checklist (Quick)

After rotation, run:

```bash
# 1. Automated verification
python scripts/security/verify-keys.py --all --env prod

# 2. Service health
kubectl get pods -n value-fabric

# 3. API health
curl https://api.fabric4l.com/health

# 4. Test login (manual)
# Access frontend and complete login flow
```

All should pass before revoking old keys.

## 🔒 Security Reminders

- **Never commit keys to git**
- **Never share keys in Slack/email**
- **Always use `--dry-run` first**
- **Always verify before revoking**
- **Always check audit log was generated**
- **Always revoke old keys within 24 hours**

## 📞 Support

| Issue | Resource |
|-------|----------|
| Process questions | `docs/security/key-rotation-guide.md` |
| Step-by-step help | `docs/security/key-rotation-checklist.md` |
| Emergency | security@fabric4l.com |
| GitHub issues | Create issue with `security` label |

---

**Print this page** for easy reference during rotation.
