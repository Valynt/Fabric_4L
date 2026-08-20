# Frequently Asked Questions & Troubleshooting

Quick answers to common questions about Fabric 4L. For detailed guides, see [Tutorials](/tutorials/getting-started) and [How-To Guides](/how-to/).

---

## Getting Started

### Q1: What are the system requirements?

**A:** Fabric 4L requires the following minimum specifications:

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 20 GB free | 50 GB SSD |
| Python | 3.11+ | 3.11+ |
| Node.js | ≥ 22.12.0 | 22.12.0+ (LTS) |
| Package Manager | pnpm 10.18.1 | pnpm 10.18.1 |
| Docker | 24.0+ | Latest stable |
| Docker Compose | 2.20+ (v2 `docker compose`) | Latest stable |

For production deployments, see the [Kubernetes deployment guide](/how-to/deploy-kubernetes).

### Q2: How do I set up without Docker?

**A:** While Docker Compose (`infra/compose/docker-compose.dev.yml`) is the standard approach, you can run services directly on your host:

```bash
# 1. Ensure prerequisites are installed:
# PostgreSQL 15+, Redis 7+, Neo4j, Keycloak, Python 3.11+, Node.js ≥ 22.12.0, pnpm 10.18.1

# 2. Enable pnpm and install frontend/monorepo dependencies
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile

# 3. Set up Python virtual environment and service dependencies
make setup

# 4. Generate local dev env secrets or configure .env
pnpm env:dev
# Or cp .env.example .env and edit to point to your local PostgreSQL/Redis/Neo4j services

# 5. Run database migrations across services
make migrate

# 6. Start individual layers and frontend as needed:
# Frontend (Vite on port 3001)
pnpm dev:web

# Individual backend layers (ports 8001–8006):
pnpm dev:layer1   # Ingestion
pnpm dev:layer2   # Extraction
pnpm dev:layer3   # Knowledge Graph
pnpm dev:layer4   # Agents
pnpm dev:layer5   # Ground Truth
pnpm dev:layer6   # Benchmarks
```

**Note:** Non-Docker setups are supported for local development only. Production deployments must use containers or Kubernetes.

### Q3: Can I use Fabric 4L on Windows/WSL?

**A:** Yes, Windows is supported via WSL2:

```bash
# In WSL2 Ubuntu terminal:
# 1. Ensure WSL2 has sufficient memory
# Edit %USERPROFILE%\.wslconfig:
# [wsl2]
# memory=12GB
# processors=4

# 2. Install Docker Desktop with WSL2 backend enabled
# 3. Follow standard Linux setup
pnpm install --frozen-lockfile
make setup
pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d
make migrate
make verify
```

**Known WSL2 issues:**
- File watchers may need increasing: `echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf`
- Use WSL2 filesystem (not `/mnt/c/`) for best performance
- If Docker is slow, enable "Use the WSL 2 based engine" in Docker Desktop settings

### Q4: How long does setup take?

**A:** Typical setup times by method:

| Method | First Setup | Subsequent |
|--------|-------------|------------|
| Docker (local) | 10-15 min | 2-3 min |
| GitHub Codespaces | 5 min (pre-built) | 2 min |
| Without Docker | 15-30 min | 2-3 min |

The first Docker setup pulls images (~2-3 GB). Subsequent starts use cached images.

### Q5: Where do I get help?

**A:** Support channels ranked by response time:

| Channel | Response Time | Best For |
|---------|---------------|----------|
| [GitHub Issues](https://github.com/bmsull560/Fabric_4L/issues) | 24-48 hours | Bug reports, feature requests |
| [GitHub Discussions](https://github.com/bmsull560/Fabric_4L/discussions) | 24-72 hours | Architecture questions, Q&A |
| [Discord](https://discord.gg/fabric4l) | Real-time | Community chat, quick questions |
| Documentation | Instant | Self-service reference |
| operations@fabric4l.io | 4 hours (business) | Enterprise support, security issues |

When reporting issues, include:
- `make verify` output
- Relevant container logs (`docker logs <container>` or `docker compose -f infra/compose/docker-compose.dev.yml logs <service>`)
- Your environment configuration (with secrets redacted)
- Steps to reproduce

---

## Development

### Q6: How do I add a new service layer?

**A:** Fabric 4L's 6-layer architecture is designed for extension. To add a new microservice:

```bash
# 1. Create service directory under services/
mkdir -p services/layer7-custom/src/layer7_custom

# 2. Create minimal FastAPI app
cat > services/layer7-custom/src/layer7_custom/main.py << 'EOF'
from fastapi import FastAPI, Depends
from value_fabric.shared.tenant import TenantContext, require_tenant_context

app = FastAPI(title="Fabric 4L — Layer 7: Custom Service")

@app.get("/health")
async def health():
    return {"status": "healthy", "layer": "layer7"}

@app.get("/api/v1/status")
async def status(ctx: TenantContext = Depends(require_tenant_context)):
    return {"layer": "layer7", "tenant_id": ctx.tenant_id}
EOF

# 3. Add to infra/compose/docker-compose.dev.yml
# 4. Register in packages/shared and Makefile test targets
# 5. Add health check to make verify
```

**Architecture rules:**
- Each layer must expose a `/health` endpoint
- Protected endpoints require tenant context authentication
- Use the shared `value_fabric.shared.tenant` module for tenant isolation
- Register OpenAPI contracts in `contracts/openapi/`

### Q7: How do I run tests for a single layer?

**A:** Use the layer-specific test targets:

```bash
# Run all tests
make test

# Run tests for a specific layer
make test-layer1    # Layer 1: Ingestion
make test-layer2    # Layer 2: Extraction
make test-layer3    # Layer 3: Knowledge Graph
make test-layer4    # Layer 4: Agents
make test-layer5    # Layer 5: Ground Truth
make test-layer6    # Layer 6: Benchmarks

# Run specific test file
pytest services/layer4-agents/tests/test_audit_orchestrator.py -v

# Run with coverage for one layer
pytest services/layer4-agents/tests/ --cov=services/layer4-agents/src --cov-report=html

# Run only failed tests
pytest --lf

# Run in parallel
pytest -n auto
```

### Q8: How do I debug agent workflows?

**A:** Multiple debugging tools are available:

**1. Trace Inspection (OTel)**
```bash
# Get trace from workflow response
curl http://localhost:8004/v1/repo-audit/runs/run_abc123 \
  -H "Authorization: ******" | jq '.'
```

**2. Workflow Logs**
```bash
# Filter worker logs for specific workflow
docker compose -f infra/compose/docker-compose.dev.yml logs layer4 --tail=100
```

**3. Breakpoint in Code**
```python
# Add breakpoint in your agent tool
import pdb; pdb.set_trace()  # Python debugger
```

### Q9: How do I add a new feature flag?

**A:** Feature flags are managed through the API or configuration:

**Via API (runtime):**
```bash
curl -X PUT http://localhost:8001/api/v1/features/new-flag-name \
  -H "Authorization: ******" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false,
    "default_value": false,
    "description": "Enables the new extraction engine",
    "targeting": {
      "tenants": ["tenant_xxx"],
      "percentage": 10
    }
  }'
```

**In code:**
```python
from value_fabric.shared.features import is_enabled

if is_enabled("new-flag-name", default=False):
    # New behavior
    pass
else:
    # Legacy behavior
    pass
```

### Q10: How do I update database migrations?

**A:** Use Alembic for all database schema changes per service:

```bash
# 1. Navigate to the relevant service directory
cd services/layer4-agents

# 2. Make changes to models, then generate migration
alembic revision --autogenerate -m "Add workflow checkpoint table"

# 3. Review generated migration in migrations/versions/
# 4. Apply migration
alembic upgrade head

# 5. Verify
alembic current

# To rollback one revision:
alembic downgrade -1

# To view migration history:
alembic history --verbose

# Run all layer migrations from repo root:
make migrate
# Check single-head consistency:
make check-migration-heads
```

**Rules:**
- Never modify existing migrations that have been applied to production
- Always test rollback (`alembic downgrade`) before committing
- Include both `upgrade()` and `downgrade()` functions
- Ensure each service has exactly one Alembic head (`make check-migration-heads`)

---

## Deployment

### Q11: What Kubernetes version is required?

**A:** Minimum Kubernetes 1.28+ with the following requirements:

| Component | Version | Notes |
|-----------|---------|-------|
| Kubernetes | 1.28+ | 1.30 recommended |
| Helm | 3.13+ | For chart deployment |
| cert-manager | 1.13+ | For TLS certificates |
| ingress-nginx | 1.9+ | For ingress routing |
| PostgreSQL | 15+ | Managed or self-hosted |
| Redis | 7+ | Cluster mode recommended |

```bash
# Verify cluster compatibility
kubectl version --client
helm version

# Deploy with Helm
helm repo add fabric4l https://charts.fabric4l.io
helm install fabric4l fabric4l/fabric4l \
  --namespace fabric4l \
  --create-namespace \
  --values values.production.yaml
```

### Q12: How do I configure multi-region deployment?

**A:** Fabric 4L supports active-passive multi-region with PostgreSQL streaming replication:

```yaml
# values.multi-region.yaml
global:
  regions:
    primary: us-east-1
    secondary: us-west-2

  replication:
    mode: streaming-async
    lag_threshold_ms: 1000

  failover:
    automatic: true
    health_check_interval: 10s
    failover_timeout: 30s

postgresql:
  primary:
    persistence:
      size: 500Gi
  readReplicas:
    count: 2
```

**Architecture:**
- Primary region handles writes
- Secondary region serves read traffic
- Automatic failover if primary health checks fail
- Object storage (MinIO/S3) is region-aware

See [Multi-Region Deployment Guide](/how-to/multi-region) for detailed setup.

### Q13: How do I rotate database credentials?

**A:** Credentials can be rotated without downtime:

```bash
# 1. Generate new credentials
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Add new credentials to secret store
kubectl create secret generic db-credentials-new \
  --from-literal=****** \
  --namespace fabric4l \
  --dry-run=client -o yaml | kubectl apply -f -

# 3. Update PostgreSQL user
kubectl exec -it fabric4l-db-0 -- psql -U postgres -c \
  "ALTER USER fabric4l WITH PASSWORD '$NEW_PASSWORD';"

# 4. Rolling restart to pick up new credentials
kubectl rollout restart deployment/fabric4l-api -n fabric4l

# 5. Verify connectivity
kubectl exec -it fabric4l-api-xxx -- \
  curl localhost:8001/api/v1/health/detailed | jq '.status'
```

### Q14: How do I scale Layer 4 (Agents)?

**A:** Layer 4 (Agents) can be scaled horizontally:

```bash
# Scale agent workers
kubectl scale deployment fabric4l-agent-worker --replicas=10 -n fabric4l

# Or use HPA (Horizontal Pod Autoscaler)
kubectl autoscale deployment fabric4l-agent-worker \
  --cpu-percent=70 \
  --min=3 \
  --max=20 \
  -n fabric4l

# Monitor scaling
kubectl get hpa fabric4l-agent-worker -n fabric4l -w
```

---

## Security & Compliance

### Q16: How does tenant isolation work?

**A:** Tenant isolation is enforced at multiple layers (Defense in Depth):

| Layer | Mechanism | ADR Reference |
|-------|-----------|---------------|
| Database | PostgreSQL Row-Level Security (RLS) | ADR-021 |
| Application | `value_fabric.shared.tenant.TenantContext` | ADR-028 |
| API | Authenticated Context Pipeline | ADR-029 |
| Network | Namespace isolation in K8s | — |
| Storage | Prefix-scoped object paths | — |

**Verification:**
```bash
# Run tenant boundary security tests
pytest tests/security/ -m tenant_boundary -v
```

### Q17: How do I handle GDPR data deletion requests?

**A:** Fabric 4L provides built-in GDPR endpoints:

```bash
# 1. Initiate deletion (Right to Erasure — Article 17)
curl -X POST http://localhost:8001/api/v1/gdpr/data-deletion \
  -H "Authorization: ******" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "user@example.com",
    "subject_type": "email",
    "reason": "User request - Article 17 GDPR",
    "verification_method": "email_confirmation"
  }'

# 2. Check deletion status
curl http://localhost:8001/api/v1/gdpr/data-deletion/del_abc123 \
  -H "Authorization: ******" | jq '{
    status,
    deleted_records,
    remaining_records,
    estimated_completion
  }'
```

---

## Troubleshooting Decision Trees

### "My tests are failing"

```
Are tests failing consistently or intermittently?
|
|-- CONSISTENT
|   |
|   |-- Did you change code recently?
|   |   |-- YES → Run git diff, check for breaking changes
|   |   |-- NO  → Continue...
|   |
|   |-- Is it a specific test file?
|   |   |-- YES → Run with -v for verbose output:
|   |   |       pytest services/layer4-agents/tests/test_audit_orchestrator.py -v -s
|   |   |-- NO  → Continue...
|   |
|   |-- Is the database migrated?
|   |   |-- Run: make migrate
|   |   |-- Verify: make check-migration-heads
|   |
|   +-- Check test fixtures and dependencies:
|       pytest --fixtures | grep your_fixture
|
|-- INTERMITTENT
    |
    |-- Is it timing-related?
    |   |-- YES → Increase timeouts in test config
    |   |-- NO  → Continue...
    |
    |-- Is it database-related?
    |   |-- YES → Check connection pool settings
    |   |       Ensure test database isolation
    |   |-- NO  → Continue...
    |
    +-- Run full verification:
        make verify
```

### "I can't connect to the database"

```
Is the database container running?
|
|-- NO
|   |-- docker compose -f infra/compose/docker-compose.dev.yml ps postgres
|   |-- docker compose -f infra/compose/docker-compose.dev.yml logs postgres
|   |-- docker compose -f infra/compose/docker-compose.dev.yml up -d postgres
|
|-- YES
    |
    |-- Can you connect locally?
    |   |-- pg_isready -h localhost -p 5432
    |   |-- If "refused": Wait 10s, PostgreSQL may still be starting
    |   |-- If "no response": Check logs for errors
    |
    |-- Are migrations applied?
    |   |-- make migrate
    |
    |-- Is the connection string correct?
    |   |-- Format: postgresql://fabric:fabric@localhost:5432/fabric
    |
    |-- Is the port accessible?
    |   |-- Check docker compose port mapping
    |
    +-- Try resetting:
        docker compose -f infra/compose/docker-compose.dev.yml down -v
        pnpm env:dev && docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.generated up -d
        make migrate
```

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Full verification | `make verify` |
| Check health | `curl http://localhost:8001/health` |
| Run migrations | `make migrate` |
| Check migration heads | `make check-migration-heads` |
| Run backend tests | `make test` |
| Run layer tests | `make test-layer1` .. `make test-layer6` |
| Start frontend dev | `pnpm dev:web` |
| Frontend typecheck & lint | `pnpm --dir apps/web run typecheck && pnpm --dir apps/web run lint` |
| Reset environment | `make clean && make setup` |

---

## Version Information

- **Documentation Version:** v1.2.0
- **Compatible Versions:** v1.2.0+
- **Maintainer:** Fabric 4L Documentation Team

For changes to this FAQ, submit a PR to [`docs/reference/faq.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/reference/faq.md).
