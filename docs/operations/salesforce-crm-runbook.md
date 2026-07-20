# Salesforce CRM Integration — Operator Runbook

> **Audit note (2026-07-18):** This runbook references Prometheus metrics with the prefix `layer4_crm_salesforce_*`. The actual metrics registered in `services/layer4-agents/src/layer4_agents/metrics/prometheus_metrics.py` use the prefix `crm_salesforce_*`. There is also a duplicate/updated runbook at `docs/operations/salesforce-crm/runbook.md` that should be considered canonical for metric names.

**Version:** 1.0  
**Date:** 2026-05-01  
**Scope:** Production operations for the Salesforce CRM integration in Fabric_4L Layer 4.

---

## 1. Prerequisites

### 1.1 Salesforce Connected App Configuration

1. Log in to Salesforce Setup (as admin).
2. Navigate to **App Manager** → **New Connected App**.
3. Configure:
   - **API Name:** `ValueFabric_Integration`
   - **Enable OAuth Settings:** Checked
   - **Callback URL:** `https://<your-domain>/v1/webhooks/crm/salesforce?tenant_id=<tenant-id>`
     - Note: `tenant_id` query parameter is required in production.
   - **Selected OAuth Scopes:**
     - `api`
     - `refresh_token`
     - `offline_access`
4. Save and note the **Consumer Key** (`SALESFORCE_CLIENT_ID`) and **Consumer Secret** (`SALESFORCE_CLIENT_SECRET`).
5. Set IP Relaxation to **Relax IP restrictions** (or configure trusted IPs).

### 1.2 Environment Variables

Ensure these are set in your secrets manager (Infisical/Vault) or environment:

| Variable | Required | Description |
|----------|----------|-------------|
| `CREDENTIALS_MASTER_KEY` | ✅ Yes | 43-char Fernet key for credential encryption |
| `SALESFORCE_CLIENT_ID` | ✅ Yes | Connected App Consumer Key |
| `SALESFORCE_CLIENT_SECRET` | ✅ Yes | Connected App Consumer Secret |
| `SALESFORCE_REDIRECT_URI` | ✅ Yes | OAuth callback URL |
| `SALESFORCE_WEBHOOK_SECRET` | ⚠️ Recommended | Shared secret for webhook HMAC verification |
| `CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION` | ❌ No | Development-only escape hatch for local testing without `tenant_id`; must remain unset/false outside local dev |

---

## 2. Day-1 Operations

### 2.1 Verify Integration Encryption

```bash
# Check that CREDENTIALS_MASTER_KEY is set and valid
python -c "from cryptography.fernet import Fernet; import os; k=os.getenv('CREDENTIALS_MASTER_KEY'); assert len(k)==43, 'Invalid key length'; Fernet(k.encode())"
```

### 2.2 Rotate Client Secret

1. In Salesforce Setup, go to the Connected App → **Manage** → **Edit Policies**.
2. Click **Regenerate Consumer Secret**.
3. Update `SALESFORCE_CLIENT_SECRET` in your secrets manager.
4. Restart Layer 4 pods to pick up the new secret.
5. Verify token refresh still works:
   ```bash
   # Trigger a test sync for a tenant
   curl -X POST "https://<api>/v1/integrations/salesforce/sync" \
     -H "Authorization: Bearer <token>" \
     -H "X-Tenant-ID: <tenant-id>"
   ```

### 2.3 Reconnect a Tenant

If a tenant's Salesforce token is revoked or expired:

1. Admin opens **Settings → Integrations** in the UI.
2. Clicks **Disconnect** for Salesforce.
3. Re-enters the new Access Token and Refresh Token (manual flow).
4. Clicks **Test Connection** to verify.
5. Clicks **Sync Now** to trigger initial sync.

---

## 3. Monitoring & Alerting

### 3.1 Key Metrics

Query Prometheus for:

```promql
# Sync failure rate (alert if > 10% over 5m)
rate(layer4_crm_salesforce_sync_failed_total[5m])
/
rate(layer4_crm_salesforce_sync_started_total[5m])

# Token refresh failures (alert if > 0)
rate(layer4_crm_salesforce_token_refresh_failed_total[5m])

# Rate limit hits (alert if > 0)
rate(layer4_crm_salesforce_rate_limit_total[5m])

# Sync duration p99
histogram_quantile(0.99,
  rate(layer4_crm_salesforce_sync_duration_seconds_bucket[5m])
)
```

### 3.2 Log Queries

```bash
# Failed syncs for a tenant
jq 'select(.event == "sync_failed") | select(.tenant_id == "TENANT_ID")'

# Token refresh failures
jq 'select(.event == "token_refresh_failed")'

# Webhook rejections (tenant isolation)
jq 'select(.message | contains("webhook rejected"))'
```

---

## 4. Incident Response

### 4.1 Sync Stuck in "running"

**Symptom:** Tenant reports sync hasn't completed for hours.

**Steps:**
1. Check if the sync task is still active:
   ```sql
   SELECT sync_status, last_sync_at, last_error_message
   FROM integrations
   WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
   ```
2. If `sync_status = 'running'` and `last_sync_at` is > 30 min old, the background task likely crashed.
3. Manually reset status:
   ```sql
   UPDATE integrations
   SET sync_status = 'failed', last_error_message = 'Manual reset: stuck sync'
   WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
   ```
4. Trigger a new sync via API or UI.

### 4.2 "Invalid webhook credentials" Errors

**Symptom:** Salesforce webhooks return 401.

**Steps:**
1. Check that the webhook URL includes `?tenant_id=<tenant-id>`.
2. Verify the tenant has an active Salesforce integration:
   ```sql
   SELECT enabled, sync_status FROM integrations
   WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
   ```
3. Verify the tenant's per-tenant webhook token is configured:
   ```sql
   SELECT credentials_encrypted IS NOT NULL as has_creds
   FROM integrations
   WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
   ```
   The `credentials_encrypted` blob must contain a `webhook_token` field.
4. If the token is missing or incorrect, rotate the tenant integration and reissue the webhook URL. Webhook processing no longer falls back to an implicit/default tenant or a global-only auth path in normal operation.

### 4.3 "Token refresh failed"

**Symptom:** Sync fails with 401, token refresh fails.

**Steps:**
1. Check if refresh token is present:
   ```sql
   SELECT refresh_token_encrypted IS NOT NULL as has_refresh_token
   FROM integrations
   WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
   ```
2. If `has_refresh_token = false`, the tenant must reconnect (no refresh token available).
3. If present, check `SALESFORCE_CLIENT_ID` and `SALESFORCE_CLIENT_SECRET` are correct.
4. Verify the Connected App hasn't been deleted or secret rotated in Salesforce.

### 4.4 Rate Limit Hit (429)

**Symptom:** Salesforce API returns 429, sync partial-fails.

**Steps:**
1. Check current API usage in Salesforce Setup → **System Overview**.
2. Reduce `CRM_SYNC_BATCH_SIZE` or increase `CRM_SYNC_INTERVAL_MINUTES` for the tenant.
3. Monitor `layer4_crm_salesforce_rate_limit_total` metric.
4. Consider requesting a Salesforce API limit increase if sustained.

---

## 5. Rollback Plan

### 5.1 Disable Integration (Tenant-Level)

```sql
UPDATE integrations
SET enabled = false, sync_status = 'idle'
WHERE tenant_id = '<tenant-id>' AND provider = 'salesforce';
```

### 5.2 Disable Integration (Global)

Set environment variable:
```bash
CRM_TYPE=none
```
Restart Layer 4 pods. This prevents all CRM sync operations.

### 5.3 Rollback Migration

If migration 021 caused issues:
```bash
alembic downgrade 020
```

---

## 6. Security Checklist

- [ ] `CREDENTIALS_MASTER_KEY` is 43 chars and stored in secrets manager
- [ ] `CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION` is unset or `false` in production
- [ ] Webhook URLs include `?tenant_id=<tenant-id>`
- [ ] Each pilot tenant has a unique `webhook_token` stored encrypted in `integrations.credentials_encrypted`
- [ ] Salesforce Connected App uses minimal OAuth scopes
- [ ] Global HMAC webhook secret is rotated quarterly and never used as a substitute for tenant-bound webhook credentials in production
- [ ] RLS policies are enabled on `integrations`, `accounts`, `account_sync_status`
