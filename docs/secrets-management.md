# Value Fabric Secrets Management Guide

Production-ready secret handling across local development, Docker Compose, and Kubernetes environments.

---

## Overview

| Environment | Method | Secret Store |
|-------------|--------|--------------|
| Local Dev | `.env` file | Local filesystem (git-ignored) |
| Docker Compose | `.env` file + env vars | Local filesystem (git-ignored) |
| Kubernetes (dev/shared) | External Secrets Operator | HashiCorp Vault or Infisical (preferred) |
| Kubernetes (prod) | External Secrets Operator | HashiCorp Vault or Infisical (preferred); cloud secret managers supported |

---

## Required Secrets Inventory

### Critical (Service Startup Will Fail Without These)

| Secret Name | Used By | Purpose | Source |
|-------------|---------|---------|--------|
| `OPENAI_API_KEY` | L1, L2, L4 | LLM API calls | OpenAI Dashboard |

### Important (Required for Full Functionality)

| Secret Name | Used By | Purpose | Default | Source |
|-------------|---------|---------|---------|--------|
| `NEO4J_PASSWORD` | L2, L3, L4 | Graph database auth | `valuefabric` | Self-managed |
| `JWT_SECRET` | L5 | Token signing | `changeme-in-production` | Generate with `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | L1, L4, L5 | SQL database auth | `postgres` | Self-managed |

### Optional (Enhancements)

| Secret Name | Used By | Purpose | Source |
|-------------|---------|---------|--------|
| `ANTHROPIC_API_KEY` | L4 | Alternative LLM provider | Anthropic Console |
| `PINECONE_API_KEY` | L3 | Vector search backend | Pinecone Dashboard |
| `BROWSERBASE_API_KEY` | L1 | Browser automation | Browserbase Dashboard |
| `FIRECRAWL_API_KEY` | L1 | Web scraping API | Firecrawl Dashboard |
| `LAYER3_API_KEY` | L5 | Inter-layer auth | Self-managed |

---

## Local Development Setup (Default: Ephemeral Local Bootstrap)

### 1. Generate ephemeral local env file

```bash
scripts/security/bootstrap_local_secrets.sh
```

This writes `.local/secrets/dev.env` (git-ignored), sets strict file permissions, and rotates values each time the script runs.

### 2. Optional: Create manual .env file

```bash
cd value-fabric
cp .env.example .env
# Edit .env with your real secrets
```

### 3. Required minimum for local dev

Your `.env` file must contain at minimum:

```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

### 4. Verify local env files are git-ignored

```bash
cat .gitignore | rg -n "\\.env|\\.local/secrets"
```

Expected output: `.env` or `.env.local` should be listed.

---

## Docker Compose Setup

Docker Compose automatically loads `.env` from the same directory as `docker-compose.yml`.

> ⚠️ **Security warning:** Vault dev mode (`server -dev`) is for isolated local development only.
> It is never production-safe and must never be used for staging/production deployments.
> Production/staging must use Vault auth methods such as Kubernetes auth, OIDC/JWT, or AppRole.

### Startup with secrets

```bash
cd value-fabric
# Ensure .env exists with OPENAI_API_KEY
docker-compose up -d
```

### Optional local Vault dev-root-token override (local only)

Use this only when you explicitly need a stable local Vault dev token:

```bash
docker compose \
  -f docker-compose.full.yml \
  -f docker-compose.full.dev-vault.yml \
  --profile local-dev up -d vault
```

This override file intentionally sets `VAULT_DEV_ROOT_TOKEN_ID=root` and must never be included in release compose paths.

### Verifying secrets are injected

```bash
# Check environment inside container
docker exec value-fabric-layer1 env | grep OPENAI
# Should show: OPENAI_API_KEY=sk-...
```

---

## Kubernetes Setup

### Development and Shared Clusters (External Secrets Required)

`k8s/secrets.yml` is a blocked legacy path and must not be used in shared dev, staging, or production clusters.
Use External Secrets + Vault (or Infisical) in every cluster that more than one developer can access.

### Production (External Secrets Operator)

#### Prerequisites

1. Install External Secrets Operator:
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets
   ```

2. Configure Vault Kubernetes auth (one-time setup):
   ```bash
   vault auth enable kubernetes
   vault write auth/kubernetes/config \
     kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
     token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
     kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
   ```

3. Create Vault policy for Value Fabric:
   ```bash
   vault policy write value-fabric-policy - <<EOF
   path "secret/data/value-fabric/*" {
     capabilities = ["read"]
   }
   EOF
   ```

4. Create Kubernetes auth role:
   ```bash
   vault write auth/kubernetes/role/value-fabric-role \
     bound_service_account_names=external-secrets-sa \
     bound_service_account_namespaces=external-secrets \
     policies=value-fabric-policy \
     ttl=1h
   ```

#### Deploy Production Secrets

```bash
# Update vault-integration.yml with your Vault URL
# Then apply:
kubectl apply -f k8s/external-secrets/vault-integration.yml

# Verify ExternalSecrets created
kubectl get externalsecrets -n value-fabric

# Verify secrets populated
kubectl get secrets -n value-fabric
```

---

## Secret Rotation Procedures

### LLM API Keys (OpenAI, Anthropic)

1. Generate new key in provider dashboard
2. Update secret store (Vault or K8s Secret)
3. Trigger rolling restart of affected pods:
   ```bash
   kubectl rollout restart deployment/layer1-ingestion -n value-fabric
   kubectl rollout restart deployment/layer2-extraction -n value-fabric
   kubectl rollout restart deployment/layer4-agents -n value-fabric
   ```
4. Verify new pods healthy
5. Revoke old key in provider dashboard

### Database Passwords (Neo4j, PostgreSQL)

1. Update password in database first
2. Update secret in Vault/K8s
3. Rolling restart of all services using that database
4. Verify connectivity post-restart

#### Neo4j Secret Contract (required)

- **Application workloads (L2/L3/L4 and other Neo4j clients)** must source `NEO4J_USER` and `NEO4J_PASSWORD` from dedicated keys (`neo4j_user` and `neo4j_password`, or equivalent dedicated key names).
- **Application workloads must not** source `NEO4J_PASSWORD` from `auth`/`NEO4J_AUTH` keys.
- `NEO4J_AUTH` should be used only by the Neo4j server container bootstrap path where Neo4j expects `user/password` format.
- CI enforces this via `python3 scripts/ci/check_neo4j_secret_key_mappings.py`.

### JWT Secret (L5)

**⚠️ CRITICAL:** JWT secret rotation invalidates all existing tokens.

1. Schedule maintenance window
2. Update secret in Vault/K8s
3. Rolling restart of L5 deployment
4. Notify all users to re-authenticate
5. Monitor for auth errors

---

## Security Best Practices

### General

- **Never commit secrets to git** - Use `.env.example` for templates
- **Rotate keys regularly** - API keys every 30 days; DB/JWT every 90 days or immediately after incidents
- **Use least privilege** - Scope API keys to minimum required permissions
- **Monitor key usage** - Set up alerts for unusual activity

### Docker Compose

- `.env` file should have permissions `600` (owner read/write only)
- Use Docker Secrets for Swarm mode (not applicable for Compose standalone)

### Kubernetes

- **Development/shared clusters:** Always use External Secrets backed by Vault/Infisical
- **Production:** Always use External Secrets backed by Vault/Infisical (or approved cloud manager)
- Enable encryption at rest for etcd (K8s 1.7+)
- Use RBAC to limit secret access
- Rotate service account tokens regularly

## Developer Runbook: Rotation Cadence & Revocation Drill

### Rotation cadence (minimum)

- LLM/API provider tokens: every 30 days.
- Database and Redis credentials: every 90 days.
- JWT signing material: every 90 days (or move to keyset rotation if supported).
- Emergency rotation: within 1 hour of suspected leak.

### Revocation drill (monthly, non-prod)

1. Select one non-critical key (for example, staging `OPENAI_API_KEY`).
2. Mint replacement in Vault/Infisical.
3. Update ExternalSecret source value.
4. Force refresh/restart workloads and verify readiness checks pass.
5. Revoke old secret and confirm no further successful authentication with old credential.
6. Capture evidence (timestamp, operator, impacted workloads, rollback plan) in incident log.

### Vault Specific

- Enable audit logging
- Use short TTLs (1h default)
- Enable response wrapping for sensitive operations
- Use AppRole or Kubernetes auth (not long-lived tokens)
- Enable seal/unseal monitoring

---

## Troubleshooting

### "OPENAI_API_KEY not set" error

**Symptom:** Service fails to start with key error
**Fix:**
```bash
# Check .env file exists and has key
cat .env | grep OPENAI

# For K8s, check secret exists
kubectl get secret openai-secret -n value-fabric -o jsonpath='{.data.api-key}' | base64 -d
```

### "authentication failed" for Neo4j/Postgres

**Symptom:** Services fail to connect to database
**Fix:**
- Verify secret matches actual database password
- Check network connectivity: `kubectl exec -it <pod> -n value-fabric -- nc -zv neo4j 7687`

### External Secrets not populating

**Symptom:** `ExternalSecret` shows `SecretSyncedError`
**Fix:**
```bash
# Check ExternalSecret status
kubectl describe externalsecret openai-api-key -n value-fabric

# Check Vault connectivity from pod
kubectl exec -it vault-0 -n vault -- vault status
```

---

## Reference

### Files

| File | Purpose |
|------|---------|
| `.env.example` | Template for local dev |
| `k8s/secrets.yml` | Dev secrets (base64 encoded) |
| `k8s/external-secrets/vault-integration.yml` | Production Vault integration |

### Tools

- [External Secrets Operator](https://external-secrets.io/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## OIDC Client Secrets via Vault

For Task 40 (SSO / OIDC), store `client_secret` as a Vault reference instead of plaintext in the database. Configure the tenant's OIDC settings with:

```json
{
  "oidc": {
    "client_secret_ref": "vault:secret/value-fabric/oidc/{tenant-slug}"
  }
}
```

The application resolves the reference at runtime using the Vault KV v2 API. Rotate the secret in Vault without touching the database.

## Dynamic PostgreSQL Secrets

In production, use the Vault Database Secrets Engine to generate short-lived PostgreSQL credentials. See `k8s/external-secrets/vault-database-dynamic.yml` for the ExternalSecret manifest (1h TTL). Dynamic credentials are automatically rotated and revoked, reducing the blast radius of credential leaks.

## Verification

### Check ClusterSecretStore Status

```bash
# Verify ClusterSecretStore is Ready
kubectl get ClusterSecretStore vault-backend -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
# Expected output: True

# Check ExternalSecret sync status
kubectl get externalsecret -n value-fabric

# Check specific ExternalSecret details
kubectl describe externalsecret openai-api-key -n value-fabric
```

### Verify Secret Sync

```bash
# List secrets created by External Secrets Operator
kubectl get secrets -n value-fabric | grep -E "(openai|postgres|neo4j|jwt|layer)"

# Verify secret content (example: OpenAI API key)
kubectl get secret openai-secret -n value-fabric -o jsonpath='{.data.api-key}' | base64 -d
```

### Test Dynamic PostgreSQL Credentials

```bash
# Generate dynamic credentials from Vault
vault read database/creds/layer1-app

# Verify credentials work (requires psql)
export PGUSER=<username_from_vault>
export PGPASSWORD=<password_from_vault>
psql -h postgres.value-fabric.svc.cluster.local -U $PGUSER -d ingestion -c "SELECT current_user;"
```

## Troubleshooting ExternalSecret Sync

### Symptom: ExternalSecret shows `SecretSyncedError`

```bash
# Check ExternalSecret status
kubectl describe externalsecret <name> -n value-fabric

# Check External Secrets Operator logs
kubectl logs -n external-secrets deployment/external-secrets

# Verify Vault connectivity from cluster
kubectl run vault-test --rm -i --restart=Never --image=curlimages/curl \
  -- -s http://vault.vault.svc.cluster.local:8200/v1/sys/health
```

### Symptom: Dynamic credentials not rotating

```bash
# Check TTL on database role
vault read database/roles/layer1-app

# Verify database connection config
vault read database/config/postgres

# Check if credentials are being generated
vault read database/creds/layer1-app
```

## Smoke Gate

Before deploying to production, run the Vault smoke test to verify connectivity and secret access:

```bash
# Test Vault connectivity and secrets
export VAULT_ADDR=https://vault.value-fabric.svc:8200
export VAULT_TOKEN=<your-vault-token>
python scripts/smoke/vault_smoke.py

# Test ClusterSecretStore status
python scripts/smoke/clustersecretstore_check.py
```

A non-zero exit code blocks the deployment pipeline.

---

*Last updated: 2026-04-19*
