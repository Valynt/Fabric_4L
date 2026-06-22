# Fabric4L Secrets Management

> Source of truth for how Fabric4L manages secrets across local development, CI/CD, and production.
> For the full Infisical architecture rationale, see the canonical design document in the project wiki.

---

## Infisical Project

| Property   | Value      |
|------------|------------|
| Project    | `Fabric4L` |
| Environments | `dev`, `staging`, `prod` |

All secrets live in **one Infisical project** with three environments. The environment is selected by Infisical at runtime, not encoded into variable names.

---

## Secret Path Structure

Paths mirror the monorepo architecture:

```text
/shared
/infra
/apps/web
/layer1-ingestion
/layer2-extraction
/layer2-5-signal-refinery
/layer3-knowledge
/layer4-agents
/layer5-ground-truth
/layer6-benchmarks
/monitoring
/ci
```

### Path responsibilities

| Path | Purpose |
|------|---------|
| `/shared` | Cross-service configuration: `APP_ENV`, `JWT_ISSUER`, `LOG_LEVEL`, `PUBLIC_APP_URL` |
| `/infra` | Infrastructure credentials: Postgres, Redis, MinIO, Neo4j |
| `/apps/web` | Frontend runtime / build variables (public `VITE_*` only) |
| `/layer{N}` | Service-specific secrets: API keys, DB URLs, model configs |
| `/monitoring` | Prometheus, Grafana, Sentry, Alertmanager credentials |
| `/ci` | CI-specific non-OIDC tokens (fallback only) |

---

## Local Development

### Prerequisites

Install the Infisical CLI and log in:

```bash
infisical login
```

### Running a single service

```bash
# Layer 4 Agents
infisical run \
  --env=dev \
  --path=/shared \
  --path=/infra \
  --path=/layer4-agents \
  -- uvicorn services.layer4-agents.src.api.main:app --reload

# Frontend
infisical run \
  --env=dev \
  --path=/shared \
  --path=/apps/web \
  -- pnpm --filter web dev
```

### Running the full Docker Compose stack

Generate a temporary env file first:

```bash
infisical export \
  --env=dev \
  --path=/shared \
  --path=/infra \
  --path=/layer1-ingestion \
  --path=/layer2-extraction \
  --path=/layer2-5-signal-refinery \
  --path=/layer3-knowledge \
  --path=/layer4-agents \
  --path=/layer5-ground-truth \
  --path=/layer6-benchmarks \
  --path=/apps/web \
  --format=dotenv \
  --output-file=.env.generated

docker compose --env-file .env.generated -f docker-compose.dev.yml up
```

Or use the root helper script:

```bash
pnpm env:dev    # generates .env.generated
pnpm compose:dev # docker compose up with .env.generated
```

### Offline fallback

If you do not have Infisical CLI access, copy `.env.example` to `.env`, fill in real values, and run services directly. This path is **not recommended** for team development because it drifts from the canonical source of truth.

---

## CI/CD

### Preferred pattern: GitHub OIDC → Infisical Machine Identity

GitHub Actions authenticate with Infisical via short-lived OIDC tokens. No long-lived secrets are stored in GitHub.

Example workflow step:

```yaml
- name: Fetch Infisical secrets
  uses: Infisical/secrets-action@v1
  with:
    method: oidc
    env-slug: staging
    project-slug: fabric4l
    identity-id: ${{ secrets.INFISICAL_IDENTITY_ID }}
```

### Machine identities

| Identity | Environment | Paths |
|----------|-------------|-------|
| `fabric4l-ci-dev` | `dev` | `/shared`, `/infra`, all service paths |
| `fabric4l-ci-staging` | `staging` | `/shared`, `/infra`, required deploy paths |
| `fabric4l-ci-prod` | `prod` | production deploy paths only |

Production identities should have **read-only** access unless CI explicitly rotates secrets.

---

## Kubernetes (Production)

The Infisical Kubernetes Operator syncs secrets from Infisical into native Kubernetes `Secret` objects.

Manifests live in `k8s/infisical/`. Each `InfisicalSecret` CRD maps one or more paths to a K8s secret that is then mounted into pods via `envFrom`.

Prerequisites:
1. Install the Infisical operator:
   ```bash
   helm repo add infisical-helm-charts https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/
   helm install infisical-operator infisical-helm-charts/secrets-operator
   ```
2. Create the machine identity credentials secret (once per cluster):
   ```bash
   kubectl create secret generic infisical-universal-auth \
     --from-literal=clientId=<CLIENT_ID> \
     --from-literal=clientSecret=<CLIENT_SECRET> \
     -n value-fabric
   ```

---

## Naming Standards

- **Uppercase snake_case**: `DATABASE_URL`, `TOGETHER_API_KEY`
- **No environment prefixes**: use `NEO4J_URI`, not `PROD_NEO4J_URI`
- **Boolean suffix**: `FEATURE_X_ENABLED=true`
- **Duration suffix**: `GRAPH_QUERY_TIMEOUT_MS=5000`
- **Frontend public variables**: must start with `VITE_`; never put backend secrets in `/apps/web`

---

## Rotation Policy

| Secret Type | Rotation Interval |
|-------------|-------------------|
| Production DB passwords | 90 days |
| LLM provider API keys | 90 days |
| Webhook signing secrets | 90 days |
| JWT signing keys | 90 days |
| CI/OIDC tokens | N/A (short-lived) |
| Local dev credentials | As needed |
| Break-glass credentials | Immediately after use |

---

## Security Rules

- [x] Do not commit `.env`, `.env.generated`, or `.infisical-token`.
- [x] Do not store production secrets in GitHub Secrets if OIDC is available.
- [x] Do not give frontend developers access to backend production secrets by default.
- [x] Do not expose private secrets through `VITE_` variables.
- [x] Do not reuse dev/staging/prod API keys across environments.
- [x] Scan the repo for leaked secrets: `infisical scan --recursive`.

## CI fail-closed policy

CI workflows must fetch runtime secrets via Infisical OIDC and fail hard when retrieval fails. Do not add fallback values for `OPENAI_API_KEY` or `JWT_SECRET` in workflow YAML. For incident recovery and emergency rotation, use `docs/runbooks/operational/ci-infisical-oidc-recovery.md`.

---

## Secrets Inventory

### Class A — Required (startup will fail without these)

| Secret | Used By | Purpose |
|--------|---------|---------|
| `OPENAI_API_KEY` | L1, L2, L4 | LLM API calls |
| `JWT_SECRET` | L4, L5, shared/identity | Token signing (≥ 32 chars) |
| `API_KEY_HMAC_SECRET` | shared/identity | API key hashing (≥ 32 chars) |
| `NEO4J_PASSWORD` | L2, L3, L4 | Graph database auth |

### Class A — Optional (feature-gated)

| Secret | Used By | Purpose |
|--------|---------|---------|
| `ANTHROPIC_API_KEY` | L4 | Alternative LLM provider |
| `PINECONE_API_KEY` | L3 | Vector search backend |
| `BROWSERBASE_API_KEY` | L1 | Browser automation |
| `FIRECRAWL_API_KEY` | L1 | Web scraping API |
| `CRM_API_KEY` | L4 | CRM integration (when CRM_TYPE ≠ none) |
| `CRM_API_SECRET` | L4 | CRM OAuth refresh token |
| `THESYS_API_KEY` | L4 | Thesys C1 generative UI |
| `LAYER3_API_KEY` | L5 | Inter-layer auth |

### Class B — Infrastructure

| Variable | Used By | Purpose |
|----------|---------|---------|
| `POSTGRES_PASSWORD` | L1, L4, L5 | SQL database auth |
| `VAULT_ADDR` | All layers | Vault endpoint |
| `CRM_INSTANCE_URL` | L4 | CRM endpoint URL |

---

## Detailed Rotation Procedures

### LLM API Keys (OpenAI, Anthropic)

1. Generate new key in provider dashboard
2. Update in Infisical for the target environment
3. Restart affected services (L1, L2, L4)
4. Verify health
5. Revoke old key in provider dashboard

### JWT_SECRET

> ⚠️ **CRITICAL:** Rotating JWT_SECRET invalidates all existing tokens.

1. Schedule maintenance window
2. Update in Infisical
3. Restart L4, L5, and any service using shared/identity
4. All users must re-authenticate
5. Monitor for auth errors

### API_KEY_HMAC_SECRET

> ⚠️ **CRITICAL:** Rotating this invalidates all existing API keys.

1. Schedule maintenance window
2. Re-hash all existing API keys with the new secret
3. Update in Infisical
4. Restart all services using shared/identity
5. Verify API key authentication works

### Database Passwords (Neo4j, PostgreSQL)

1. Update password in the database first
2. Update in Infisical
3. Restart affected services
4. Verify connectivity

#### Neo4j Secret Contract (required)

- **Application workloads (L2/L3/L4 and other Neo4j clients)** must source `NEO4J_USER` and `NEO4J_PASSWORD` from dedicated keys (`neo4j_user` and `neo4j_password`, or equivalent dedicated key names).
- **Application workloads must not** source `NEO4J_PASSWORD` from `auth`/`NEO4J_AUTH` keys.
- `NEO4J_AUTH` should be used only by the Neo4j server container bootstrap path where Neo4j expects `user/password` format.
- CI enforces this via `python3 scripts/ci/check_neo4j_secret_key_mappings.py`.

---

## Infisical Access Control

### Project Structure

```
/fabric-4l/value-fabric/{dev,test,staging,prod}
/fabric-4l/frontend/{dev,test,staging,prod}
```

### Role-Based Access

| Role | Access |
|------|--------|
| Developer | Read dev, test |
| CI pipeline | Read test, staging (machine identity) |
| Deploy pipeline | Read staging, prod (machine identity) |
| Admin | Read/write all environments |

### Adding a New Secret

1. Add the key to `.env.example` (with placeholder value)
2. Add validation to `packages/config/src/env/backend.ts` (or `frontend.ts`)
3. Add the real value to the appropriate Infisical paths
4. Update this document's inventory table
5. Run `npx tsx scripts/check-env.ts` to verify

---

## Local Development: Vault Dev Mode

The file `docker-compose.full.dev-vault.yml` starts Vault in **dev mode** for
local secret management. Dev mode is intentionally insecure and should
**never** be used outside of a local developer workstation.

### Vault Root Token

The Vault dev root token is controlled by the `VAULT_DEV_ROOT_TOKEN_ID`
environment variable:

```bash
# .env
VAULT_DEV_ROOT_TOKEN_ID=my-local-dev-token
```

If the variable is not set it defaults to `root`, which is a well-known value
and **must not** be used in any shared or long-lived environment (CI, staging,
production).

**Best practice:** Set `VAULT_DEV_ROOT_TOKEN_ID` to a random token in your
personal `.env`:

```bash
# Generate a random token
python3 -c "import secrets; print(secrets.token_hex(16))"
# Add to .env
echo "VAULT_DEV_ROOT_TOKEN_ID=<generated-token>" >> .env
```

Then start Vault:

```bash
docker compose -f docker-compose.full.dev-vault.yml --profile local-dev up -d vault
```

### Vault in CI and Staging

- CI uses mock secret backends — Vault dev mode is not started.
- Staging uses production-mode Vault with TLS and auto-unseal; see
  `k8s/base/vault/` for configuration.
