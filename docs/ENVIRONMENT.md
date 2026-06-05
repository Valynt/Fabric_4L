# Environment Variable Standard

> **Governing rule:** Infisical stores real secrets. Git stores env contracts.
> Services validate env at startup.

This document defines how environment variables are managed across Value Fabric.

---

## Variable Classification

Every variable falls into one of four classes:

| Class | Description | Storage | Example |
|-------|-------------|---------|---------|
| **A** | Secret, backend-only | Infisical only — never committed | `OPENAI_API_KEY`, `JWT_SECRET` |
| **B** | Sensitive non-secret backend config | Infisical or committed contract files | `CRM_INSTANCE_URL`, `VAULT_ADDR` |
| **C** | Public frontend config | Committed `.env.*` files — safe for browser | `VITE_API_BASE_URL`, `VITE_ENABLE_QUERY_DEVTOOLS` |
| **D** | Local-only developer convenience | Local `.env.local` — never relied on for correctness | Mock toggles, debug flags |

### Class A — Secret, backend-only

- Stored in Infisical, never committed to git
- Injected at runtime
- Validated at startup via Zod schema
- Rotated centrally through Infisical

Variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `JWT_SECRET`, `API_KEY_HMAC_SECRET`,
`NEO4J_PASSWORD`, `PINECONE_API_KEY`, `BROWSERBASE_API_KEY`, `FIRECRAWL_API_KEY`,
`THESYS_API_KEY`

### Class B — Sensitive but non-secret backend config

- May live in Infisical for consistency
- Validated at startup
- Not exposed to frontend

Variables: `CRM_INSTANCE_URL`, `VAULT_ADDR`, private internal base URLs

### Class C — Public frontend config

- Safe to expose to browser (VITE_* prefix)
- Committed to git in `.env.*` files
- Must never contain credentials

Variables: `VITE_API_BASE`, `VITE_ENABLE_QUERY_DEVTOOLS`, `VITE_API_LOG_LEVEL`,
`VITE_ENVIRONMENT`, `VITE_APP_VERSION`, `VITE_JAEGER_ENDPOINT`,
`VITE_ENABLE_WEB_VITALS`

### Class D — Local-only developer convenience

- Allowed in `.env.local` files only
- Never relied on for correctness
- Production/staging must not depend on them

---

## File Layout

```
Fabric_4L/
├─ .infisical.json             # Infisical project/path mapping
├─ services/
│  ├─ .env.example             # Full variable list with placeholders
│  ├─ .env.test                # Deterministic test values
│  ├─ .env.staging             # Staging shape with placeholders
│  └─ .env.production.example  # Production contract, no real secrets
├─ frontend/
│  ├─ .env.example             # Full VITE_* variable list
│  ├─ .env.development         # Dev-mode settings
│  ├─ .env.test                # Test-mode settings
│  ├─ .env.staging             # Staging settings
│  ├─ .env.production          # Production settings
│  └─ client/
│     └─ .env.example          # Inner client config
└─ packages/
   └─ config/
      └─ src/env/
         ├─ shared.ts           # Common schema fragments
         ├─ backend.ts          # Backend Zod schema
         ├─ frontend.ts         # Frontend Zod schema
         └─ test.ts             # Test-relaxed schema
```

### What each file means

| File | Purpose |
|------|---------|
| `.env.example` | Full supported variable list with comments, harmless defaults, placeholder values |
| `.env.test` | Deterministic test-only values, localhost endpoints, fake credentials |
| `.env.staging` | Same shape as prod, placeholder secrets, stage-safe defaults |
| `.env.production.example` | Exact production contract — no real secrets |
| `.env.development` | Development convenience values |
| `.env.production` | Production public (frontend only — no secrets) |

---

## Startup Validation

Each service **must** parse and validate env before doing anything else.

### Backend

```typescript
import { loadBackendEnv } from "@fabric/config/env/backend";

const env = loadBackendEnv(process.env);
// If env is invalid, startup fails immediately with a clear error.
```

### Frontend

```typescript
import { loadFrontendEnv } from "@fabric/config/env/frontend";

const env = loadFrontendEnv(import.meta.env);
```

The Zod schemas are defined in `packages/config/src/env/`.

---

## Local Development

Developers should not manually maintain secret-filled `.env` files.

### With Infisical (recommended)

```bash
# One-time setup
./scripts/infisical/bootstrap-dev.sh

# Run backend
infisical run --env=dev --path=/fabric-4l/value-fabric/dev -- pnpm --dir value-fabric dev

# Run frontend
infisical run --env=dev --path=/fabric-4l/frontend/dev -- pnpm --dir frontend dev
```

### Without Infisical (fallback)

```bash
cd value-fabric
cp .env.example .env
# Edit .env with real values
```

---

## CI/CD

CI uses machine identities — never human user tokens.

### Pipeline steps

1. **Inject secrets:** `infisical run --env=staging --path=/fabric-4l/value-fabric/staging -- ...`
2. **Validate contract:** `npx tsx scripts/ci/validate-env-contract.ts all`
3. **Build and test:** With validated config
4. **Deploy:** Same environment scope as workload

---

## Infisical Path Design

Secrets are organized by app and environment:

```
/fabric-4l/value-fabric/dev
/fabric-4l/value-fabric/test
/fabric-4l/value-fabric/staging
/fabric-4l/value-fabric/prod

/fabric-4l/frontend/dev
/fabric-4l/frontend/test
/fabric-4l/frontend/staging
/fabric-4l/frontend/prod
```

Future granular split:

```
/fabric-4l/api/prod
/fabric-4l/worker/prod
/fabric-4l/ingestion/prod
/fabric-4l/crawler/prod
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check-env.ts` | Quick local env validation |
| `scripts/infisical/bootstrap-dev.sh` | Linux/macOS dev setup |
| `scripts/infisical/bootstrap-dev.ps1` | Windows dev setup |
| `scripts/infisical/verify-secrets.ts` | Verify Infisical paths have required keys |
| `scripts/ci/validate-env-contract.ts` | CI gate — validates env contract + schema |

---

*See also: [SECRETS.md](./SECRETS.md) for rotation procedures and Infisical administration.*
