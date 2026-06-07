---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Deployment

This page documents the deployment environments, local development stack,
Kubernetes production manifests, secret management, database migrations, and
rolling deployment strategy for the Value Fabric platform.

## Deployment Environments

| Environment | Purpose | Orchestration | Secret Manager |
|---|---|---|---|
| **Local** | Developer workstations, feature validation | Docker Compose (`docker-compose.dev.yml`) | Infisical CLI or `.env` from `.env.example` |
| **Dev** | Integration testing, pre-PR validation | Kustomize (`k8s/deployments/dev-nginx`) | External Secrets Operator + Vault or Infisical |
| **Staging** | Production mirror, SHA-digest pinned images | Kustomize (`k8s/deployments/staging-nginx`) | External Secrets Operator + Vault |
| **Production** | Live customer workloads | Kustomize (`k8s/deployments/prod-nginx`) | External Secrets Operator + Vault / Infisical K8s Operator |

!!! danger "Dev auth bypass prohibition"
    The following flags are for local development only and will cause startup
    failure in production-like environments via `ProductionSafetyValidator`:
    `DEV_AUTH_BYPASS`, `ALLOW_DEV_AUTH_BYPASS`, `AUTH_BYPASS_ENABLED`,
    `ALLOW_INSECURE_DEV_AUTH_BYPASS`. Never set these in staging or production.

## Docker Compose Local Development Stack

The canonical local stack is defined in `docker-compose.dev.yml` at the repository
root. It spins up infrastructure and a subset of backend services for local
exploration.

### Services Included

| Service | Image | Ports | Purpose |
|---|---|---|---|
| `postgres` | `postgres:15-alpine` | `5432` | Relational store with multiple databases: `valuefabric`, `ingestion`, `ground_truth`, `layer4_agents`, `signal_refinery` |
| `pgbouncer` | `pgbouncer/pgbouncer:latest` | `6432` | Connection pooling |
| `minio` | `minio/minio:latest` | `9000`, `9001` | S3-compatible object storage |
| `redis` | `redis:7-alpine` | `6379` | Cache, pub/sub, Celery broker |
| `neo4j` | `neo4j:5-community` | `7474`, `7687` | Knowledge graph with APOC plugin |
| `keycloak` | `quay.io/keycloak/keycloak:25.0` | `8080` | OIDC/SAML identity broker |
| `layer2` | Build context: `services/layer2-extraction` | `8002` | Extraction API + Celery worker |
| `layer2-5` | Build context: `services/layer2-5-signal-refinery` | `8007` | Signal refinery |
| `layer4` | Build context: `services/layer4-agents` | `8004` | Agents API |
| `frontend` | Build context: `.` (Dockerfile: `apps/web/Dockerfile.dev`) | `3001` | Vite dev server |

### Starting the Stack

```bash
# Recommended: generate environment from Infisical
pnpm env:dev

# Start all services
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# Or start with build
docker compose -f docker-compose.dev.yml --env-file .env.generated up --build
```

!!! note "Legacy manual `.env`"
    If Infisical is unavailable, copy `.env.example` to `.env`, fill in the
    required values, and run `docker compose -f docker-compose.dev.yml up`.
    Never commit `.env` or `.env.generated`.

### Health Checks in Docker Compose

All services define native Docker health checks:

- **Postgres**: `pg_isready -U postgres`
- **PgBouncer**: `CMD-SHELL true` (connectivity validated via dependency)
- **MinIO**: `curl -f http://localhost:9000/minio/health/live`
- **Redis**: `redis-cli -a ${REDIS_PASSWORD} ping`
- **Neo4j**: `wget -q --spider http://localhost:7474/browser`
- **Keycloak**: TCP probe on `localhost:8080` with HTTP `GET /health/ready`
- **Layer 2/4**: Python urllib probe to `http://localhost:8000/health`
- **Frontend**: Node.js HTTP GET to `http://127.0.0.1:3001`

## Kubernetes Production Manifests

Production deployments use Kustomize with four composable axes:

```text
k8s/base/                    — Core workloads (Deployments, Services, ConfigMaps, NetworkPolicies, HPAs, PDBs)
k8s/envs/{dev,staging,prod}/ — Environment overlays (replicas, image pinning, ExternalSecrets)
k8s/routing/{nginx,gateway-api,istio}/ — External routing strategies
k8s/deployments/<env>-<routing>/ — Final deployable compositions
```

### Supported Deployment Targets

| Target | Environment | Routing | Status |
|---|---|---|---|
| `dev-nginx` | dev | NGINX Ingress + cert-manager | Supported |
| `staging-nginx` | staging | NGINX Ingress + cert-manager | Supported (pre-production validation) |
| `prod-nginx` | prod | NGINX Ingress + cert-manager | Supported (default production path) |
| `prod-gateway-api` | prod | Gateway API + cert-manager | Experimental |
| `prod-istio` | prod | Istio Gateway / VirtualService | Experimental (CI-render only) |

### Render and Deploy

```bash
# Render manifests for validation
kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone

# Dry-run against the API server
kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone | kubectl apply --dry-run=server -f -

# Deploy
kubectl apply -k k8s/deployments/prod-nginx
```

### Deployment Order

Deploy in dependency order to avoid cascading failures:

```bash
# 1. Namespace and secret backend
kubectl apply -f k8s/base/namespace.yml
kubectl apply -f k8s/external-secrets/vault-integration.yml

# 2. Config maps
kubectl apply -f k8s/base/configmap-global.yml

# 3. Infrastructure
kubectl apply -f k8s/base/postgres.yml
kubectl apply -f k8s/base/redis.yml
kubectl apply -f k8s/base/neo4j.yml

# Wait for infrastructure
kubectl wait --for=condition=ready pod -l app=postgres -n value-fabric --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n value-fabric --timeout=60s
kubectl wait --for=condition=ready pod -l app=neo4j -n value-fabric --timeout=180s

# 4. Application layers L1–L4
kubectl apply -f k8s/base/layer1-ingestion.yml
kubectl apply -f k8s/base/layer2-extraction.yml
kubectl apply -f k8s/base/layer3-knowledge.yml
kubectl apply -f k8s/base/layer4-agents.yml

# 5. Application layers L5–L6
kubectl apply -f k8s/base/layer5-ground-truth.yml
kubectl apply -f k8s/base/layer6-benchmarks.yml

# 6. Monitoring
kubectl apply -f k8s/base/monitoring-alertmanager.yml
```

## Environment Variable Management

### Local Development

Local development uses **Infisical CLI** as the preferred secret source:

```bash
# Export all paths to a single .env.generated
pnpm env:dev

# The export covers:
#   /shared, /infra, /layer1-ingestion, /layer2-extraction,
#   /layer2-5-signal-refinery, /layer3-knowledge, /layer4-agents,
#   /layer5-ground-truth, /layer6-benchmarks, /apps/web
```

If Infisical is unavailable, use `.env.example` as a path-annotated reference:

```bash
cp .env.example .env
# Fill in real values, then:
docker compose -f docker-compose.dev.yml up -d
```

### Production and Staging

Production uses the **External Secrets Operator** or **Infisical Kubernetes Operator**.
All secrets are stored in Vault or Infisical and synced into the cluster via
`ExternalSecret` or `InfisicalSecret` resources.

!!! warning "Never commit secrets"
    `k8s/secrets.yml` is a legacy local-only path blocked by CI guardrails.
    Kyverno policies reject unguarded Secret placeholder values at admission time.

### Critical Environment Variables

| Variable | Scope | Purpose |
|---|---|---|
| `DATABASE_URL` | L1–L6 | PostgreSQL async connection string |
| `DATABASE_URL_SYNC` | L1, L2, L4–L6 | PostgreSQL sync/psycopg connection string |
| `REDIS_URL` | All layers | Redis connection including password |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | L3, L4 | Graph database credentials |
| `JWT_SECRET` | All layers | Symmetric JWT signing (dev only; production uses Clerk OIDC) |
| `CLERK_SECRET_KEY` | API gateway | Clerk backend authentication |
| `CREDENTIALS_MASTER_KEY` | L4, L5 | Fernet field encryption key |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | All layers | Error tracking |

## Database Migrations

Value Fabric uses **Alembic** per service. Each maintained service layer manages
its own migration history.

### Running Migrations

```bash
# All layers
make migrate

# Per-layer (where applicable)
make migrate-layer1
make migrate-layer2
make migrate-layer4
make migrate-layer5
make migrate-api
```

### Migration Entrypoint Validation

Every service must have exactly one Alembic head. Validate before deploying:

```bash
make check-migration-heads
```

Additional migration governance checks:

```bash
make check-migration-entrypoints       # Validate entrypoints
make check-migration-rollback-policy   # Enforce rollback policy
make db-migrate-check                  # Read-only migration drift gate
make db-migrate-status                 # Emit read-only migration status artifacts
make check-migration-postgres-roundtrip # Live PostgreSQL round-trip test
```

!!! danger "Do not change models without migrations"
    Never modify database models without a corresponding Alembic migration.
    Preserve tenant fields, prefer additive migrations, and avoid destructive
    migrations unless explicitly required.

## Rolling Deployment Strategy

### Image Pinning and Registry

Service images are published to `ghcr.io/bmsull560/fabric_4l/<service>`.

- **Staging and production** use SHA256 digest pinning (immutable references).
- CI updates digests via:
  ```bash
  kustomize edit set image "ghcr.io/bmsull560/fabric_4l/layer4-agents@sha256:abc123..."
  ```

### Horizontal Pod Autoscaler (HPA)

| Service | Min | Max | Target Metric |
|---|---|---|---|
| `layer2-extraction` | 2 | 6 | 70% CPU |
| `layer4-agents` | 2 | 10 | 70% CPU / 80% memory |
| `frontend` | 2 | 8 | 70% CPU |

Scaling behavior:

- **Scale-up**: 100% increase per minute after 60s stabilization
- **Scale-down**: 50% decrease per minute after 300s stabilization

Requires `metrics-server` in the cluster.

### Pod Disruption Budgets

Critical services maintain availability during node disruptions:

- **layer4-agents**: `minAvailable: 1`

## Health Check Endpoints

All services expose health and readiness endpoints. Use these for load balancer
probes, Kubernetes readiness/liveness checks, and operational validation.

| Service | Health Endpoint | Notes |
|---|---|---|
| Layer 1 Ingestion | `/api/v1/ingestion/health` | Includes Celery worker connectivity |
| Layer 2 Extraction | `/health` | Includes database and Redis health |
| Layer 3 Knowledge | `/health` | Includes Neo4j connectivity |
| Layer 4 Agents | `/health` | Includes database, Redis, and Neo4j health |
| Layer 5 Ground Truth | `/api/v1/health` | Includes database health |
| Layer 6 Benchmarks | `/health` | Includes database health |
| API Gateway | `/health` | Includes upstream dependency health |
| Frontend | `/` | Returns `200 OK` when the Vite server is ready |

### Metrics Scraping

Prometheus metrics are available at `/metrics` on all backend services.

```bash
# Verify a local service
curl http://localhost:8004/health
curl http://localhost:8004/metrics

# Verify in Kubernetes
kubectl port-forward -n value-fabric svc/layer4-agents 8004:8004
curl http://localhost:8004/health
```

## Resource Requirements (Production)

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---|---|---|---|---|
| Neo4j | 500m | 2Gi | 2000m | 4Gi |
| Postgres | 100m | 256Mi | 500m | 1Gi |
| Redis | 100m | 128Mi | 500m | 512Mi |
| Layer 1–6 | 100m | 128Mi | 500m | 512Mi |

## Persistent Storage

| PVC | Size | Purpose |
|---|---|---|
| `neo4j-data` | 20Gi | Neo4j graph data |
| `neo4j-logs` | 5Gi | Neo4j logs |
| `postgres-pvc` | 10Gi | PostgreSQL data |

!!! note "Neo4j encryption policy"
    Neo4j PVCs require encrypted storage classes with compliance annotations:
    `storageClassName: encrypted-rwo`,
    `security.valuefabric.io/encryption-at-rest: "required"`,
    `security.valuefabric.io/kms-provider: "external"`.
    Production defaults to Aura-first deployment unless self-hosted Neo4j is
    explicitly enabled.
