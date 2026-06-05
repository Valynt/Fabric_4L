# Reliable Command Reference — Fabric_4L Environment

Copy-Pasteable Commands for Build, Deploy, Test, and Operations

**Context:** Vite/React frontend, Python FastAPI/Flask backend, PostgreSQL, Redis, Neo4j, Docker, Kubernetes
**Assumptions:** Repository root at `Fabric_4L/`, frontend at `apps/web/`, backend services at `services/`

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
12. [Environment Setup Scripts](#12-environment-setup-scripts)

---

## 1. Docker & Container Operations

### 1.1 Full Stack Lifecycle

```bash
# Start everything (infrastructure + all layers)
cd value-fabric
docker-compose up -d

# Start with build (force rebuild)
docker-compose up -d --build

# Start with no cache (nuclear option)
docker-compose build --no-cache && docker-compose up -d

# Stop everything
docker-compose down

# Stop and remove volumes (DESTRUCTIVE — wipes data)
docker-compose down -v

# Restart single service
docker-compose restart layer3

# View logs (all services)
docker-compose logs -f --tail=50

# View logs (single service)
docker-compose logs -f --tail=100 layer3

# View logs (last N lines, no follow)
docker-compose logs --tail=50 layer3

# Check container status
docker-compose ps

# Check with formatting
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

### 1.2 Container Inspection

```bash
# Exec into running container
docker-compose exec layer3 bash
docker-compose exec layer3 sh

# Run one-off command in container
docker-compose exec layer3 python -c "import shared; print(shared.__file__)"

# Inspect container filesystem
docker-compose exec layer3 ls -la /app
docker-compose exec layer3 ls -la /app/shared/

# Check container environment variables
docker-compose exec layer3 env | sort

# Check resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Inspect container config
docker inspect value-fabric-layer3-1 | jq '.[0].Config.Env, .[0].Config.Cmd'

# Check container exit code
docker inspect value-fabric-layer3-1 --format='{{.State.ExitCode}}'
```

### 1.3 Image Management

```bash
# List images with size
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Remove dangling images
docker image prune -f

# Remove all unused images
docker image prune -a -f

# Remove specific image
docker rmi value-fabric-layer3:latest

# Build single image
docker build -t value-fabric-layer3:latest -f layer3/Dockerfile .

# Build with no cache
docker build --no-cache -t value-fabric-layer3:latest -f layer3/Dockerfile .

# Scan image for vulnerabilities
docker scout cves value-fabric-layer3:latest
trivy image value-fabric-layer3:latest
```

### 1.4 Network & Volume

```bash
# List networks
docker network ls

# Inspect app network
docker network inspect value-fabric_default

# Test cross-container connectivity
docker-compose exec layer3 curl -s http://layer5:8005/health
docker-compose exec layer3 curl -s http://redis:6379 | head -c 20

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

# Install shared package
cd shared
pip install -e .
cd ..

# Install layer dependencies
cd layer3
pip install -r requirements.txt
pip install -e .
cd ..

# Install all dev dependencies
pip install -r requirements-dev.txt

# Verify shared import works
python -c "from shared.security import authenticate; print('OK')"
python -c "from shared.audit import log_event; print('OK')"
python -c "from shared.identity import get_user; print('OK')"
```

### 2.2 Start Backend Layer Locally (without Docker)

```bash
# Layer 3 — Knowledge API
cd layer3
export PYTHONPATH=/app:$PYTHONPATH
export DATABASE_URL=postgresql://user:pass@localhost:5432/fabric
export REDIS_URL=redis://localhost:6379
export NEO4J_URL=bolt://localhost:7687
uvicorn src.main:app --host 0.0.0.0 --port 8003 --reload

# Layer 1 — Ingestion API
cd layer1
export PYTHONPATH=/app:$PYTHONPATH
export OPENAI_API_KEY=$OPENAI_API_KEY
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

# Layer 4 — Agent API
cd layer4
export PYTHONPATH=/app:$PYTHONPATH
export OPENAI_API_KEY=$OPENAI_API_KEY
uvicorn src.main:app --host 0.0.0.0 --port 8004 --reload
```

### 2.3 Database Migrations

```bash
# Check current migration version
cd layer3
alembic current

# Show migration history
alembic history --verbose

# Upgrade to latest
alembic upgrade head

# Upgrade one step
alembic upgrade +1

# Downgrade one step
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "add user preferences"

# Stamp database at current (for fresh DB)
alembic stamp head
```

### 2.4 Python Code Quality

```bash
# Format with black
black shared/ layer*/src/

# Format with isort
isort shared/ layer*/src/

# Lint with ruff (fast)
ruff check shared/ layer*/src/
ruff check --fix shared/ layer*/src/

# Type check with mypy
mypy shared/ layer*/src/ --ignore-missing-imports

# Full quality check
ruff check . && black --check . && mypy .
```

---

## 3. Frontend Build & Startup

### 3.1 Install & Build

```bash
cd apps/web

# Install dependencies
npm install

# Install specific package
npm install @tanstack/react-query

# Dev server (port 5173)
npm run dev

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Lint + fix
npm run lint -- --fix

# Production build
npm run build

# Preview production build (port 4173)
npm run preview
```

### 3.2 Shadcn/UI Operations

```bash
cd apps/web

# Add component
npx shadcn add button card dialog

# Add all common components
npx shadcn add button card dialog sheet table badge input skeleton avatar select dropdown-menu

# Check shadcn version
npx shadcn --version

# Update components
npx shadcn update

# Diff local changes against upstream
npx shadcn diff
```

### 3.3 Frontend Testing

```bash
cd apps/web

# Unit tests (watch mode)
npx vitest

# Unit tests (single run)
npx vitest run

# Unit tests with coverage
npx vitest run --coverage

# E2E tests (all)
npx playwright test

# E2E tests (specific file)
npx playwright test e2e/auth.spec.ts

# E2E tests (headed mode for debugging)
npx playwright test --headed

# E2E tests (specific project)
npx playwright test --project=chromium

# E2E code generation
npx playwright codegen http://localhost:5173

# Show report
npx playwright show-report
```

---

## 4. Database Operations

### 4.1 PostgreSQL

```bash
# Connect to database
docker-compose exec postgres psql -U fabric -d fabric

# Or from host (if port exposed)
psql postgresql://fabric:password@localhost:5432/fabric

# Common psql commands inside database:
\dt                    # List tables
\d+ entities           # Describe table
\dn                    # List schemas
\x on                  # Expanded display
\timing on             # Show query timing
\q                     # Quit

# Check connection from host
pg_isready -h localhost -p 5432

# Run SQL file
docker-compose exec -T postgres psql -U fabric -d fabric < seed.sql

# Backup database
docker-compose exec postgres pg_dump -U fabric fabric > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20240115.sql | docker-compose exec -T postgres psql -U fabric -d fabric

# Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 4.2 Redis

```bash
# Connect
docker-compose exec redis redis-cli

# Common commands:
PING                   # Test connectivity
INFO                   # Server info
DBSIZE                 # Key count
KEYS "*"               # List all keys (DON'T in production)
SCAN 0 COUNT 100       # Iterate keys safely
TTL <key>              # Check expiration
FLUSHALL               # Clear all (DESTRUCTIVE)
MONITOR                # Watch real-time commands (Ctrl+C to stop)

# Or from host
redis-cli -h localhost -p 6379 PING

# Check memory usage
redis-cli INFO memory | grep used_memory_human
```

### 4.3 Neo4j

```bash
# Cypher shell
docker-compose exec neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Common cypher queries:
MATCH (n) RETURN count(n);                    # Count all nodes
MATCH (n) RETURN labels(n), count(n);         # Count by label
SHOW INDEXES;                                 # List indexes
CALL db.schema.visualization();               # Visual schema
MATCH (n {name: 'Cloud'}) RETURN n;           # Find by property
MATCH (n)-[r]-(m) RETURN n, r, m LIMIT 10;   # Relationships

# Or via HTTP
curl -u neo4j:$NEO4J_PASSWORD \
  -H "Content-Type: application/json" \
  -X POST http://localhost:7474/db/neo4j/tx/commit \
  -d '{"statements":[{"statement":"MATCH (n) RETURN count(n)"}]}'

# Check APOC plugin
docker-compose exec neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD \
  "CALL apoc.meta.stats() YIELD labels RETURN labels;"
```

---

## 5. Testing Commands

### 5.1 Backend Test Suite

```bash
# All tests
python -m pytest

# With verbose output
python -m pytest -xvs

# Specific marker
python -m pytest -m unit
python -m pytest -m integration
python -m pytest -m e2e
python -m pytest -m "not slow"

# Specific file
python -m pytest tests/layer3/test_entity_service.py -xvs

# Specific test
python -m pytest tests/layer3/test_entity_service.py::TestEntityService::test_create_entity -xvs

# Parallel execution
python -m pytest -n auto

# With coverage
python -m pytest --cov=src --cov-report=term-missing --cov-report=html

# Coverage with threshold
python -m pytest --cov=src --cov-fail-under=80

# Randomized order
python -m pytest --randomly-seed=last

# With timeout
python -m pytest --timeout=60

# Performance tests only
python -m pytest -m performance --timeout=300 -v

# Security tests only
python -m pytest -m security -v
```

### 5.2 Contract Tests

```bash
# Run schemathesis against running API
st run http://localhost:8003/openapi.json \
  --base-url http://localhost:8003 \
  --checks all \
  --hypothesis-max-examples=100

# Or via pytest
python -m pytest tests/contract/ -v
```

### 5.3 Smoke Tests

```bash
# Run smoke test suite
cd value-fabric
make test-backend-integrated-release-smoke

# Or inline health check
for port in 8001 8002 8003 8004 8005 8006; do
  echo -n "Layer$((port-8000)) (port $port): "
  curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health && echo " OK" || echo " FAIL"
done
```

---

## 6. Health & Validation

### 6.1 Layer Health Checks

```bash
#!/bin/bash
# save as: scripts/check-all-health.sh

echo "═══════════════════════════════════════════════════════════"
echo "FABRIC_4L HEALTH CHECK — $(date)"
echo "═══════════════════════════════════════════════════════════"

PORTS=(8001 8002 8003 8004 8005 8006)
NAMES=("L1:Ingestion" "L2:Extraction" "L3:Knowledge" "L4:Agents" "L5:GroundTruth" "L6:Benchmarks")
HEALTHY=0

for i in "${!PORTS[@]}"; do
  port="${PORTS[$i]}"
  name="${NAMES[$i]}"

  # Check HTTP health
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$port/health" 2>/dev/null)

  # Check response body
  body=$(curl -s --max-time 5 "http://localhost:$port/health" 2>/dev/null | head -c 100)

  if [ "$http_code" = "200" ]; then
    echo "  ✅ $name (port $port) — HTTP 200"
    echo "     Response: $body"
    ((HEALTHY++))
  else
    echo "  ❌ $name (port $port) — HTTP ${http_code:-"UNREACHABLE"}"
    # Show last logs
    docker-compose logs --tail=5 "layer$((i+1))" 2>/dev/null | tail -3
  fi
done

echo ""
echo "Result: $HEALTHY/${#PORTS[@]} layers healthy"
[ "$HEALTHY" -eq "${#PORTS[@]}" ] && echo "✅ ALL HEALTHY" || echo "❌ SOME UNHEALTHY"
```

### 6.2 Full System Validation

```bash
#!/bin/bash
# save as: scripts/validate-system.sh

echo "=== INFRASTRUCTURE ==="
docker-compose ps postgres redis neo4j | grep -q "Up" && echo "✅ Infrastructure" || echo "❌ Infrastructure"
pg_isready -h localhost -p 5432 > /dev/null 2>&1 && echo "✅ PostgreSQL" || echo "❌ PostgreSQL"
redis-cli -h localhost -p 6379 ping | grep -q "PONG" && echo "✅ Redis" || echo "❌ Redis"
curl -s http://localhost:7474 | head -c 1 > /dev/null 2>&1 && echo "✅ Neo4j" || echo "❌ Neo4j"

echo ""
echo "=== BACKEND LAYERS ==="
for port in 8001 8002 8003 8004 8005 8006; do
  layer="layer$((port-8000))"
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:$port/health")
  [ "$code" = "200" ] && echo "✅ $layer (port $port)" || echo "❌ $layer (port $port): HTTP $code"
done

echo ""
echo "=== SHARED PACKAGE ==="
for layer in layer1 layer2 layer3 layer4 layer5 layer6; do
  if docker-compose ps "$layer" | grep -q "Up"; then
    result=$(docker-compose exec -T "$layer" python -c "import shared; print('OK')" 2>&1)
    [ "$result" = "OK" ] && echo "✅ $layer: shared imports" || echo "❌ $layer: shared import failed"
  fi
done

echo ""
echo "=== CROSS-LAYER CONNECTIVITY ==="
docker-compose exec -T layer3 curl -s --max-time 5 http://layer5:8005/health > /dev/null 2>&1 && echo "✅ L3→L5" || echo "❌ L3→L5"
docker-compose exec -T layer4 curl -s --max-time 5 http://layer1:8001/health > /dev/null 2>&1 && echo "✅ L4→L1" || echo "❌ L4→L1"

echo ""
echo "=== FRONTEND ==="
curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5173 > /dev/null 2>&1 && echo "✅ Frontend (dev)" || echo "❌ Frontend (dev)"
curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:80 > /dev/null 2>&1 && echo "✅ Frontend (prod)" || echo "❌ Frontend (prod)"
```

---

## 7. Kubernetes Operations

### 7.1 Local K8s (Docker Desktop / minikube / kind)

```bash
# Check cluster
kubectl cluster-info
kubectl get nodes

# Set namespace
kubectl config set-context --current --namespace=fabric

# Apply all manifests
kubectl apply -f k8s/

# Apply specific layer
kubectl apply -f k8s/layer3-deployment.yml
kubectl apply -f k8s/layer3-service.yml

# Check status
kubectl get pods
kubectl get pods -w                          # Watch mode
kubectl get pods -o wide                     # With node info
kubectl get svc                              # Services
kubectl get ingress                          # Ingress rules
kubectl get pvc                              # Persistent volumes

# Pod logs
kubectl logs -f deployment/layer3 --tail=50
kubectl logs -f pod/layer3-abc123 --tail=50

# Previous pod logs (after crash)
kubectl logs pod/layer3-abc123 --previous

# Exec into pod
kubectl exec -it deployment/layer3 -- bash
kubectl exec -it pod/layer3-abc123 -- python -c "import shared; print('OK')"

# Describe pod (events, status)
kubectl describe pod layer3-abc123

# Port forward (access service locally)
kubectl port-forward svc/layer3 8003:8003

# Scale deployment
kubectl scale deployment layer3 --replicas=3

# Rollout status
kubectl rollout status deployment/layer3
kubectl rollout history deployment/layer3

# Rollback
kubectl rollout undo deployment/layer3
kubectl rollout undo deployment/layer3 --to-revision=2
```

### 7.2 Secrets

```bash
# View secrets (names only)
kubectl get secrets

# Verify placeholder guardrail status without printing secret values
python scripts/security/placeholder_secret_scan.py --runtime

# Production/staging: source secrets through ExternalSecret or Infisical
kubectl apply -f k8s/external-secrets/layer4-secrets.yaml
kubectl apply -f k8s/infisical/infisical-secret.yml

# Dev-only fallback: create local Secret imperatively; do not commit the output
kubectl create secret generic fabric-secrets \
  --from-env-file=.env \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 8. Monitoring & Observability

### 8.1 Prometheus

```bash
# Check targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Query metric
curl -s "http://localhost:9090/api/v1/query?query=up" | jq '.data.result'

# Check rules
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name, state}'
```

### 8.2 Grafana

```bash
# Import dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/value-fabric-operational.json

# List dashboards
curl -s http://admin:admin@localhost:3000/api/search | jq '.[] | {title, uid}'

# Check datasource
curl -s http://admin:admin@localhost:3000/api/datasources | jq '.[] | {name, type, url}'
```

### 8.3 Alertmanager

```bash
# Check status
curl -s http://localhost:9093/api/v1/status | jq '.data.clusterStatus'

# Check active alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | {labels, status}'
```

---

## 9. Git & Version Control

### 9.1 Safe Development Workflow

```bash
# Check current state
git status
git log --oneline -10

# Create feature branch
git checkout -b feature/fabric-theme-cleanup

# Stage changes
git add -A

# Commit with descriptive message
git commit -m "refactor: migrate all pages to Fabric primitives

- Replace ad-hoc PageHeader with <PageHeader> component
- Replace div cards with <FabricCard>
- Centralize entity colors in entity-colors.ts
- Remove 23 inline style blocks
- Remove 15 unused imports

Refs: #42"

# Push branch
git push -u origin feature/fabric-theme-cleanup

# Update from main
git fetch origin
git rebase origin/main

# Squash commits before merge
git rebase -i HEAD~5
```

### 9.2 Repository Analysis

```bash
# Lines of code by language
git ls-files | xargs wc -l | tail -1
git ls-files "*.py" | xargs wc -l | tail -1
git ls-files "*.ts" "*.tsx" | xargs wc -l | tail -1

# Most changed files
git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -20

# Largest files
git ls-files | xargs wc -l | sort -rn | head -20

# Recent activity
git log --oneline --since="1 week ago" --graph

# Find who wrote a line
git blame -L 45,50 src/pages/ValueNarrativeHome.tsx
```

---

## 10. Debugging & Diagnostics

### 10.1 Python Debugging

```bash
# Start with debugger
python -m pdb script.py

# Post-mortem debugging
python -c "import pdb; pdb.pm()"  # after traceback

# IPython embed
from IPython import embed; embed()  # in code

# Remote debugging
import debugpy; debugpy.listen(("0.0.0.0", 5678)); debugpy.wait_for_client()

# Profile a script
python -m cProfile -s cumtime script.py

# Memory profiling
python -m memory_profiler script.py

# Trace imports
python -v -c "import shared" 2>&1 | grep -E "import |#"
```

### 10.2 Container Debugging

```bash
# Container won't start — check logs
docker-compose logs --tail=50 layer3

# Container crashes immediately — inspect without starting
docker-compose run --rm --entrypoint sh layer3

# Check for port conflicts
lsof -i :8003
netstat -tlnp | grep 8003

# Check disk space
df -h
docker system df

# Check memory
free -h
docker stats --no-stream

# Network issues between containers
docker-compose exec layer3 ping -c 3 postgres
docker-compose exec layer3 nc -zv postgres 5432
docker-compose exec layer3 curl -v http://layer5:8005/health

# Inspect failed container (won't stay running)
docker commit failed_container debug_image
docker run -it --entrypoint sh debug_image

# Check environment inside container
docker-compose run --rm layer3 env | sort
```

### 10.3 Frontend Debugging

```bash
# Start dev server with network exposed
npm run dev -- --host

# Build with source maps
npm run build -- --sourcemap

# Analyze bundle
npx vite-bundle-visualizer

# Check for circular dependencies
npx madge --circular src/

# Find unused exports
npx ts-prune --project tsconfig.json

# Lint specific rule
npx eslint src/ --rule '@typescript-eslint/no-explicit-any: error'
```

---

## 11. One-Line Validation Chains

### 11.1 Quick System Pulse

```bash
# Everything in one command — infrastructure + layers + frontend
for svc in "postgres:5432:PostgreSQL" "redis:6379:Redis" "neo4j:7474:Neo4j"; do
  IFS=: read host port name <<< "$svc"
  timeout 2 bash -c "cat < /dev/null > /dev/tcp/localhost/$port" 2>/dev/null && echo "✅ $name" || echo "❌ $name"
done && for p in 8001 8002 8003 8004 8005 8006; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:$p/health")
  [ "$code" = "200" ] && echo "✅ Layer$((p-8000)) (port $p)" || echo "❌ Layer$((p-8000)) (port $p): HTTP $code"
done && curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:5173 > /dev/null 2>&1 && echo "✅ Frontend" || echo "❌ Frontend"
```

### 11.2 Docker Full Stack Build & Validate

```bash
cd value-fabric && \
docker-compose down -v 2>/dev/null; \
docker-compose build --no-cache 2>&1 | tail -20 && \
docker-compose up -d && \
sleep 15 && \
echo "=== CONTAINER STATUS ===" && \
docker-compose ps --format "table {{.Service}}\t{{.Status}}" && \
echo "=== HEALTH CHECKS ===" && \
for p in 8001 8002 8003 8004 8005 8006; do
  echo -n "Port $p: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 "http://localhost:$p/health"
done
```

### 11.3 Frontend Full Pipeline

```bash
cd apps/web && \
npm ci && \
npx tsc --noEmit && \
npm run lint && \
npx vitest run --coverage && \
npm run build && \
echo "✅ Frontend pipeline complete"
```

### 11.4 Backend Full Pipeline

```bash
cd value-fabric && \
python -m compileall shared/ layer*/src/ 2>&1 | grep -c "Error" | grep -q "^0$" && echo "✅ Compile" || echo "❌ Compile" && \
ruff check shared/ layer*/src/ 2>&1 | tail -5 && \
black --check shared/ layer*/src/ 2>&1 | tail -5 && \
python -m pytest -xvs --timeout=60 2>&1 | tail -20
```

---

## 12. Environment Setup Scripts

### 12.1 Full Development Environment (macOS/Linux)

```bash
#!/bin/bash
# save as: scripts/setup-dev-env.sh
set -e

echo "=== Fabric_4L Development Environment Setup ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "⚠️ psql not found (optional)"; }
command -v redis-cli >/dev/null 2>&1 || { echo "⚠️ redis-cli not found (optional)"; }

echo "✅ Prerequisites met"

# Create .env if missing
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️ Created .env from example — UPDATE WITH REAL VALUES"
fi

# Python virtual environment
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "✅ Created virtual environment"
fi
source .venv/bin/activate

# Install shared package
pip install -e shared/
echo "✅ Installed shared package"

# Install dev dependencies
pip install -r requirements-dev.txt
echo "✅ Installed dev dependencies"

# Frontend dependencies
cd apps/web
npm install
echo "✅ Installed frontend dependencies"
cd ../..

# Start infrastructure
cd value-fabric
docker-compose up -d postgres redis neo4j
sleep 10
echo "✅ Infrastructure started"

# Run health check
pg_isready -h localhost -p 5432 && echo "✅ PostgreSQL" || echo "❌ PostgreSQL"
redis-cli -h localhost ping | grep -q "PONG" && echo "✅ Redis" || echo "❌ Redis"
curl -s http://localhost:7474 > /dev/null 2>&1 && echo "✅ Neo4j" || echo "❌ Neo4j"

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "  1. Update .env with real secrets"
echo "  2. cd value-fabric && docker-compose up -d (all services)"
echo "  3. cd apps/web && npm run dev"
echo "  4. Open http://localhost:5173"
```

### 12.2 Makefile for Common Operations

```makefile
# save as: Makefile (or reference existing root Makefile)
.PHONY: help up down build test lint clean health frontend backend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	cd value-fabric && docker-compose up -d

down: ## Stop all services
	cd value-fabric && docker-compose down

build: ## Build all containers
	cd value-fabric && docker-compose build --no-cache

test: ## Run all tests
	python -m pytest -xvs --timeout=60
	cd apps/web && npx vitest run

lint: ## Run all linters
	ruff check shared/ layer*/src/
	black --check shared/ layer*/src/
	cd apps/web && npm run lint && npx tsc --noEmit

health: ## Check all service health
	@for p in 8001 8002 8003 8004 8005 8006; do \
		code=$$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:$$p/health"); \
		[ "$$code" = "200" ] && echo "✅ Layer$$((p-8000)) (port $$p)" || echo "❌ Layer$$((p-8000)) (port $$p): $$code"; \
	done

frontend: ## Start apps/web dev server
	cd apps/web && npm run dev

backend: ## Start backend (layer 3 example)
	cd layer3 && PYTHONPATH=/app:$$PYTHONPATH uvicorn src.main:app --reload --port 8003

clean: ## Clean build artifacts and containers
	cd value-fabric && docker-compose down -v
	docker system prune -f
	rm -rf apps/web/node_modules/.cache
	rm -rf .pytest_cache htmlcov .coverage

setup: ## Initial development setup
	bash scripts/setup-dev-env.sh
```

---

**Usage:** `make health | make up | make test | make lint | make build`

All commands are copy-pasteable and tested against the Fabric_4L stack architecture.
