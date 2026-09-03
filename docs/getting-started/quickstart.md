---
title: "Value Fabric Quickstart Guide"
category: "getting-started"
audience: "beginner"
last-reviewed: "2026-06-04"
freshness: "current"
related: ["environment", "../core-concepts/architecture", "../how-to-guides/setup-local-dev", "../troubleshooting/index", "../core-concepts/security-model"]
---

> **In this guide, you will:**
>
> - Set up a local Fabric_4L instance in 15 minutes
> - Ingest your first document
> - Query the knowledge graph
> - Run your first agent workflow

---

## Prerequisites

Before starting, ensure you have:

| Requirement | Version | Verify Command |
| ----------- | ------- | -------------- |
| Docker Desktop | 4.25+ | `docker --version` |
| Docker Compose | 2.23+ | `docker compose version` |
| Git | 2.40+ | `git --version` |
| Make | 3.81+ | `make --version` |
| uv | 0.4+ | `uv --version` |
| pnpm | 10.18.1 (via corepack) | `pnpm --version` |
| OpenAI API Key | — | [Get one here](https://platform.openai.com/api-keys) |

**Estimated Time:** 15 minutes
**Complexity:** Beginner

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Your Machine"
        A[Docker Compose] --> B[Layer 1: Ingestion<br/>Host Port 8000]
        A --> C[Layer 2: Extraction<br/>Host Port 8000]
        A --> L2_5[Layer 2.5: Signal Refinery<br/>Host Port 8007]
        A --> D[Layer 3: Knowledge Graph<br/>Host Port 8001]
        A --> E[Layer 4: Agents<br/>Host Port 8004]
        A --> M[Layer 5: Ground Truth<br/>Host Port 8005]
        A --> N[Layer 6: Benchmarks<br/>Host Port 8006]
        A --> L7[Layer 7: Billing<br/>Host Port 8008]
        A --> G[(PostgreSQL)]
        A --> H[(Neo4j)]
        A --> I[(Redis)]
        A --> F[Frontend UI<br/>Port 5173 (pnpm dev)<br/>or 3001 (docker compose)]
    end
    J[LLM APIs] -.-> C
    J -.-> L2_5
    J -.-> E

    style A fill:#4a90d9,color:white
    style F fill:#4a90d9,color:white
    style J fill:#95a5a6,color:white
```

**Data Flow:** Documents → L1 (Ingest) → L2 (Extract) → L2.5 (Signal Refinery) → L3 (Store) → L4 (Agent Analysis) → L5 (Ground Truth) → L6 (Benchmarks)

**All 9 services** (run from repo root via `docker compose -f docker-compose.full.yml`):

| # | Service | Path | Host Port | Role |
| - | ------- | ---- | --------- | ---- |
| 0 | API Gateway | `services/api/` | 8000 | Request routing, auth |
| 1 | Layer 1 Ingestion | `services/layer1-ingestion/` | 8000 | Document ingestion |
| 2 | Layer 2 Extraction | `services/layer2-extraction/` | 8000 | LLM-based extraction |
| 2.5 | Layer 2.5 Signal Refinery | `services/layer2-5-signal-refinery/` | 8007 | Signal normalization & trust scoring |
| 3 | Layer 3 Knowledge Graph | `services/layer3-knowledge/` | 8001 | Neo4j graph storage |
| 4 | Layer 4 Agents | `services/layer4-agents/` | 8004 | Agent orchestration |
| 5 | Layer 5 Ground Truth | `services/layer5-ground-truth/` | 8005 | Validation & ground truth |
| 6 | Layer 6 Benchmarks | `services/layer6-benchmarks/` | 8006 | Benchmark evaluation |
| 8 | Frontend UI | `apps/web/` | 5173 (`pnpm dev`) or 3001 (`docker compose`) | React/Vite user interface |

## Runtime path placement (contributors)

Per **ADR-021**, all implementation logic lives in `services/` trees. The legacy root `value_fabric/` compatibility namespace has been removed; shared modules resolve from `packages/shared/src/value_fabric/shared/`.

When you add or change service code, place it under the canonical service path:

- `services/layer6-benchmarks/src/` — canonical source for Layer 6

Authoritative policy references:

- `docs/reference/layer-runtime-path-governance.md`
- `docs/explanations/adr/ADR-021-layer-3-canonical-runtime-path.md`

Required guardrails when adding a new layer module:

- Implement it under the service's `src/<package>/` tree
- Do **not** restore `value_fabric/layerX/` implementation files or path-appender shims
- Run contract tests after changes: `pytest tests/arch/test_canonical_module_sentinels.py`

---

## Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L

# Copy the local-only environment contract
cp .env.example .env
```

For team development, prefer secret injection so credentials never live in a
checked-in manifest or shared `.env`:

```bash
infisical run --env=dev --path=/fabric-4l/Fabric_4L/dev -- \
  docker compose -f docker-compose.full.yml up -d
```

For solo local work, edit `.env` and add your credentials. Do not
copy these values into Kubernetes `Secret` manifests; use `ExternalSecret` or
Infisical mappings for cluster deployments.

```bash
# Required: OpenAI API Key, injected by Infisical when possible
OPENAI_API_KEY=sk-your-key-here

# Required: JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your-generated-secret-here

# Optional: Override private GHCR base image for local Docker builds
BASE_IMAGE=python:3.11.11-slim-bookworm

# Optional: Change ports if conflicts exist
LAYER1_PORT=8000
LAYER2_PORT=8000
LAYER3_PORT=8001
LAYER4_PORT=8004
LAYER5_PORT=8005
LAYER6_PORT=8006
```

---

## Step 2: Start Services

All commands run from the **repository root** (there is no `value-fabric/` subdirectory):

```bash
# Start the full stack (recommended)
docker compose -f docker-compose.full.yml up -d

# Or start the minimal live stack
docker compose up -d

# Expected output:
# [+] Running 9/9
#  ✔ Container vf-live-postgres  Started
#  ✔ Container vf-live-redis     Started
#  ✔ Container vf-live-neo4j     Started
#  ✔ Container vf-live-layer1    Started
#  ✔ Container vf-live-layer2    Started
#  ✔ Container vf-live-layer3    Started
#  ✔ Container vf-live-layer4    Started
#  ✔ Container vf-live-layer5    Started
#  ✔ Container vf-live-layer6    Started
```

**Verification:**

```bash
# Check all services are healthy
docker compose ps

# Expected: All services show "healthy" or "running (0)"
```

**Customizing the Docker Base Image (Optional):**

By default, Dockerfiles use a private GHCR base image. To override this for local development (e.g., to use a public Python image), set `BASE_IMAGE` in your `.env`:

```bash
BASE_IMAGE=python:3.11.11-slim-bookworm
```

Then rebuild with the override:

```bash
docker compose -f docker-compose.full.yml up --build -d
```

This is already pre-configured in the provided `.env` and `.env.example` files.

---

## Step 3: Run Database Migrations

```bash
# From the repository root
make migrate

# Or run per-service migrations using the supported Makefile targets:
# make migrate-layer1
# make migrate-layer2
# make migrate-layer4
# make migrate-layer5

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl
# INFO  [alembic.runtime.migration] Running upgrade  -> 001, create accounts tables
```

---

## Step 4: Verify Installation

```bash
# Run comprehensive verification
make verify

# Expected output:
# ✓ Layer 1: Healthy (port 8000)
# ✓ Layer 2: Healthy (port 8000)
# ✓ Layer 2.5: Healthy (port 8007)
# ✓ Layer 3: Healthy (port 8001)
# ✓ Layer 4: Healthy (port 8004)
# ✓ Layer 5: Healthy (port 8005)
# ✓ Layer 6: Healthy (port 8006)
# ✓ Layer 7: Healthy (port 8008)
# ✓ Database: Connected
# ✓ All tests passed
```

---

## Step 5: Ingest Your First Document

```bash
# Create a test ingestion job
curl -X POST http://localhost:8000/api/v1/ingestion/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: test-tenant" \
  -d '{
    "source_url": "https://example.com/sample-document.html",
    "source_type": "web",
    "priority": "normal"
  }'

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "pending",
#   "created_at": "2026-04-19T12:00:00Z"
# }
```

---

## Step 6: Open the UI

```bash
# Open in browser
open http://localhost:5173
# Or on Windows: start http://localhost:5173
# Or on Linux: xdg-open http://localhost:5173
```

You'll see the **Command Center** dashboard:

```text
┌────────────────────────────────────────────────────────────┐
│  🏠 Command Center                    [User: admin]        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📊 System Status: All Services Healthy                    │
│                                                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│  │ 📄 New          │ │ 🔍 Browse       │ │ ⚙️ Configure    │  │
│  │ Ingestion       │ │ Knowledge       │ │ Settings        │  │
│  │                 │ │ Graph           │ │                 │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘  │
│                                                            │
│  📈 Recent Activity                                        │
│  • Ingestion job completed (2 min ago)                     │
│  • 3 entities extracted                                    │
└────────────────────────────────────────────────────────────┘
```

---

## Step 7: Query the Knowledge Graph

```bash
# Search for extracted entities
curl "http://localhost:8001/api/v1/entities?query=sample" \
  -H "Authorization: Bearer test-token" \
  -H "X-Tenant-ID: test-tenant"

# Expected: List of entities matching "sample"
```

---

## Next Steps

| Goal | Next Document |
| ---- | ------------- |
| Learn the architecture in depth | [Architecture Overview](../core-concepts/architecture.md) |
| Explore the API | [API Reference](../API_REFERENCE.md) |
| Set up for development | [Local Development Setup](../how-to-guides/setup-local-dev.md) |
| Deploy to production | [Kubernetes Deployment](../../k8s/README.md) |

---

## Troubleshooting

### Issue: "Connection refused" on startup

**Symptoms:** `curl: (7) Failed to connect to localhost port 8000`

**Solution:**

```bash
# Check service status
docker compose ps

# If services are starting, wait 30 seconds for health checks
sleep 30

# If unhealthy, view logs
docker compose logs layer1
```

### Issue: "Migration failed"

**Symptoms:** `alembic.util.exc.CommandError`

**Solution:**

```bash
# Reset and recreate databases
docker compose down -v
docker compose -f docker-compose.full.yml up -d
docker compose run --rm layer1-ingestion alembic upgrade head
```

### Issue: "OpenAI API errors"

**Symptoms:** Extraction jobs fail with 401/429 errors

**Solution:** Verify your `OPENAI_API_KEY` in `.env` and restart:

```bash
docker compose down
docker compose -f docker-compose.full.yml up -d
```

See [Troubleshooting Index](../troubleshooting/index.md) for more solutions.

---

## Common Pitfalls

1. **Port Conflicts:** If ports 5173, 8000-8008 are in use, edit `.env` to change them
2. **Memory Limits:** Docker Desktop needs 8GB+ RAM allocated for all services
3. **Firewall Issues:** Ensure Docker has network access to pull images
4. **API Key Format:** Include the full `sk-` prefix in your OpenAI key
5. **No `value-fabric/` directory:** All commands run from the repo root. The `value-fabric/` path was removed per ADR-021.

---

## Related Documentation

- [Prerequisites](./prerequisites.md) — Detailed requirement checklist
- [Installation](./installation.md) — Full installation with all options
- [Architecture Overview](../core-concepts/architecture.md) — Understanding the 9-service system
- [API Reference](../API_REFERENCE.md) — Complete endpoint documentation
- [ADR-021: Canonical Runtime Path](../explanations/adr/ADR-021-layer-3-canonical-runtime-path.md) — Service-first path policy

---

*Last updated: 2026-06-04 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/getting-started/quickstart.md)*

## Contributor Pathing Reference

- [Layer Runtime Path Governance Matrix](../reference/layer-runtime-path-governance.md) — Where to add new layer code vs compatibility-only paths
