# API Key Rotation Checklist

Use this checklist to ensure all steps are completed during key rotation.

## Pre-Rotation (Before Starting)

- [ ] **Team Notification**: Notify team members of upcoming rotation
- [ ] **Schedule Window**: Choose low-traffic time for production
- [ ] **Access Verification**: Confirm access to all provider dashboards
  - [ ] OpenAI: https://platform.openai.com/account/api-keys
  - [ ] Clerk: https://dashboard.clerk.com
  - [ ] Thesys: Internal dashboard
  - [ ] GitHub: https://github.com/settings/tokens
- [ ] **Infisical Access**: Verify `infisical login` works
- [ ] **Kubernetes Access**: Verify `kubectl` access (for production)
- [ ] **System Health**: Check all services are healthy before rotation
- [ ] **Backup Confirmation**: Verify Infisical secret versioning is enabled

## Rotation Execution

### Step 1: Generate New Keys

- [ ] **OpenAI** (if rotating)
  - [ ] Visit https://platform.openai.com/account/api-keys
  - [ ] Click "Create new secret key"
  - [ ] Name: `fabric4l-{env}-{date}`
  - [ ] Copy key to secure location
  - [ ] Store in environment: `export OPENAI_MANUAL_KEY="sk-..."`

- [ ] **Clerk** (if rotating)
  - [ ] Visit https://dashboard.clerk.com
  - [ ] Select instance
  - [ ] Navigate to API Keys → Secret Keys
  - [ ] Add new secret key
  - [ ] Copy key to secure location
  - [ ] Store in environment: `export CLERK_MANUAL_KEY="sk_live_..."`

- [ ] **Thesys** (if rotating)
  - [ ] Visit Thesys dashboard
  - [ ] Generate new API key
  - [ ] Copy key to secure location
  - [ ] Store in environment: `export THESYS_MANUAL_KEY="..."`

- [ ] **Registry** (if rotating)
  - [ ] Visit https://github.com/settings/tokens
  - [ ] Generate new token with packages scopes
  - [ ] Copy token to secure location
  - [ ] Store in environment: `export REGISTRY_MANUAL_KEY="ghp_..."`

### Step 2: Execute Rotation

- [ ] **Runbook Method** (Interactive)
  ```bash
  ./scripts/security/rotation-runbook.sh
  ```

- [ ] **Script Method** (Direct)
  ```bash
  # Dry run first
  python scripts/security/key_rotation.py \
    --provider {openai|clerk|thesys|registry|all} \
    --env {dev|staging|prod} \
    --dry-run

  # Live rotation
  python scripts/security/key_rotation.py \
    --provider {openai|clerk|thesys|registry|all} \
    --env {dev|staging|prod}
  ```

- [ ] **GitHub Actions Method** (CI/CD)
  ```bash
  gh workflow run api-key-rotation.yml \
    --field provider={provider} \
    --field environment={env} \
    --field dry_run=false \
    --field manual_key="..."
  ```

### Step 3: Verify New Keys

- [ ] **Automated Verification**
  ```bash
  python scripts/security/verify-keys.py \
    --all \
    --env {dev|staging|prod} \
    --detailed
  ```

- [ ] **Service Health Check**
  ```bash
  kubectl get pods -n value-fabric
  ```

- [ ] **Log Check** (no auth errors)
  ```bash
  kubectl logs -n value-fabric deployment/api-gateway --tail=50 | grep -i error
  kubectl logs -n value-fabric deployment/layer2-extraction --tail=50 | grep -i error
  kubectl logs -n value-fabric deployment/layer4-agents --tail=50 | grep -i error
  ```

- [ ] **API Endpoint Test**
  ```bash
  curl https://api.fabric4l.com/health
  ```

- [ ] **Authentication Flow Test**
  - [ ] Access frontend application
  - [ ] Complete login flow
  - [ ] Verify session works

### Step 4: Revoke Old Keys

⚠️ **CRITICAL**: Only complete this step after verifying new keys work!

- [ ] **OpenAI** (if rotated)
  - [ ] Visit https://platform.openai.com/account/api-keys
  - [ ] Find old key (check audit log for ID)
  - [ ] Click trash icon to delete
  - [ ] Confirm deletion

- [ ] **Clerk** (if rotated)
  - [ ] Visit https://dashboard.clerk.com
  - [ ] Go to API Keys → Secret Keys
  - [ ] Revoke old secret key

- [ ] **Thesys** (if rotated)
  - [ ] Visit Thesys dashboard
  - [ ] Navigate to API Keys
  - [ ] Revoke old key

- [ ] **Registry** (if rotated)
  - [ ] Visit https://github.com/settings/tokens
  - [ ] Find old token
  - [ ] Delete token

## Post-Rotation

### Immediate (0-1 hours)

- [ ] **Audit Log**: Confirm audit log was generated
  ```bash
  ls -la rotation_audit_*.json
  ```

- [ ] **Documentation**: Update any external docs with new key references

- [ ] **Team Notification**: Notify team that rotation is complete

### Short-term (1-24 hours)

- [ ] **Service Monitoring**: Monitor service health dashboards
- [ ] **Error Log Review**: Check for any auth-related errors
- [ ] **CI/CD Check**: Verify pipelines can still access registry
- [ ] **Old Key Revocation**: Ensure all old keys are revoked within 24 hours

### Long-term (1-7 days)

- [ ] **Performance Baseline**: Confirm no performance degradation
- [ ] **User Feedback**: Check for any user-reported auth issues
- [ ] **Audit Log Archive**: Move audit log to secure storage
- [ ] **Documentation Update**: Update runbook if process changed

## Emergency Procedures

### If Rotation Fails

- [ ] **Stop**: Do not proceed with additional providers
- [ ] **Assess**: Check which step failed
- [ ] **Rollback**: Restore old key if necessary
  ```bash
  # Restore from backup
  infisical secrets set --env={env} --path={path} {SECRET_NAME}={old_value}
  kubectl rollout restart deployment/{service} -n value-fabric
  ```
- [ ] **Notify**: Alert team of issue
- [ ] **Document**: Record what went wrong for future prevention

### If New Keys Don't Work

- [ ] **Verify Key Format**: Confirm correct prefix and length
- [ ] **Check Provider Status**: Verify no provider outages
- [ ] **Test Directly**: Try API call with curl:
  ```bash
  curl https://api.openai.com/v1/models \
    -H "Authorization: Bearer $OPENAI_MANUAL_KEY"
  ```
- [ ] **Check Scopes**: Verify key has required permissions
- [ ] **Contact Support**: Reach out to provider if needed

## Compliance Requirements

### Audit Trail

- [ ] **Log Generated**: `rotation_audit_{provider}_{env}_{timestamp}.json`
- [ ] **Log Retained**: Kept for 365 days per policy
- [ ] **Log Secured**: Stored in secure location with access controls

### Reporting

- [ ] **Quarterly Summary**: Document completed rotations
- [ ] **Incident Report**: File if any issues occurred
- [ ] **Review**: Schedule quarterly review of rotation process

### Access Reviews

- [ ] **Dashboard Access**: Confirm only authorized personnel have access
- [ ] **Infisical Access**: Review Infisical project members
- [ ] **Key Holders**: Document who has access to manual keys during rotation

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Executor | | | |
| Verifier | | | |
| Security Lead | | | |

## Notes

**Rotation Date**: _______________

**Environment**: _______________

**Providers Rotated**: _______________

**Issues Encountered**: 
```

```

**Lessons Learned**:
```

```

---

## Quick Command Reference

```bash
# Verify current keys
python scripts/security/verify-keys.py --all --env prod

# Interactive rotation
./scripts/security/rotation-runbook.sh

# Direct rotation
export OPENAI_MANUAL_KEY="sk-..."
python scripts/security/key_rotation.py --provider openai --env prod

# GitHub Actions
git workflow run api-key-rotation.yml \
  --field provider=all --field environment=prod --field dry_run=false

# Check service logs
kubectl logs -n value-fabric deployment/api-gateway --tail=100
kubectl logs -n value-fabric deployment/layer2-extraction --tail=100
kubectl logs -n value-fabric deployment/layer4-agents --tail=100

# Get Infisical secret
infisical secrets get --env=prod --path=/shared CLERK_SECRET_KEY

# Set Infisical secret
infisical secrets set --env=prod --path=/shared CLERK_SECRET_KEY="sk_live_..."
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-15  
**Review Date**: Quarterly
