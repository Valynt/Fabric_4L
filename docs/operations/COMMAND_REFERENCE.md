# Reliable Command Reference — Fabric_4L Environment

Canonical Copy-Pasteable Commands for Build, Deploy, Test, and Operations.

**Context:** Vite/React frontend, Python FastAPI backend services, PostgreSQL, Redis, Neo4j, Docker Compose, Kubernetes  
**Monorepo Standard:** pnpm 10.18.1 (Node.js ≥ 22.12.0), Python 3.11+, Docker Compose v2 (`docker compose`)  
**Assumptions:** Repository root at `Fabric_4L/`, frontend at `apps/web/`, backend services at `services/layer*-*/`, shared package at `packages/shared/`

---

## TABLE OF CONTENTS

1. [Docker & Container Operations](#1-docker--container-operations)
2. [Backend Build & Startup](#2-backend-build--startup)
3. [Frontend Build & Startup](#3-frontend-build--startup)
4. [Database Operations](#4-database-operations)
5. [Testing Commands](#5-testing-commands)
6. [Health & Validation](#6-health--validation)
7. [Kubernetes Operations](#7-kubernetes-operations)
8. [Monitoring & Observability](#8-monitoring--observability)
9. [Git & Version Control](#9-git--version-control)
10. [Debugging & Diagnostics](#10-debugging--diagnostics)
11. [One-Line Validation Chains](#11-one-line-validation-chains)
12. [Environment Setup Scripts & Common Operations](#12-environment-setup-scripts--common-operations)

---

## 1. Docker & Container Operations

### 1.1 Full Stack Lifecycle

The local dev stack is defined at `infra/compose/docker-compose.dev.yml`.

```bash
# Start infrastructure and supporting services (PostgreSQL, Redis, Neo4j, Keycloak)
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d

# Start with build (force rebuild)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d --build

# Start with no cache
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated build --no-cache && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d

# Stop everything
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated down

# Stop and remove volumes (DESTRUCTIVE — wipes container data)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated down -v

# Restart single service
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated restart postgres

# View logs (all services)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated logs -f --tail=50

# View logs (single service)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated logs -f --tail=100 postgres

# View logs (last N lines, no follow)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated logs --tail=50 redis

# Check container status
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated ps

# Check with formatting
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

### 1.2 Container Inspection

```bash
# Exec into running container
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres bash
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres sh

# Run one-off command in container
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres psql -U postgres -d valuefabric -c "SELECT 1;"

# Check container environment variables
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres env | sort

# Check resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Inspect container exit code
docker inspect fabric_postgres --format='{{.State.ExitCode}}'
```

### 1.3 Image Management

```bash
# List images with size
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Remove dangling images
docker image prune -f

# Remove all unused images
docker image prune -a -f

# Scan image for vulnerabilities
trivy image fabric-layer3:latest
```

### 1.4 Network & Volume

```bash
# List networks
docker network ls

# Inspect app network
docker network inspect compose_default

# List volumes
docker volume ls

# Clean orphaned volumes
docker volume prune -f
```

---

## 2. Backend Build & Startup

### 2.1 Python Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install shared library in editable mode
pip install -e packages/shared

# Run root setup to install all service dependencies and test dependencies
make setup

# Verify shared import works
python -c "import value_fabric.shared; print('OK')"
python -c "from value_fabric.shared.tenant import TenantContext; print('OK')"
```

### 2.2 Start Backend Layer Locally

```bash
# Layer 1 — Ingestion API (Port 8001)
pnpm dev:layer1
# Or directly via uvicorn:
# uvicorn layer1_ingestion.api.app:app --app-dir services/layer1-ingestion/src --port 8001 --reload

# Layer 2 — Extraction API (Port 8002)
pnpm dev:layer2
# Or directly via uvicorn:
# uvicorn layer2_extraction.api.app:app --app-dir services/layer2-extraction/src --port 8002 --reload

# Layer 3 — Knowledge Graph API (Port 8003)
pnpm dev:layer3
# Or directly via uvicorn:
# uvicorn api.app:app --app-dir services/layer3-knowledge/src --port 8003 --reload

# Layer 4 — Agentic Workflow Engine (Port 8004)
pnpm dev:layer4
# Or directly via uvicorn:
# uvicorn layer4_agents.api.app:app --app-dir services/layer4-agents/src --port 8004 --reload

# Layer 5 — Ground Truth API (Port 8005)
pnpm dev:layer5
# Or directly via uvicorn:
# uvicorn layer5_ground_truth.api.app:app --app-dir services/layer5-ground-truth/src --port 8005 --reload

# Layer 6 — Benchmark Service (Port 8006)
pnpm dev:layer6
# Or directly via uvicorn:
# uvicorn layer6_benchmarks.api.app:app --app-dir services/layer6-benchmarks/src --port 8006 --reload
```

### 2.3 Database Migrations

Migrations are maintained per service via Alembic.

```bash
# Run all layer database migrations
make migrate

# Check migration heads (ensure exactly one head per service)
make check-migration-heads

# Layer 1 migrations
make migrate-layer1
# or: cd services/layer1-ingestion && alembic upgrade head

# Layer 2 migrations
make migrate-layer2
# or: cd services/layer2-extraction && alembic upgrade head

# Layer 4 migrations
make migrate-layer4
# or: cd services/layer4-agents && alembic upgrade head

# Layer 5 migrations
make migrate-layer5
# or: cd services/layer5-ground-truth && alembic upgrade head

# Create new migration in a specific service
cd services/layer4-agents && alembic revision --autogenerate -m "add workflow checkpoint table"
```

### 2.4 Python Code Quality

```bash
# Format & lint check across all Python services with ruff
make lint

# Per-layer linting
make lint-layer1
make lint-layer2
make lint-layer3
make lint-layer4
make lint-layer5
make lint-layer6

# Auto-fix linting issues
ruff check --fix services/ packages/

# Type check all layers with mypy
make typecheck

# Per-layer typecheck
make typecheck-layer1
make typecheck-layer4
```

---

## 3. Frontend Build & Startup

The monorepo uses **pnpm** exclusively (`corepack prepare pnpm@10.18.1 --activate`). Do not use `npm` or `yarn`.

### 3.1 Install & Build

```bash
# Install root & workspace dependencies
pnpm install --frozen-lockfile

# Frontend dev server (port 3001, with mock API)
pnpm dev:web
# Or scoped to apps/web:
# pnpm --dir apps/web run dev

# Frontend against live backend services
pnpm --dir apps/web run dev:live

# Type check
pnpm --dir apps/web run typecheck

# Lint
pnpm --dir apps/web run lint

# Format
pnpm --dir apps/web run format

# Production build
pnpm --dir apps/web run build

# Preview production build
pnpm --dir apps/web run preview

# Analyze bundle size
pnpm --dir apps/web run build:analyze
```

### 3.2 Component and Contract Checks

```bash
# Check contract compliance
pnpm run check:contract-compliance

# Regenerate API types from contracts and assert no drift
pnpm run check:api-types

# Verify full frontend test suite
pnpm run verify:frontend
```

### 3.3 Frontend Testing

```bash
# Unit & component tests (Vitest)
pnpm --dir apps/web run test

# Unit tests in watch mode
pnpm --dir apps/web run test:watch

# Unit tests with coverage
pnpm --dir apps/web run test:coverage

# Contract tests
pnpm --dir apps/web run test:contracts

# Production auth bypass security assertion
pnpm --dir apps/web run test:prod-auth-bypass

# E2E tests (Playwright mocked)
pnpm --dir apps/web run test:e2e

# E2E tests against live backend
pnpm --dir apps/web run test:e2e:live

# Continuous live role-authenticated E2E suite (@backend specs: J1 ValuePilot continuous,
# J2 multi-role approval, cross-tenant denial) — requires a running live backend stack
pnpm --dir apps/web run test:e2e:live:continuous

# Specific golden-path journey E2E test
pnpm --dir apps/web run test:e2e:golden:j1:canonical

# Accessibility tests
pnpm --dir apps/web run test:a11y:components
pnpm --dir apps/web run test:a11y:pages
```

---

## 4. Database Operations

### 4.1 PostgreSQL

```bash
# Connect to PostgreSQL via Docker Compose
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres psql -U postgres -d valuefabric

# Or from host (port 5432)
psql postgresql://fabric:fabric@localhost:5432/fabric

# Common psql commands inside database:
\dt                    # List tables
\d+ entities           # Describe table
\dn                    # List schemas
\x on                  # Expanded display
\timing on             # Show query timing
\q                     # Quit

# Check connection from host
pg_isready -h localhost -p 5432

# Backup database
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec postgres pg_dump -U postgres valuefabric > backup_$(date +%Y%m%d).sql

# Restore database
cat backup.sql | docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec -T postgres psql -U postgres -d valuefabric
```

### 4.2 Redis

```bash
# Connect to Redis CLI
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec redis redis-cli

# Common commands:
PING                   # Test connectivity
INFO                   # Server info
DBSIZE                 # Key count
SCAN 0 COUNT 100       # Iterate keys safely
TTL <key>              # Check expiration
MONITOR                # Watch real-time commands (Ctrl+C to stop)

# Or from host
redis-cli -h localhost -p 6379 PING
```

### 4.3 Neo4j

```bash
# Cypher shell via Docker Compose
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated exec neo4j cypher-shell -u neo4j -p devpassword

# Common cypher queries:
MATCH (n) RETURN count(n);                    # Count all nodes
MATCH (n) RETURN labels(n), count(n);         # Count by label
SHOW INDEXES;                                 # List indexes
MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 10;   # Relationships
```

---

## 5. Testing Commands

### 5.1 Backend Test Suite

```bash
# All backend tests
make test

# Per-layer testing
make test-layer1
make test-layer2
make test-layer3
make test-layer4
make test-layer5
make test-layer6

# Run specific test file
pytest services/layer4-agents/tests/test_audit_orchestrator.py -v

# Run with pytest markers
pytest -m unit
pytest -m integration
pytest -m contract_static
pytest -m tenant_boundary
pytest -m security

# Parallel test execution
pytest -n auto

# With coverage
pytest --cov=services --cov-report=term-missing
```

### 5.2 Contract & Architecture Tests

```bash
# Contract and architecture tests (no live services needed)
make contract-tests

# Direct pytest contract invocation
pytest tests/contract/ -v

# Security & tenant-boundary tests
pytest tests/security/ -v
```

### 5.3 Integrated Validation & Smoke Tests

```bash
# Backend-integrated validation (requires running Docker dev stack)
make test-backend-integrated-validation

# Release smoke test suite
make test-backend-integrated-release-smoke
```

---

## 6. Health & Validation

### 6.1 Layer Health Checks

```bash
# Health check endpoints
curl -f http://localhost:8001/health          # Layer 1
curl -f http://localhost:8002/health          # Layer 2
curl -f http://localhost:8003/health          # Layer 3
curl -f http://localhost:8004/health          # Layer 4
curl -f http://localhost:8005/health          # Layer 5
curl -f http://localhost:8006/health          # Layer 6
curl -f http://localhost:3001/                # Frontend (Vite)
```

### 6.2 Full Verification Gate

```bash
# Canonical gate for full platform verification (required before PR)
make verify

# Behavior readiness audit
make check-behavior-readiness-audit

# Critical behaviors suite
pnpm run test:critical-behaviors
```

---

## 7. Kubernetes Operations

### 7.1 Local K8s & Deployments

```bash
# Check cluster
kubectl cluster-info
kubectl get nodes

# Set namespace
kubectl config set-context --current --namespace=fabric

# Apply manifests
kubectl apply -f k8s/

# Check pod and service status
kubectl get pods -n fabric
kubectl get svc -n fabric
kubectl get ingress -n fabric

# Pod logs
kubectl logs -f deployment/layer3 --tail=50 -n fabric

# Exec into pod
kubectl exec -it deployment/layer3 -n fabric -- python -c "import value_fabric.shared; print('OK')"

# Port forward
kubectl port-forward svc/layer3 8003:8003 -n fabric
```

### 7.2 Secrets & Infisical

```bash
# View secrets
kubectl get secrets -n fabric

# Verify placeholder guardrails without printing secret values
python scripts/security/placeholder_secret_scan.py --runtime

# Apply external secrets
kubectl apply -f k8s/external-secrets/
kubectl apply -f k8s/infisical/
```

---

## 8. Monitoring & Observability

### 8.1 Prometheus & Alertmanager

```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Query metric
curl -s "http://localhost:9090/api/v1/query?query=up" | jq '.data.result'

# Alertmanager status
curl -s http://localhost:9093/api/v1/status | jq '.data.clusterStatus'

# Alertmanager active alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | {labels, status}'
```

### 8.2 Grafana

```bash
# List dashboards
curl -s http://admin:admin@localhost:3000/api/search | jq '.[] | {title, uid}'
```

---

## 9. Git & Version Control

### 9.1 Safe Development Workflow

```bash
# Check current state
git status
git log --oneline -10

# Create feature branch
git checkout -b feat/layer4-checkpoint-resume

# Stage changes
git add -A

# Commit with descriptive message and AI co-author if applicable
git commit -m "feat(layer4): add checkpoint resume capability

Co-authored-by: Ona <no-reply@ona.com>"

# Push branch
git push -u origin feat/layer4-checkpoint-resume
```

### 9.2 Pre-commit Hooks

```bash
# Run pre-commit hooks on all files
pre-commit run --all-files

# Install pre-commit hooks
pre-commit install
```

---

## 10. Debugging & Diagnostics

### 10.1 Python Debugging

```bash
# Trace imports
python -v -c "import value_fabric.shared" 2>&1 | grep -E "import |#"

# Run specific failing test with traceback and stdout
pytest services/layer4-agents/tests/test_audit_orchestrator.py -vv -s --tb=short
```

### 10.2 Container Debugging

```bash
# Check container logs
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated logs --tail=50 postgres

# Check port conflicts
lsof -i :8003 || netstat -tlnp | grep 8003
```

### 10.3 Frontend Debugging

```bash
# Start dev server with exposed host
pnpm --dir apps/web run dev -- --host

# Check for type errors
pnpm --dir apps/web run typecheck
```

---

## 11. One-Line Validation Chains

### 11.1 Quick System Pulse

```bash
# Check running ports for infrastructure and layers
for p in 5432 6379 7474 8001 8002 8003 8004 8005 8006 3001; do
  nc -z -v -w3 localhost $p 2>/dev/null && echo "✅ Port $p listening" || echo "❌ Port $p closed";
done
```

### 11.2 Frontend Full Pipeline

```bash
pnpm --dir apps/web run typecheck && pnpm --dir apps/web run lint && pnpm --dir apps/web run test && pnpm --dir apps/web run build && echo "✅ Frontend pipeline complete"
```

### 11.3 Backend Full Pipeline

```bash
make lint && make typecheck && make test && echo "✅ Backend pipeline complete"
```

---

## 12. Environment Setup Scripts & Common Operations

### 12.1 First-Time Setup Flow

```bash
# 1. Enable pnpm via corepack
corepack enable
corepack prepare pnpm@10.18.1 --activate

# 2. Install frontend & workspace dependencies
pnpm install --frozen-lockfile

# 3. Setup Python service dependencies
make setup

# 4. Generate local dev env and launch infra containers
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d

# 5. Run database migrations
make migrate

# 6. Verify everything passes
make verify
```

### 12.2 Common Make Targets

```bash
make help               # Display all available targets and descriptions
make verify             # Run full verification suite (lint, typecheck, contract tests, unit tests)
make test               # Run all Python backend tests
make lint               # Run Python linting (ruff)
make typecheck          # Run Python type checking (mypy)
make migrate            # Run Alembic migrations across all layers
make contract-tests     # Run API and architecture contract tests
make clean              # Clean cache files, pyc files, and test artifacts
```

---

**Usage:** `make verify | make test | pnpm dev:web | make migrate`

All commands are copy-pasteable and tested against the Fabric_4L stack architecture.
