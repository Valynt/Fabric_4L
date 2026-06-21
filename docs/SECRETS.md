# Secrets Management

> **Governing rule:** Infisical stores real secrets. Git stores env contracts.
> Services validate env at startup.

This document covers secrets storage, rotation, and operational procedures.
For variable classification and file layout, see [ENVIRONMENT.md](./ENVIRONMENT.md).

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

## Infisical Administration

### Project Structure

```
/fabric-4l/value-fabric/{dev,test,staging,prod}
/fabric-4l/frontend/{dev,test,staging,prod}
```

### Access Control

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

## Rotation Procedures

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

## CI/CD Secrets

### Machine Identities

CI uses Infisical machine identities — never human user tokens.

```yaml
# Example GitHub Actions step
- name: Inject secrets
  run: |
    infisical run --env=staging \
      --path=/fabric-4l/value-fabric/staging \
      -- sh -c 'cd apps/web && pnpm run test'
  env:
    INFISICAL_TOKEN: ${{ secrets.INFISICAL_MACHINE_TOKEN }}
```

### Least Privilege

Each pipeline stage gets only the secrets it needs:

| Stage | Infisical Path | Access |
|-------|---------------|--------|
| Unit tests | `/fabric-4l/value-fabric/test` | Read |
| Integration tests | `/fabric-4l/value-fabric/staging` | Read |
| Deploy staging | `/fabric-4l/value-fabric/staging` | Read |
| Deploy prod | `/fabric-4l/value-fabric/prod` | Read |

---

## Security Best Practices

- **Never commit secrets to git** — use `.env.example` for templates
- **Rotate keys quarterly** — set calendar reminders
- **Use least privilege** — scope API keys to minimum required permissions
- **Monitor key usage** — set up alerts for unusual activity
- **Validate at startup** — use `loadBackendEnv()` / `loadFrontendEnv()`
- **Audit access** — Infisical provides access logs out of the box

---

*See also: [ENVIRONMENT.md](./ENVIRONMENT.md) for variable classification and file layout.*
*See also: [secrets-management.md](./secrets-management.md) for Kubernetes/Vault specifics.*
