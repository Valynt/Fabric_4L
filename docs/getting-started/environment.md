---
title: "Environment Configuration Guide"
category: "getting-started"
audience: "intermediate"
last-reviewed: "2026-06-12"
freshness: "current"
related: ["quickstart", "../core-concepts/security-model", "../core-concepts/architecture", "../how-to-guides/setup-local-dev", "../troubleshooting/authentication-errors", "../troubleshooting/index", "../reference/layer1-ingestion-api"]
---

# Environment Configuration Guide

> **In this guide, you will:**
> - Understand environment variable classification and security
> - Configure local development environments
> - Set up staging and production configurations
> - Validate and troubleshoot environment issues

---

## Prerequisites

Before configuring your environment:

1. Complete the [Quickstart Guide](./quickstart.md)
2. Obtain necessary credentials:
   - OpenAI API key
   - JWT secret (generate with `openssl rand -hex 32`)
   - Optional: Infisical access for team development

---

## Environment Architecture

```mermaid
graph TB
    subgraph "Variable Classification"
        A[🔴 Class A<br/>Secrets<br/>Infisical Only]
        B[🟠 Class B<br/>Sensitive Config<br/>Infisical/Git]
        C[🟢 Class C<br/>Public Config<br/>Git Committed]
        D[🔵 Class D<br/>Local Dev<br/>Never Deployed]
    end

    subgraph "Environments"
        DEV[Development<br/>Local]
        TEST[Test<br/>CI/Local]
        STAGE[Staging<br/>Cloud]
        PROD[Production<br/>Cloud]
    end

    subgraph "Storage"
        INF[Infisical<br/>Vault]
        GIT[Git Repo<br/>Contracts]
        LOCAL[.env.local<br/>Ignored]
    end

    A --> INF
    B --> INF
    B --> GIT
    C --> GIT
    D --> LOCAL

    INF --> DEV
    INF --> STAGE
    INF --> PROD
    GIT --> DEV
    GIT --> TEST
    GIT --> STAGE
    GIT --> PROD
    LOCAL --> DEV

    style A fill:#e74c3c,color:white
    style B fill:#e67e22,color:white
    style C fill:#2ecc71,color:white
    style D fill:#4a90d9,color:white
    style INF fill:#9b59b6,color:white
```

---

## Variable Classification

### Class A: Secrets (🔴 Critical)

**Never committed to Git. Stored in Infisical only.**

| Variable | Purpose | Rotation |
|----------|---------|----------|
| `OPENAI_API_KEY` | LLM provider access | 90 days |
| `ANTHROPIC_API_KEY` | Alternative LLM | 90 days |
| `JWT_SECRET` | Token signing | 180 days |
| `API_KEY_HMAC_SECRET` | API key validation | 180 days |
| `NEO4J_PASSWORD` | Graph database | 90 days |
| `POSTGRES_PASSWORD` | Relational database | 90 days |

**Example:**
```bash
# From Infisical - never in .env files
OPENAI_API_KEY=sk-abc123...
JWT_SECRET=a3f5c7e9...
```

### Class B: Sensitive Config (🟠 High)

**May be in Infisical or committed contracts.**

| Variable | Purpose | Example |
|----------|---------|---------|
| `VAULT_ADDR` | HashiCorp Vault URL | `https://vault.internal:8200` |
| `CRM_INSTANCE_URL` | Salesforce/HubSpot URL | `https://instance.salesforce.com` |
| `INTERNAL_API_BASE` | Internal service URLs | `https://api.internal` |

### Class C: Public Config (🟢 Safe)

**Committed to Git. Safe for frontend exposure.**

| Variable | Purpose | Example |
|----------|---------|---------|
| `VITE_API_BASE_URL` | Frontend API endpoint | `/api/v1` |
| `VITE_ENABLE_QUERY_DEVTOOLS` | Debug tools | `true` (dev only) |
| `VITE_ENABLE_WEB_VITALS` | Local opt-in for frontend RUM metrics; staging/production enable automatically | `false` |
| `LAYER1_PORT` | Service port | `8001` |
| `ENVIRONMENT` | Environment name | `development` |

### Class D: Local Dev (🔵 Convenience)

**Local `.env.local` files only. Never relied on for correctness.**

| Variable | Purpose | Example |
|----------|---------|---------|
| `DEBUG_MODE` | Extra logging | `true` |
| `MOCK_LLM` | Use fake LLM | `true` |
| `SKIP_RATE_LIMITS` | Disable limits | `true` |
| `DEV_SEED_ADMIN_PASSWORD` | Local demo admin seed password | explicit local value |
| `DEV_SEED_ANALYST_PASSWORD` | Local demo analyst seed password | explicit local value |

Demo seed user passwords have no production-code defaults. Set `DEV_SEED_ADMIN_PASSWORD` and `DEV_SEED_ANALYST_PASSWORD` only when intentionally seeding local demo users in a non-production environment. Do not deploy these variables to production.

---

## Required Variables

### Backend services (services/)

```bash
# Class A - Required
OPENAI_API_KEY=sk-...                    # From OpenAI dashboard
JWT_SECRET=$(openssl rand -hex 32)       # Generate new
API_KEY_HMAC_SECRET=$(openssl rand -hex 32)
NEO4J_PASSWORD=...                         # Neo4j auth
POSTGRES_PASSWORD=fabric                 # Database auth

# Class C - Required
ENVIRONMENT=development                    # dev/staging/production
LAYER1_PORT=8001                             # Layer 1 port
LAYER2_PORT=8002                             # Layer 2 port
LAYER3_PORT=8003                             # Layer 3 port
LAYER4_PORT=8004                             # Layer 4 port
DATABASE_URL=postgresql://fabric:fabric@localhost:5432/fabric
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
```

### Frontend (apps/web/)

```bash
# Class C - All public, all safe to commit
VITE_API_BASE_URL=/api/v1
VITE_PROXY_L1_URL=http://localhost:8001
VITE_PROXY_L2_URL=http://localhost:8002
VITE_PROXY_L3_URL=http://localhost:8003
VITE_PROXY_L4_URL=http://localhost:8004
VITE_PROXY_L5_URL=http://localhost:8005
VITE_PROXY_L6_URL=http://localhost:8006
VITE_ENABLE_QUERY_DEVTOOLS=true          # Dev only
VITE_API_LOG_LEVEL=debug                 # Dev only
VITE_ENVIRONMENT=development
VITE_APP_VERSION=local
VITE_JAEGER_ENDPOINT=http://localhost:4318/v1/traces
VITE_ENABLE_WEB_VITALS=false             # Set true only to collect local RUM/web-vitals
```

---

## Setup Instructions

### Option 1: With Infisical (Recommended for Teams)

Infisical provides secure secret management with automatic injection.

```mermaid
sequenceDiagram
    participant D as Developer
    participant I as Infisical CLI
    participant INF as Infisical Cloud
    participant S as Service

    D->>I: infisical login
    I->>INF: Authenticate
    INF-->>I: Token

    D->>I: infisical run --env=dev
    I->>INF: Fetch secrets
    INF-->>I: Decrypted secrets
    I->>S: Inject as env vars
    S->>S: Start with secrets
```

**Setup:**

```bash
# 1. Install Infisical CLI
# macOS
brew install infisical/get-cli/infisical

# Linux/WSL
brew install infisical/get-cli/infisical

# Windows (PowerShell)
winget install Infisical.infisical

# 2. Authenticate
infisical login

# 3. Run backend with secrets
infisical run --env=dev --path=/fabric-4l/dev -- \
  docker compose up -d

# 4. Run frontend
infisical run --env=dev --path=/fabric-4l/apps/web/dev -- \
  pnpm run dev
```

### Option 2: Manual .env (Local-Only Quick Start)

For solo development or quick testing. Manual `.env` files are local-only and
must not become Kubernetes `Secret` manifests.

```bash
# 1. Copy example file
cp .env.example .env

# 2. Edit .env with your values
# - Add OPENAI_API_KEY
# - Generate JWT_SECRET
# - Configure database URLs if not using defaults

# 3. Start services
docker compose up -d
```

### Kubernetes Secret Injection

Cluster deployments must use injected secret paths wherever possible:

- Use `ExternalSecret` resources under `k8s/external-secrets/` for Vault-backed secrets.
- Use Infisical `InfisicalSecret` resources under `k8s/infisical/` for Infisical-backed secrets.
- Do not commit direct Kubernetes `Secret` manifests with real values.
- Direct dev-only `Secret` manifests are allowed only when they carry
  `value-fabric.io/non-prod-only: "true"`,
  `value-fabric.io/secret-scope: dev-placeholder`, and an explicit
  `value-fabric.io/allowed-namespaces` annotation. Kyverno admission policy
  rejects these if they are applied to staging or production namespaces.

**Validation Checklist:**

```bash
# Verify all required vars are set
grep -E '^(OPENAI_API_KEY|JWT_SECRET|DATABASE_URL)=' .env

# Check for placeholder values
grep 'changeme\|placeholder\|example' .env

# Test connectivity
make verify
```

---

## Environment Validation

### Startup Validation

Services validate environment before starting:

```python
# Backend validation example
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    openai_api_key: str
    jwt_secret: str
    database_url: str

    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        if v == 'changeme-in-production':
            raise ValueError('JWT_SECRET must be changed from default')
        if len(v) < 32:
            raise ValueError('JWT_SECRET must be at least 32 characters')
        return v

    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('OPENAI_API_KEY must start with sk-')
        return v

# If validation fails, service exits immediately
settings = Settings()  # Validates on instantiation
```

### Manual Validation

```bash
# Check env file validity
npx tsx scripts/dev/check-env.ts

# Expected output:
# ✓ OPENAI_API_KEY: valid format
# ✓ JWT_SECRET: 64 characters
# ✓ DATABASE_URL: valid connection string
# ✓ All required variables present

# Test connections
make verify
```

---

## Environment-Specific Configurations

### Development

```bash
# Development goals: Fast feedback, verbose logging, local services

# .env.development
ENVIRONMENT=development
LOG_LEVEL=debug
DEBUG_MODE=true
ENABLE_SWAGGER=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Local service ports
LAYER1_PORT=8001
LAYER2_PORT=8002
LAYER3_PORT=8003
LAYER4_PORT=8004

# Local databases
DATABASE_URL=postgresql://fabric:fabric@localhost:5432/fabric
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
```

### Staging

```bash
# Staging goals: Production-like, isolated testing

# .env.staging
ENVIRONMENT=staging
LOG_LEVEL=info
DEBUG_MODE=false
ENABLE_SWAGGER=true  # For API testing

# Cloud services (placeholder URLs)
DATABASE_URL=postgresql://...:5432/fabric_staging?sslmode=verify-full
REDIS_URL=redis://...:6379/0
NEO4J_URI=neo4j+s://...
```

### Production

```bash
# Production goals: Security, performance, reliability

# .env.production
ENVIRONMENT=production
LOG_LEVEL=warn
DEBUG_MODE=false
ENABLE_SWAGGER=false
CORS_ORIGINS=https://app.valuefabric.io

# Strict security
JWT_TOKEN_EXPIRY=3600  # 1 hour
API_KEY_RATE_LIMIT=600  # requests per minute
MAX_UPLOAD_SIZE=10485760  # 10MB

# Cloud services
DATABASE_URL=postgresql://...:5432/fabric_prod?sslmode=verify-full
REDIS_URL=redis://...:6379/0
NEO4J_URI=neo4j+s://...
```

Production-like environments (`production` and `staging`) must set database TLS
explicitly on `DATABASE_URL`. Startup validation accepts only
`sslmode=require`, `sslmode=verify-ca`, or `sslmode=verify-full`; `verify-full`
is preferred.

---

## Troubleshooting

### Common Issues

#### JWT_SECRET Not Set

**Symptoms:**
```
Error: JWT_SECRET must be set in production
```

**Resolution:**
```bash
# Generate secure secret
export JWT_SECRET=$(openssl rand -hex 32)
echo "JWT_SECRET=$JWT_SECRET" >> .env
```

#### OpenAI API Key Invalid

**Symptoms:**
```
Error: OPENAI_API_KEY must start with sk-
```

**Resolution:**
```bash
# Verify key format
echo $OPENAI_API_KEY | grep '^sk-'

# Get new key from OpenAI dashboard
# https://platform.openai.com/api-keys
```

#### Database Connection Failed

**Symptoms:**
```
Error: Unable to connect to postgresql://localhost:5432/fabric
```

**Resolution:**
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Verify connection string
psql $DATABASE_URL -c "SELECT 1"

# Reset database if needed
docker compose down -v postgres
docker compose up -d postgres
make migrate
```

#### Port Already in Use

**Symptoms:**
```
Error: Address already in use :::8001
```

**Resolution:**
```bash
# Find process using port
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Change port in .env
LAYER1_PORT=8002
```

---

## Security Checklist

### Production Deployment

- [ ] All secrets in Infisical (not in Git)
- [ ] Kubernetes secrets sourced through `ExternalSecret` or Infisical, not direct `Secret` manifests
- [ ] Placeholder scan passes for manifests and runtime cluster:
  `python scripts/security/placeholder_secret_scan.py k8s --allow-guarded-dev`
- [ ] JWT_SECRET > 32 characters, not default
- [ ] DEBUG_MODE=false
- [ ] ENABLE_SWAGGER=false
- [ ] LOG_LEVEL=warn or info
- [ ] CORS restricted to production domains
- [ ] API rate limiting enabled
- [ ] Database credentials rotated
- [ ] TLS/SSL for all connections
- [ ] Secrets encryption at rest

---

## Related Documentation

- [Quickstart Guide](./quickstart.md) — Get running quickly
- [Security Model](../core-concepts/security-model.md) — Deep dive on security
- [Local Development Setup](../how-to-guides/setup-local-dev.md) — Full dev environment
- [Troubleshooting Authentication](../troubleshooting/authentication-errors.md) — Debug auth issues

---

*Last updated: 2026-06-12 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/getting-started/environment.md)*


## Release Approval Reliability Requirement

For production/staging release approvals, SLO review is mandatory:

- Attach latest `artifacts/performance/slo-report.md` and `artifacts/performance/slo-evaluation.json`.
- Confirm the relevant layer/service owner reviewed error budget and burn-rate status.
- Block release if burn-rate threshold breaches are unresolved.

See `docs/troubleshooting/runbooks/infrastructure/release-checklist.md` and `docs/operations/reliability-policy.md`.

## Contributor Pathing Reference

- [Layer Runtime Path Governance Matrix](../reference/layer-runtime-path-governance.md) — Where to add new layer code vs compatibility-only paths

---

## Reproduce `make verify` Locally

Use this sequence to match CI prerequisites and execution order:

```bash
# 1) Toolchain parity
corepack enable
corepack prepare pnpm@10.34.5 --activate
python3 --version  # expected: 3.11.x
node --version     # expected: 22.x
pnpm --version     # expected: 10.34.5

# 2) Install JavaScript dependencies
pnpm install --frozen-lockfile

# 3) Install Python test/runtime dependencies used by verify
pip install -r tests/requirements-test.txt
pip install -e services/api
pip install -e services/layer1-ingestion
pip install -e services/layer2-extraction
pip install -e services/layer3-knowledge
pip install -e services/layer4-agents
pip install -e services/layer5-ground-truth
pip install -e services/layer6-benchmarks

# 4) Run the full gate
make verify
```

Expected environment:
- Linux/macOS shell with `bash`, `make`, `python3`, `pip`, `node`, `pnpm` available.
- Repository root as working directory (`/workspace/Fabric_4L` in containerized dev).
- Network access for first-time dependency resolution.
