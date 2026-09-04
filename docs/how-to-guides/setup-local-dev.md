---
title: "Local Development Setup"
category: "how-to-guides"
audience: "intermediate"
last-reviewed: "2026-06-12"
freshness: "current"
related: ["../getting-started/quickstart", "../getting-started/environment", "../core-concepts/architecture", "../core-concepts/security-model", "../troubleshooting/index", "../troubleshooting/runbooks/infrastructure/service-down"]
---

# Set Up Local Development Environment

> **In this guide, you will:**
> - Configure a complete development environment
> - Set up hot-reload for all layers
> - Connect debugging tools
> - Enable local testing against production-like data

---

## Prerequisites

Before starting:

1. Complete the [Quickstart Guide](../getting-started/quickstart.md)
2. Install development tools:
   - Python 3.11+ (any patch release; Python 3.11.10 is not specifically required; Make targets resolve `python3.11` first and otherwise require a `python3`/`python` shim that reports >=3.11)
   - Node.js 22.12.0+
   - pnpm 10.34.5 (via corepack)
   - VS Code (recommended) or PyCharm
   - Git with SSH key configured

**Estimated Time:** 45 minutes
**Complexity:** Intermediate

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Development Mode"
        IDE[IDE with<br/>Debugger]

        subgraph "Local Services (Hot Reload)"
            L1_DEV[L1 Dev Server<br/>Port 8001]
            L2_DEV[L2 Dev Server<br/>Port 8002]
            L3_DEV[L3 Dev Server<br/>Port 8003]
            L4_DEV[L4 Dev Server<br/>Port 8004]
            FE_DEV[Frontend Dev<br/>Port 5173]
        end

        subgraph "Docker Services"
            PG[(PostgreSQL)]
            NEO[(Neo4j)]
            RED[(Redis)]
            S3[MinIO]
        end
    end

    subgraph "External"
        OPENAI[OpenAI API]
        GIT[Git Remote]
    end

    IDE -->|Debug| L1_DEV
    IDE -->|Debug| L2_DEV
    IDE -->|Debug| L3_DEV
    IDE -->|Debug| L4_DEV
    IDE -->|Debug| FE_DEV

    L1_DEV -->|Store| PG
    L1_DEV -->|Queue| RED
    L1_DEV -->|Files| S3

    L2_DEV -->|Cache| RED
    L2_DEV -->|LLM| OPENAI

    L3_DEV -->|Graph| NEO
    L3_DEV -->|Vectors| PG

    L4_DEV -->|State| RED
    L4_DEV -->|LLM| OPENAI

    FE_DEV -->|API| L1_DEV
    FE_DEV -->|API| L2_DEV
    FE_DEV -->|API| L3_DEV
    FE_DEV -->|API| L4_DEV

    style IDE fill:#4a90d9,color:white
    style L1_DEV fill:#2ecc71,color:white
    style L2_DEV fill:#2ecc71,color:white
    style L3_DEV fill:#2ecc71,color:white
    style L4_DEV fill:#2ecc71,color:white
    style FE_DEV fill:#2ecc71,color:white
```

---

## Step 1: Clone and Configure

```bash
# Clone the repository
git clone git@github.com:bmsull560/Fabric_4L.git
cd Fabric_4L

# Select Python 3.11 if your shell does not already provide python3.11
pyenv install --skip-existing "$(pyenv latest -k 3.11)"
pyenv local 3.11

# Create Python virtual environments for each layer
# Layer 1
python3.11 -m venv services/layer1-ingestion/.venv
source services/layer1-ingestion/.venv/bin/activate  # Windows: .\services\layer1-ingestion\.venv\Scripts\activate
pip install -e services/layer1-ingestion/[dev]
deactivate

# Repeat for layers 2-4...
```

---

## Step 2: Start Infrastructure Services

```bash
# Start only databases (not application layers)
docker compose up -d postgres neo4j redis minio

# Verify they're ready
./scripts/wait-for-services.sh
```

### Docker Base Image Override

All Python service Dockerfiles default to a private GHCR base image. For local development, you can override this via the `BASE_IMAGE` environment variable (already set in `.env`):

```bash
BASE_IMAGE=python:3.11.11-slim-bookworm
```

When building services via Docker Compose, this override is automatically passed as a build argument. For Layer 3, you can also override the builder stage base image with `BUILDER_BASE_IMAGE`.

---

## Step 3: Configure Hot Reload

> **Note:** The architecture diagram ports are illustrative. Actual service ports depend on your `.env`/Compose configuration and the command-line flags used below.

### Layer 1 (Ingestion)

```bash
cd services/layer1-ingestion
source .venv/bin/activate

# Create dev config
cat > .env.local << EOF
DEBUG=true
RELOAD=true
LOG_LEVEL=debug
DATABASE_URL=postgresql://fabric:fabric@localhost:5432/fabric
REDIS_URL=redis://localhost:6379/0
EOF

# Run with hot reload
uvicorn src.api.main:app --reload --port 8001 --log-level debug
```

### Layer 2 (Extraction)

```bash
cd services/layer2-extraction
source .venv/bin/activate

# Run with hot reload
uvicorn src.layer2_extraction.api.main:app --reload --port 8002 --log-level debug
```

### Layer 3 (Knowledge)

```bash
cd services/layer3-knowledge
source .venv/bin/activate

uvicorn src.api.main:app --reload --port 8003 --log-level debug
```

### Layer 4 (Agents)

```bash
cd services/layer4-agents
source .venv/bin/activate

uvicorn src.api.main:app --reload --port 8004 --log-level debug
```

### Frontend

```bash
cd apps/web
pnpm install --frozen-lockfile
pnpm run dev
```

### Safe Local Auth Workflow

Use real JWT or OIDC flows by default, even in local development. The only sanctioned bypasses are explicit, non-production-only flags for narrow debugging or test harness use.

```bash
# Preferred local defaults
ENVIRONMENT=development
AUTH_REQUIRED=true
JWT_SECRET=<32+ random chars>
API_KEY_HMAC_SECRET=<32+ random chars>
SERVICE_AUTH_SECRET=<32+ random chars>
ALLOW_INSECURE_DEV_AUTH_BYPASS=false
JWT_FALLBACK_TO_QUERY_PARAM=false
ALLOW_EPHEMERAL_ENCRYPTION=false
```

Rules for local auth work:

1. Use `ALLOW_INSECURE_DEV_AUTH_BYPASS=true` only for temporary local debugging when a real JWT or OIDC session is unavailable.
2. Use `JWT_FALLBACK_TO_QUERY_PARAM=true` only in isolated test harnesses that still depend on the legacy Layer 5 fallback path.
3. Use `ALLOW_EPHEMERAL_ENCRYPTION=true` only in local development or tests when you intentionally accept credential loss on restart.
4. Never commit these flags to shared `.env` files, Compose overrides, CI variables, Helm values, or production secrets stores.
5. Production-like startup now fails closed if any bypass flag is enabled.

---

## Step 4: Set Up Debugging

### VS Code Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Layer 1: Ingestion",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.api.main:app", "--reload", "--port", "8001"],
      "cwd": "${workspaceFolder}/services/layer1-ingestion",
      "console": "integratedTerminal"
    },
    {
      "name": "Layer 2: Extraction",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.layer2_extraction.api.main:app", "--reload", "--port", "8002"],
      "cwd": "${workspaceFolder}/services/layer2-extraction"
    },
    {
      "name": "Layer 3: Knowledge",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.api.main:app", "--reload", "--port", "8003"],
      "cwd": "${workspaceFolder}/services/layer3-knowledge"
    },
    {
      "name": "Layer 4: Agents",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.api.main:app", "--reload", "--port", "8004"],
      "cwd": "${workspaceFolder}/services/layer4-agents"
    }
  ],
  "compounds": [
    {
      "name": "All Layers",
      "configurations": [
        "Layer 1: Ingestion",
        "Layer 2: Extraction",
        "Layer 3: Knowledge",
        "Layer 4: Agents"
      ]
    }
  ]
}
```

---

## Step 5: Development Workflow

### Making Changes

```mermaid
sequenceDiagram
    participant D as Developer
    participant IDE as IDE
    participant S as Service
    participant T as Tests

    D->>IDE: Edit code
    IDE->>S: Hot reload triggers
    S->>S: Restart with changes
    S-->>IDE: Ready

    D->>T: Run tests
    T->>T: Unit tests
    T->>T: Integration tests
    T-->>D: Results

    D->>IDE: Commit changes
```

### Testing Changes

```bash
# Run tests for specific layer
cd services/layer3-knowledge
pytest -xvs tests/

# Run with coverage
pytest --cov=src --cov-report=html

# Test specific file
pytest tests/test_entities.py -xvs
```

---

## Common Pitfalls

### Port Already in Use

```bash
# Find process using port
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

### Database Schema Drift

```bash
# Reset database state
docker compose down -v postgres
docker compose up -d postgres

# Re-run migrations
cd services/layer1-ingestion
alembic upgrade head
```

### Python Import Errors

```bash
# Ensure editable install
pip install -e .

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

---

## Next Steps

| Goal | Next Document |
|------|---------------|
| Learn testing patterns | [Testing Strategy](../reference/testing-strategy.md) |
| Set up pre-commit hooks | [Contributing Guidelines](../../CONTRIBUTING.md) |
| Understand the codebase | [Architecture Overview](../core-concepts/architecture.md) |
| Submit your first PR | [PR Process](../../CONTRIBUTING.md) |

---

## Related Documentation

- [Quickstart Guide](../getting-started/quickstart.md) — Get running in 15 minutes
- [Contributing Guidelines](../../CONTRIBUTING.md) — Code and documentation standards
- [Architecture Overview](../core-concepts/architecture.md) — Understanding the 6-layer system
- [Troubleshooting Index](../troubleshooting/index.md) — Common development issues

---

*Last updated: 2026-06-12 | [Edit this page](https://github.com/bmsull560/Fabric_4L/edit/main/docs/how-to-guides/setup-local-dev.md)*
