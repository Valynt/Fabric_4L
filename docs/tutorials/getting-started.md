# Getting Started with Fabric 4L

Welcome to Fabric 4L — an enterprise agentic SaaS platform that transforms documents into actionable insights through a six-layer pipeline. This tutorial walks you from zero to running your first agent workflow in under 15 minutes.

**What you'll learn:**
- Launch a complete development environment
- Create a tenant and obtain API credentials
- Upload and process your first document
- Query the knowledge graph
- Run an agent workflow
- View ROI metrics in the dashboard

**Time required:** ~15 minutes  
**Prerequisites:** Docker, Docker Compose, Git, 8GB RAM available

---

## Prerequisites

Before starting, ensure you have the following installed:

| Requirement | Version | Verify Command |
|-------------|---------|----------------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Git | 2.40+ | `git --version` |
| Available RAM | 8GB+ | `free -h` (Linux) / `vm_stat` (macOS) |

### GitHub Codespaces (Alternative)

If you prefer not to install dependencies locally, click below to launch a pre-configured environment:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/bmsull560/Fabric_4L?devcontainer_path=.devcontainer/devcontainer.json)

The Codespace includes all dependencies pre-installed and the development server running on port 3001.

---

## Step 1: Launch Development Environment (2 minutes)

Clone the repository and run the setup script.

```bash
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L
make setup
```

### What `make setup` does

1. Checks Docker and Docker Compose versions
2. Creates local data directories (`data/postgres`, `data/redis`, `data/minio`)
3. Generates development environment file (`.env.dev`)
4. Pulls required Docker images
5. Installs Python dependencies in a virtual environment
6. Installs frontend Node.js dependencies

### Expected Output

```
[Fabric 4L] Checking prerequisites...
[Fabric 4L] Docker version: 24.0.7 ✓
[Fabric 4L] Docker Compose version: 2.23.0 ✓
[Fabric 4L] Creating data directories... ✓
[Fabric 4L] Generating .env.dev... ✓
[Fabric 4L] Pulling Docker images... ✓
[Fabric 4L] Installing Python dependencies... ✓
[Fabric 4L] Installing frontend dependencies... ✓
✅ Environment ready

Next steps:
  make infra-up    # Start infrastructure services
  make migrate     # Run database migrations
  make verify      # Verify the installation
```

### Troubleshooting

**"Docker daemon not running"**
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker

# Verify
docker info
```

**"Port 8001 already in use"**
```bash
# Find and kill the process using port 8001
lsof -ti:8001 | xargs kill -9
# Or change the port in .env.dev: API_PORT=8002
```

**"make: command not found"**
```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt-get install build-essential

# Or run setup manually:
./scripts/setup.sh
```

---

## Step 2: Start Infrastructure (3 minutes)

Start all backend services and run database migrations.

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d
make migrate
```

### What this starts

| Service | Port | Purpose |
|---------|------|---------|
| API (L1-L6) | 8001 | Main API gateway |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Caching & queues |
| MinIO | 9000 | Object storage (S3-compatible) |
| Tempo | 4317 | OpenTelemetry trace collection |

### Expected Output

```
[+] Running 6/6
 ⠿ Network fabric4l_dev     Created
 ⠿ Container fabric4l-db    Started
 ⠿ Container fabric4l-redis Started
 ⠿ Container fabric4l-minio Started
 ⠿ Container fabric4l-tempo Started
 ⠿ Container fabric4l-api   Started

Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0032, v1.2.0 schema
✅ Migrations complete
```

### Verify Services

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Expected:** All containers show `(healthy)` or `Up` status.

```
NAMES           STATUS                    PORTS
fabric4l-api    Up 30 seconds (healthy)   0.0.0.0:8001->8001/tcp
fabric4l-db     Up 30 seconds (healthy)   0.0.0.0:5432->5432/tcp
fabric4l-redis  Up 30 seconds (healthy)   0.0.0.0:6379->6379/tcp
fabric4l-minio  Up 30 seconds (healthy)   0.0.0.0:9000->9000/tcp
fabric4l-tempo  Up 30 seconds             0.0.0.0:4317->4317/tcp
```

### Troubleshooting

**"Migration fails with connection refused"**
```bash
# Wait for PostgreSQL to be ready, then retry:
docker compose -f infra/compose/docker-compose.dev.yml logs -f fabric4l-db
# When you see "database system is ready to accept connections", retry:
make migrate
```

**"Container unhealthy"**
```bash
# Check specific container logs
docker logs fabric4l-api

# Common fix: insufficient disk space
docker system prune -f

# Restart services
docker compose -f infra/compose/docker-compose.dev.yml restart
```

---

## Step 3: Run Verification (2 minutes)

Run the comprehensive verification suite to confirm everything is working.

```bash
make verify
```

### What `make verify` checks

| Check | Description |
|-------|-------------|
| Database connectivity | Can connect to PostgreSQL |
| Migration status | All migrations applied |
| API health | All layers respond to health checks |
| Redis connectivity | Cache and queue available |
| MinIO connectivity | Object storage accessible |
| OTel pipeline | Trace collection working |
| Feature flags | Flag system operational |
| Contract compliance | All ADRs validated |

### Expected Output

```
[Fabric 4L] Running verification suite...

✓ Database connectivity
✓ Migration status (32/32 applied)
✓ API Layer 1 (Ingestion) — healthy
✓ API Layer 2 (Extraction) — healthy
✓ API Layer 3 (Knowledge) — healthy
✓ API Layer 4 (Agents) — healthy
✓ API Layer 5 (Ground Truth) — healthy
✓ API Layer 6 (Benchmarks) — healthy
✓ Redis connectivity
✓ MinIO connectivity
✓ OpenTelemetry pipeline
✓ Feature flag system
✓ Contract compliance (6/6 ADRs compliant)

✅ All checks passed (12/12)

Services:
  Frontend:  http://localhost:3001
  API:       http://localhost:8001
  API Docs:  http://localhost:8001/api/docs
```

### Troubleshooting

**"Contract compliance failed"**
```bash
# View detailed contract status
curl http://localhost:8001/api/v1/admin/contracts | jq

# This is non-blocking for development; check specific warnings
```

**"MinIO connectivity failed"**
```bash
# MinIO takes longer to initialize on first boot
sleep 10 && make verify

# Or check MinIO logs
docker logs fabric4l-minio
```

---

## Step 4: Create Your First Tenant (1 minute)

Create a tenant to isolate your data and obtain API credentials.

```bash
curl -X POST http://localhost:8001/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Tenant",
    "tier": "shared",
    "admin_email": "admin@example.com"
  }'
```

### Expected Output

```json
{
  "id": "tenant_2v8x4k1m9p",
  "name": "My First Tenant",
  "tier": "shared",
  "api_key": "fab_test_dummy_ak_live_placeholder",
  "status": "active",
  "created_at": "2026-07-14T10:30:00Z",
  "settings": {
    "max_documents": 1000,
    "max_workflows_per_day": 100,
    "features": ["basic_ingestion", "knowledge_graph", "insight_generation"]
  }
}
```

### Save Your API Key

```bash
# Save the API key for subsequent commands
export API_KEY="fab_test_dummy_ak_live_placeholder"  # Replace with your actual key

echo "API_KEY=$API_KEY" >> .env.dev
```

**Important:** Your API key grants access to your tenant's data. Store it securely and never commit it to version control.

### Troubleshooting

**"Tenant creation failed: validation error"**
```bash
# Ensure all required fields are provided: name, tier, admin_email
# tier must be one of: shared, dedicated, enterprise
# admin_email must be a valid email format
```

**"Tenant creation failed: database error"**
```bash
# Ensure migrations are applied
make migrate

# Check database connectivity
docker exec fabric4l-db pg_isready -U fabric4l
```

---

## Step 5: Upload Your First Document (2 minutes)

Upload a PDF document to the ingestion pipeline. The system will automatically queue it for text extraction and knowledge graph processing.

```bash
curl -X POST http://localhost:8001/api/v1/ingestion/documents \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample-document.pdf" \
  -F "metadata={\"source\": \"tutorial\", \"language\": \"en\"}"
```

Don't have a sample PDF? Create one:

```bash
# Generate a sample PDF (requires Python with reportlab)
python -c "
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
c = canvas.Canvas('sample-document.pdf', pagesize=letter)
c.drawString(100, 700, 'Fabric 4L Sample Document')
c.drawString(100, 680, 'This document demonstrates the extraction pipeline.')
c.drawString(100, 660, 'Key themes: automation, knowledge graphs, agent workflows.')
c.drawString(100, 640, 'Contact: info@fabric4l.io')
c.save()
print('Created sample-document.pdf')
"
```

### Expected Output

```json
{
  "document_id": "doc_7f3a9b2e4c",
  "filename": "sample-document.pdf",
  "file_size": 45231,
  "mime_type": "application/pdf",
  "extraction_status": "queued",
  "extraction_id": "ext_9k2m4p7q1r",
  "tenant_id": "tenant_2v8x4k1m9p",
  "uploaded_at": "2026-07-14T10:32:15Z",
  "estimated_processing_time": "30s",
  "metadata": {
    "source": "tutorial",
    "language": "en"
  }
}
```

### Check Extraction Status

```bash
curl http://localhost:8001/api/v1/ingestion/documents/doc_7f3a9b2e4c \
  -H "Authorization: Bearer $API_KEY" | jq '{document_id, extraction_status, extraction_progress}'
```

Poll until `extraction_status` changes to `"completed"`:

```json
{
  "document_id": "doc_7f3a9b2e4c",
  "extraction_status": "completed",
  "extraction_progress": 100,
  "pages_processed": 1,
  "text_extracted": true,
  "entities_extracted": 5,
  "completed_at": "2026-07-14T10:32:45Z"
}
```

### Troubleshooting

**"File too large"**
```bash
# Default max file size is 50MB
# For larger files, use the chunked upload endpoint:
curl -X POST http://localhost:8001/api/v1/ingestion/documents/chunked \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@large-document.pdf"
```

**"Unsupported file type"**
```bash
# Supported formats: PDF, DOCX, TXT, MD, PNG, JPG, TIFF
# For other formats, convert first:
libreoffice --headless --convert-to pdf document.doc
```

**"Extraction stuck at queued"**
```bash
# Check worker status
docker logs fabric4l-worker

# Restart extraction pipeline
docker compose -f infra/compose/docker-compose.dev.yml restart worker

# Or trigger manual extraction
curl -X POST http://localhost:8001/api/v1/ingestion/documents/doc_7f3a9b2e4c/retry \
  -H "Authorization: Bearer $API_KEY"
```

---

## Step 6: View Extracted Knowledge (2 minutes)

Query the knowledge graph to see the entities and relationships extracted from your document.

```bash
curl http://localhost:8003/api/v1/knowledge/graph \
  -H "Authorization: Bearer $API_KEY" \
  -G -d "document_id=doc_7f3a9b2e4c" -d "depth=2" -d "include_metadata=true"
```

### Expected Output

```json
{
  "document_id": "doc_7f3a9b2e4c",
  "graph": {
    "nodes": [
      {
        "id": "ent_1a2b3c4d",
        "type": "ORGANIZATION",
        "label": "Fabric 4L",
        "properties": {
          "confidence": 0.98,
          "source_text": "Fabric 4L Sample Document",
          "position": { "page": 1, "x": 100, "y": 700 }
        }
      },
      {
        "id": "ent_5e6f7g8h",
        "type": "CONCEPT",
        "label": "automation",
        "properties": {
          "confidence": 0.95,
          "source_text": "automation",
          "category": "technology"
        }
      },
      {
        "id": "ent_9i0j1k2l",
        "type": "CONCEPT",
        "label": "knowledge graphs",
        "properties": {
          "confidence": 0.93,
          "source_text": "knowledge graphs",
          "category": "technology"
        }
      },
      {
        "id": "ent_3m4n5o6p",
        "type": "CONCEPT",
        "label": "agent workflows",
        "properties": {
          "confidence": 0.94,
          "source_text": "agent workflows",
          "category": "technology"
        }
      }
    ],
    "relationships": [
      {
        "id": "rel_7q8r9s0t",
        "source": "ent_1a2b3c4d",
        "target": "ent_5e6f7g8h",
        "type": "RELATED_TO",
        "properties": { "confidence": 0.91, "context": "document content" }
      },
      {
        "id": "rel_1u2v3w4x",
        "source": "ent_1a2b3c4d",
        "target": "ent_9i0j1k2l",
        "type": "RELATED_TO",
        "properties": { "confidence": 0.89, "context": "document content" }
      }
    ],
    "statistics": {
      "total_nodes": 4,
      "total_relationships": 2,
      "entity_types": { "ORGANIZATION": 1, "CONCEPT": 3 },
      "average_confidence": 0.95
    }
  }
}
```

### Query the Graph with Natural Language

```bash
curl -X POST http://localhost:8003/api/v1/knowledge/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What technologies are mentioned?",
    "document_ids": ["doc_7f3a9b2e4c"]
  }'
```

### Troubleshooting

**"Graph is empty"**
```bash
# Ensure extraction completed
curl http://localhost:8001/api/v1/ingestion/documents/doc_7f3a9b2e4c \
  -H "Authorization: Bearer $API_KEY" | jq '.extraction_status'

# If not completed, wait and retry
```

**"Authorization failed"**
```bash
# Verify API_KEY is set
echo $API_KEY

# If empty, set it again from Step 4 output
export API_KEY="fab_ak_live_..."
```

---

## Step 7: Run Your First Agent Workflow (3 minutes)

Execute an insight generation workflow that analyzes your document and produces actionable insights.

```bash
curl -X POST http://localhost:8004/api/v1/workflows/run \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_type": "insight_generation",
    "inputs": {
      "query": "What are the key themes?",
      "document_ids": ["doc_7f3a9b2e4c"],
      "insight_depth": "detailed"
    },
    "feature_flags": {
      "new-extraction-engine": true,
      "insight-model-version": "v2"
    }
  }'
```

### Expected Output

```json
{
  "workflow_id": "wf_3n5p7q9r2s",
  "status": "running",
  "estimated_completion": "2026-07-14T10:38:00Z",
  "trace_id": "trace_a1b2c3d4e5f6",
  "started_at": "2026-07-14T10:35:00Z",
  "_links": {
    "self": "/api/v1/workflows/wf_3n5p7q9r2s",
    "results": "/api/v1/workflows/wf_3n5p7q9r2s/results",
    "cancel": "/api/v1/workflows/wf_3n5p7q9r2s/cancel"
  }
}
```

### Poll for Completion

```bash
# Poll every 5 seconds until complete
while true; do
  STATUS=$(curl -s http://localhost:8004/api/v1/workflows/wf_3n5p7q9r2s \
    -H "Authorization: Bearer $API_KEY" | jq -r '.status')
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 5
done
```

### View Results

```bash
curl http://localhost:8004/api/v1/workflows/wf_3n5p7q9r2s/results \
  -H "Authorization: Bearer $API_KEY" | jq '.payload'
```

**Expected:**
```json
{
  "insights": [
    {
      "id": "ins_8t9u0v1w",
      "type": "theme_extraction",
      "title": "Core Technology Themes",
      "description": "The document identifies three core technology themes: automation, knowledge graphs, and agent workflows. These represent the foundational pillars of the Fabric 4L platform.",
      "confidence": 0.96,
      "evidence": [
        { "text": "automation, knowledge graphs, agent workflows", "document_id": "doc_7f3a9b2e4c", "page": 1 }
      ],
      "metadata": {
        "processing_time_ms": 4200,
        "model_version": "insight-v2.1"
      }
    }
  ],
  "summary": {
    "total_insights": 1,
    "average_confidence": 0.96,
    "processing_time_ms": 4200
  }
}
```

### View Distributed Trace

```bash
# View the OTel trace
curl http://localhost:8001/api/v1/traces/trace_a1b2c3d4e5f6 \
  -H "Authorization: Bearer $API_KEY" | jq '.spans[] | {service, operation, duration_ms}'
```

Or open the trace in Jaeger at http://localhost:16686 (if enabled).

### Troubleshooting

**"Workflow failed: insufficient_quota"**
```bash
# Your tenant may have hit the daily workflow limit
# Check quota usage:
curl http://localhost:8001/api/v1/tenants/current \
  -H "Authorization: Bearer $API_KEY" | jq '.usage'

# For development, increase limits in tenant settings
```

**"Workflow timed out"**
```bash
# Check worker logs
docker logs fabric4l-worker | grep wf_3n5p7q9r2s

# Retry the workflow
curl -X POST http://localhost:8004/api/v1/workflows/wf_3n5p7q9r2s/retry \
  -H "Authorization: Bearer $API_KEY"
```

**"Feature flag not recognized"**
```bash
# List available feature flags
curl http://localhost:8001/api/v1/features \
  -H "Authorization: Bearer $API_KEY" | jq '.flags | keys'

# Use only flags returned by this endpoint
```

---

## Step 8: View ROI Analysis (1 minute)

Open the frontend dashboard to see the ROI panel with your processing metrics.

### Start the Frontend

If not already running:

```bash
pnpm dev:web
# Or: pnpm --dir apps/web run dev
```

### Open Dashboard

Navigate to http://localhost:3001 and log in with your tenant credentials.

### Expected Dashboard View

```
┌─────────────────────────────────────────────────────────────┐
│  Fabric 4L Dashboard                    Tenant: My First    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ROI Summary                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐    │
│  │ Documents   │  │ Insights    │  │ Time Saved       │    │
│  │ Processed   │  │ Generated   │  │                  │    │
│  │             │  │             │  │                  │    │
│  │     1       │  │     1       │  │   ~45 minutes   │    │
│  │             │  │             │  │                  │    │
│  │ PDF         │  │ Theme       │  │ vs. manual      │    │
│  │ extraction  │  │ extraction  │  │ analysis        │    │
│  └─────────────┘  └─────────────┘  └──────────────────┘    │
│                                                             │
│  Recent Activity                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 10:35  Insight workflow completed — wf_3n5p7q9r2s  │   │
│  │ 10:32  Document uploaded — sample-document.pdf      │   │
│  │ 10:30  Tenant created — My First Tenant             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### API Alternative (Headless)

If you prefer not to use the frontend:

```bash
curl http://localhost:8001/api/v1/tenants/current/usage \
  -H "Authorization: Bearer $API_KEY" | jq '{
  documents_processed,
  insights_generated,
  workflows_run,
  processing_time_saved_minutes
}'
```

**Expected:**
```json
{
  "documents_processed": 1,
  "insights_generated": 1,
  "workflows_run": 1,
  "processing_time_saved_minutes": 45
}
```

### Troubleshooting

**"Frontend shows connection error"**
```bash
# Ensure API is running
curl http://localhost:8001/api/v1/health/detailed | jq '.status'

# Check CORS settings in .env
# Ensure API_URL points to http://localhost:8001
```

**"Dashboard shows empty data"**
```bash
# Wait a few seconds for metrics aggregation
# Or force refresh: curl -X POST http://localhost:8001/api/v1/metrics/refresh \
#   -H "Authorization: Bearer $API_KEY"
```

---

## Cleanup

When you're done exploring, stop all services:

```bash
# Stop all containers
docker compose -f infra/compose/docker-compose.dev.yml down

# To also remove volumes (deletes all data):
docker compose -f infra/compose/docker-compose.dev.yml down -v

# To reset everything and start fresh:
make clean && make setup
```

---

## Next Steps

Now that you have a working Fabric 4L environment, explore these tutorials:

| Tutorial | What You'll Learn | Time |
|----------|-----------------|------|
| [Building Custom Workflows](/docs/tutorials/custom-workflows) | Create multi-step agent workflows with custom tools | 20 min |
| [Knowledge Graph Querying](/docs/tutorials/knowledge-graph) | Advanced graph queries, filtering, and visualization | 15 min |
| [Agent Configuration](/docs/tutorials/agent-config) | Configure agent behavior, models, and output formats | 15 min |
| [Feature Flags & Kill Switches](/docs/tutorials/feature-flags) | Safely roll out features and handle emergencies | 10 min |

### Quick Reference

| Resource | URL |
|----------|-----|
| API Documentation (Scalar) | http://localhost:8001/api/docs |
| Grafana Dashboards | http://localhost:3000 (if enabled) |
| Feature Flag Admin | http://localhost:8001/api/v1/features |
| Contract Dashboard | http://localhost:8001/api/v1/admin/contracts |

---

## Full Verification Script

Save this script to verify your entire setup:

```bash
#!/bin/bash
# verify-setup.sh — Comprehensive setup verification

set -euo pipefail

API_KEY="${API_KEY:-}"
BASE_URL="${BASE_URL:-http://localhost:8001}"

echo "=== Fabric 4L Setup Verification ==="
echo ""

# Test health
echo -n "Health check... "
HEALTH=$(curl -sf "$BASE_URL/api/v1/health/detailed" | jq -r '.status')
[ "$HEALTH" = "healthy" ] && echo "PASS" || { echo "FAIL"; exit 1; }

# Test tenant
echo -n "Tenant access... "
curl -sf "$BASE_URL/api/v1/tenants/current" -H "Authorization: Bearer $API_KEY" > /dev/null
echo "PASS"

# Test ingestion
echo -n "Document ingestion... "
curl -sf "$BASE_URL/api/v1/ingestion/documents" \
  -H "Authorization: Bearer $API_KEY" | jq '.documents' > /dev/null
echo "PASS"

# Test knowledge
echo -n "Knowledge graph... "
curl -sf "$BASE_URL/api/v3/knowledge/graph" \
  -H "Authorization: Bearer $API_KEY" | jq '.graph.nodes' > /dev/null
echo "PASS"

# Test workflows
echo -n "Workflow engine... "
curl -sf "$BASE_URL/api/v4/workflows" \
  -H "Authorization: Bearer $API_KEY" | jq '.workflows' > /dev/null
echo "PASS"

# Test feature flags
echo -n "Feature flags... "
curl -sf "$BASE_URL/api/v1/features" \
  -H "Authorization: Bearer $API_KEY" | jq '.flags' > /dev/null
echo "PASS"

echo ""
echo "=== All verifications passed ==="
```

Run with: `bash verify-setup.sh`
