# Frequently Asked Questions & Troubleshooting

> **Audit note (2026-07-18):** Several answers below reference legacy paths and commands (`npm install`, `cd frontend && npm run dev`, `backend/`, `frontend/`). The production frontend is at `apps/web/`, backend services are under `services/`, and the package manager is `pnpm`. Update setup and build instructions accordingly.

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
| Docker | 24.0+ | Latest stable |
| Docker Compose | 2.20+ | Latest stable |

For production deployments, see the [Kubernetes deployment guide](/how-to/deploy-kubernetes).

### Q2: How do I set up without Docker?

**A:** While Docker is the recommended approach, you can run services directly:

```bash
# 1. Install dependencies manually
# PostgreSQL 15+, Redis 7+, MinIO, Python 3.11+, Node.js 20+

# 2. Configure environment
cp .env.example .env
# Edit .env to point to your local services

# 3. Install Python dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend && npm install

# 5. Run database migrations
alembic upgrade head

# 6. Start services individually
# Terminal 1: API
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Worker
celery -A worker worker --loglevel=info
```

**Note:** Non-Docker setups are supported for development only. Production deployments must use Docker or Kubernetes.

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
make setup
make infra-up
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
| Without Docker | 30-60 min | 5 min |

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
- Relevant container logs (`docker logs <container>`)
- Your `.env.dev` (with secrets redacted)
- Steps to reproduce

---

## Development

### Q6: How do I add a new service layer?

**A:** Fabric 4L's 6-layer architecture is designed for extension. To add a new microservice:

```bash
# 1. Create service directory
mkdir backend/services/mynewlayer

# 2. Create minimal FastAPI app
cat > backend/services/mynewlayer/main.py << 'EOF'
from fastapi import FastAPI, Depends
from middleware.auth import require_auth

app = FastAPI(title="Fabric 4L — Layer X: My New Layer")

@app.get("/health")
async def health():
    return {"status": "healthy", "layer": "mynewlayer"}

@app.get("/api/vX/status")
async def status(user=Depends(require_auth)):
    return {"layer": "mynewlayer", "user": user.tenant_id}
EOF

# 3. Add to docker-compose.dev.yml
# 4. Register in API gateway
# 5. Add health check to make verify

# See full guide: /how-to/add-new-service
```

**Architecture rules:**
- Each layer must expose `/health` endpoint
- All endpoints require `require_auth` dependency
- Use the shared `tenant_context` for tenant isolation (ADR-028)
- Register in the API gateway for routing

### Q7: How do I run tests for a single layer?

**A:** Use the layer-specific test targets:

```bash
# Run all tests
make test

# Run tests for a specific layer
make test-l1    # Layer 1: Ingestion
make test-l2    # Layer 2: Extraction
make test-l3    # Layer 3: Knowledge
make test-l4    # Layer 4: Agents
make test-l5    # Layer 5: Ground Truth
make test-l6    # Layer 6: Benchmarks

# Run specific test file
pytest backend/tests/l4/test_workflows.py -v

# Run with coverage for one layer
pytest backend/tests/l4/ --cov=backend/l4 --cov-report=html

# Run only failed tests
pytest --lf

# Run in parallel (4 workers)
pytest -n 4
```

### Q8: How do I debug agent workflows?

**A:** Multiple debugging tools are available:

**1. Trace Inspection (OTel)**
```bash
# Get the trace_id from workflow response
curl http://localhost:8001/api/v1/traces/trace_a1b2c3d4e5f6 \
  -H "Authorization: Bearer $API_KEY" | jq '.spans'
```

**2. Workflow Logs**
```bash
# Filter worker logs for specific workflow
docker logs fabric4l-worker 2>&1 | grep wf_3n5p7q9r2s

# Or use structured logging
jq 'select(.workflow_id == "wf_3n5p7q9r2s")' logs/structured/worker.jsonl
```

**3. Step-by-Step Execution**
```python
# Enable debug mode to execute synchronously with verbose output
response = client.workflows.run(
    workflow_type="insight_generation",
    inputs={"query": "test"},
    debug=True  # Returns step-by-step execution log
)
```

**4. Breakpoint in Code**
```python
# Add breakpoint in your agent tool
import pdb; pdb.set_trace()  # Python debugger

# Or use the built-in debug endpoint
curl -X POST http://localhost:8004/api/v1/workflows/debug \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"workflow_type": "insight_generation", "inputs": {"query": "test"}}'
```

### Q9: How do I add a new feature flag?

**A:** Feature flags are managed through the API or configuration:

**Via API (runtime):**
```bash
curl -X PUT http://localhost:8001/api/v1/features/new-flag-name \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
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

**Via configuration (static):**
```yaml
# config/features.yaml
new-flag-name:
  enabled: false
  default_value: false
  description: "Enables the new extraction engine"
  targeting:
    tenants: []
    percentage: 0
```

**In code:**
```python
from core.features import is_enabled

if is_enabled("new-flag-name", default=False):
    # New behavior
    pass
else:
    # Legacy behavior
    pass
```

### Q10: How do I update database migrations?

**A:** Use Alembic for all database schema changes:

```bash
# 1. Make changes to SQLAlchemy models
# 2. Generate migration
alembic revision --autogenerate -m "Add user preferences table"

# 3. Review generated migration in backend/migrations/versions/
# 4. Apply migration
alembic upgrade head

# 5. Verify
alembic current

# To rollback one revision:
alembic downgrade -1

# To view migration history:
alembic history --verbose
```

**Rules:**
- Never modify existing migrations that have been applied to production
- Always test rollback (`alembic downgrade`) before committing
- Include both `upgrade()` and `downgrade()` functions
- Mark destructive migrations with `op.execute("-- destructive change")`

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
  --from-literal=password="$NEW_PASSWORD" \
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

# 6. Remove old secret after confirming stability (24h+)
# kubectl delete secret db-credentials -n fabric4l
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

**Scaling factors:**
- CPU/memory: Agent workers are CPU-bound during model inference
- Queue depth: Monitor Redis queue length for backpressure
- GPU: For LLM-based agents, GPU nodes may be required

### Q15: How do I perform a zero-downtime deployment?

**A:** Use the built-in blue-green deployment:

```bash
# 1. Deploy new version to green environment
helm upgrade fabric4l-green fabric4l/fabric4l \
  --namespace fabric4l \
  --set image.tag=v1.2.1 \
  --values values.production.yaml

# 2. Run smoke tests against green
SMOKE_URL=$(kubectl get svc fabric4l-green -n fabric4l -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
make smoke-test URL=http://$SMOKE_URL

# 3. Switch traffic to green
kubectl patch service fabric4l -n fabric4l -p \
  '{"spec":{"selector":{"app":"fabric4l","version":"green"}}}'

# 4. Monitor for errors
# If issues detected, switch back:
kubectl patch service fabric4l -n fabric4l -p \
  '{"spec":{"selector":{"app":"fabric4l","version":"blue"}}}'
```

---

## Security & Compliance

### Q16: How does tenant isolation work?

**A:** Tenant isolation is enforced at multiple layers (Defense in Depth):

| Layer | Mechanism | ADR Reference |
|-------|-----------|---------------|
| Database | PostgreSQL Row-Level Security (RLS) | ADR-021 |
| Application | AsyncLocalStorage tenant context | ADR-028 |
| API | 8-phase auth pipeline | ADR-029 |
| Network | Namespace isolation in K8s | — |
| Storage | Prefix-scoped object paths | — |

**Verification:**
```bash
# Verify RLS is active
kubectl exec -it fabric4l-db-0 -- psql -U fabric4l -c \
  "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';"

# Expected: All tenant tables show rowsecurity = true
```

**Breach response:** See [Q23: Tenant isolation breach response](#q23-how-do-i-respond-to-a-tenant-isolation-breach).

### Q17: How do I handle GDPR data deletion requests?

**A:** Fabric 4L provides built-in GDPR endpoints:

```bash
# 1. Initiate deletion (Right to Erasure — Article 17)
curl -X POST http://localhost:8001/api/v1/gdpr/data-deletion \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "user@example.com",
    "subject_type": "email",
    "reason": "User request - Article 17 GDPR",
    "verification_method": "email_confirmation"
  }'

# 2. Check deletion status
curl http://localhost:8001/api/v1/gdpr/data-deletion/del_abc123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '{
    status,
    deleted_records,
    remaining_records,
    estimated_completion
  }'
```

**What gets deleted:**
- All documents associated with the subject
- Knowledge graph nodes and relationships
- Workflow history and results
- Audit logs older than retention period
- Feature flag targeting records

**What is retained (anonymized):**
- Aggregate metrics (with subject ID hashed)
- Billing records (as required by law)
- Security incident records

**Timeline:** Deletion completes within 30 days per GDPR requirements. Status can be checked at any time.

### Q18: What security headers are enforced?

**A:** The following headers are enforced on all API responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HSTS |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing protection |
| `X-Frame-Options` | `DENY` | Clickjacking protection |
| `Content-Security-Policy` | `default-src 'self'` | XSS mitigation |
| `X-Request-ID` | `<uuid>` | Request tracing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Referrer control |
| `Permissions-Policy` | `camera=(), microphone=()` | Feature restriction |

**Verification:**
```bash
curl -I http://localhost:8001/api/v1/health/detailed | grep -i "strict-transport\|x-content\|x-frame\|content-security"
```

### Q19: How do I report a security vulnerability?

**A:** Security issues should be reported privately:

1. **Email:** security@fabric4l.io (PGP key available)
2. **Do not** open public GitHub issues for security bugs
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

**Response timeline:**
- Acknowledgment within 24 hours
- Initial assessment within 72 hours
- Fix timeline communicated within 1 week
- Public disclosure coordinated after fix

See [SECURITY.md](https://github.com/bmsull560/Fabric_4L/blob/main/SECURITY.md) for full policy.

### Q20: How is audit logging handled?

**A:** All sensitive operations are audited:

```bash
# Query audit logs
curl http://localhost:8001/api/v1/admin/audit-log \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -G -d "resource_type=tenant" -d "action=delete" -d "limit=100"
```

**Logged events:**
- Tenant CRUD operations
- API key creation/revocation
- GDPR data deletion
- Feature flag changes
- Kill switch activation
- Database migrations
- Authentication failures

**Log format (structured JSON):**
```json
{
  "timestamp": "2026-07-14T10:30:00Z",
  "event_type": "tenant_deleted",
  "actor": { "type": "user", "id": "user_abc", "email": "admin@example.com" },
  "resource": { "type": "tenant", "id": "tenant_xyz" },
  "action": "delete",
  "result": "success",
  "ip_address": "10.0.0.1",
  "user_agent": "Mozilla/5.0...",
  "request_id": "req_123",
  "metadata": { "reason": "User request" }
}
```

**Retention:** 1 year for standard logs, 7 years for compliance-related logs.

---

## Operations

### Q21: How do I access Grafana dashboards?

**A:** Grafana is available at the configured URL (default: http://localhost:3000):

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| System Overview | `/d/system-overview` | CPU, memory, disk, network |
| API Performance | `/d/api-performance` | Request rates, latencies, errors |
| SLO Compliance | `/d/slo-compliance` | All 6 SLOs with burn rates |
| Agent Workflows | `/d/agent-workflows` | Workflow execution metrics |
| Knowledge Graph | `/d/knowledge-graph` | Graph statistics and health |
| Feature Flags | `/d/feature-flags` | Flag usage and performance impact |

**Login:** Default credentials are set during setup. Change immediately:
```bash
# Reset admin password
kubectl exec -it fabric4l-grafana-0 -- grafana-cli admin reset-admin-password $NEW_PASSWORD
```

### Q22: What are the critical alerts and their meanings?

**A:** Critical alerts (P1 — immediate response required):

| Alert | Meaning | Response |
|-------|---------|----------|
| `TenantIsolationBreach` | Cross-tenant data access detected | [Run DR-001](/runbooks/dr-001-tenant-isolation) |
| `SLOBurnRateCritical` | Error budget exhausted in < 3 days | Scale resources or disable features |
| `DatabaseConnectionsExhausted` | Connection pool saturated | Check for connection leaks, scale DB |
| `AgentWorkerQueueBacklog` | > 1000 pending workflows | Scale agent workers |
| `KillSwitchActivated` | Emergency kill switch is active | Investigate root cause, prepare fix |

**Warning alerts (P2 — respond within 4 hours):**

| Alert | Meaning | Response |
|-------|---------|----------|
| `HighLatencyP99` | P99 latency > 500ms | Check resource usage, review slow queries |
| `DiskSpaceWarning` | Disk > 80% full | Clean old exports, scale storage |
| `CertificateExpiring` | TLS cert expires in < 30 days | Renew certificate |
| `FeatureFlagDrift` | Flag config differs from code | Sync feature flag definitions |

Alert routing is configured in `infra/alertmanager/alertmanager.yml`.

### Q23: How do I respond to a tenant isolation breach?

**A:** Follow the DR-001 runbook:

```bash
# STEP 1: Confirm the breach
curl http://localhost:8001/api/v1/admin/audit-log \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -G -d "event_type=tenant_isolation_breach" | jq '.events'

# STEP 2: Activate emergency kill switch
curl -X POST http://localhost:8001/api/v1/killswitches/ingestion/activate \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "Tenant isolation breach detected"}'

# STEP 3: Isolate affected tenants
curl -X POST http://localhost:8001/api/v1/admin/tenants/isolate \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"tenant_ids": ["tenant_affected"], "reason": "Isolation breach"}'

# STEP 4: Preserve evidence
# Audit logs are automatically preserved
curl http://localhost:8001/api/v1/admin/audit-log/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"start": "2026-07-14T00:00:00Z", "format": "json"}'

# STEP 5: Notify security team
curl -X POST http://localhost:8001/api/v1/admin/security-incident \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "severity": "critical",
    "type": "tenant_isolation_breach",
    "description": "Cross-tenant data access detected",
    "affected_tenants": ["tenant_affected"]
  }'

# STEP 6: Post-incident review within 24 hours
```

### Q24: How do I perform disaster recovery?

**A:** DR procedures are documented in 5 runbooks:

| Runbook | Scenario | RTO | RPO |
|---------|----------|-----|-----|
| [DR-001](/runbooks/dr-001) | Tenant isolation breach | 15 min | 0 |
| [DR-002](/runbooks/dr-002) | Database corruption | 30 min | 5 min |
| [DR-003](/runbooks/dr-003) | Complete region failure | 1 hour | 5 min |
| [DR-004](/runbooks/dr-004) | API layer cascade failure | 10 min | 0 |
| [DR-005](/runbooks/dr-005) | Data center network partition | 20 min | 0 |

**Quick recovery commands:**

```bash
# Restore from latest backup
make dr-restore BACKUP_DATE=latest

# Failover to secondary region
make dr-failover TARGET_REGION=us-west-2

# Verify recovery
make dr-verify
```

### Q25: How do I interpret SLO burn rate alerts?

**A:** SLO burn rate alerts indicate how fast you're consuming your error budget:

```bash
# View current SLO status
curl http://localhost:8001/api/v1/slos \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.slos[] | {
    name,
    target,
    current_value,
    burn_rate,
    days_remaining
  }'
```

**Burn rate interpretation:**

| Burn Rate | Meaning | Action |
|-----------|---------|--------|
| < 1x | On track to meet SLO | None |
| 1-2x | Slightly elevated | Monitor closely |
| 2-6x | Fast budget burn | Investigate, prepare mitigation |
| 6-14x | Critical | Page on-call, begin incident response |
| > 14x | Emergency | Full incident response, consider kill switches |

**Example:** A burn rate of 6x for API availability means at the current error rate, the quarterly error budget will be exhausted in ~5 days instead of 90 days.

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
|   |   |       pytest path/to/test.py -v -s
|   |   |-- NO  → Continue...
|   |
|   |-- Is the database migrated?
|   |   |-- Run: make migrate
|   |   |-- Verify: alembic current
|   |
|   +-- Check test fixtures and dependencies:
|       pytest --fixtures | grep your_fixture
|
|-- INTERMITTENT
    |
    |-- Is it timing-related?
    |   |-- YES → Increase timeouts in test config
    |   |       Or use pytest-rerunfailures: pytest --reruns 3
    |   |-- NO  → Continue...
    |
    |-- Is it database-related?
    |   |-- YES → Check connection pool settings
    |   |       Ensure test database isolation
    |   |-- NO  → Continue...
    |
    +-- Check flakiness tracker:
        make flakiness-report
        # Or view: https://ci.fabric4l.io/flakiness
```

### "I can't connect to the database"

```
Is the database container running?
|
|-- NO
|   |-- docker ps | grep fabric4l-db
|   |-- docker logs fabric4l-db
|   |-- docker compose -f infra/compose/docker-compose.dev.yml up -d fabric4l-db
|
|-- YES
    |
    |-- Can you connect locally?
    |   |-- docker exec -it fabric4l-db pg_isready -U fabric4l
    |   |-- If "refused": Wait 10s, PostgreSQL may still be starting
    |   |-- If "no response": Check logs for errors
    |
    |-- Are migrations applied?
    |   |-- make migrate
    |   |-- alembic current
    |
    |-- Is the connection string correct?
    |   |-- cat .env.dev | grep DATABASE_URL
    |   |-- Format: postgresql://user:pass@host:port/db
    |
    |-- Is the port accessible?
    |   |-- telnet localhost 5432
    |   |-- If "connection refused": Check docker port mapping
    |
    +-- Try resetting:
        docker compose -f infra/compose/docker-compose.dev.yml down -v fabric4l-db
        make infra-up
        make migrate
```

### "Agent workflows are failing"

```
What is the failure symptom?
|
|-- Workflows stuck in "queued" state
|   |
|   |-- Is the worker running?
|   |   |-- docker ps | grep fabric4l-worker
|   |   |-- docker logs fabric4l-worker
|   |
|   |-- Is Redis accessible?
|   |   |-- docker exec -it fabric4l-redis redis-cli ping
|   |   |-- Should return: PONG
|   |
|   +-- Check queue depth:
|       docker exec -it fabric4l-redis redis-cli LLEN celery
|       # If > 100: Workers may be overwhelmed, scale up
|
|-- Workflows failing immediately (status: "failed")
|   |
|   |-- Check workflow logs:
|   |   docker logs fabric4l-worker 2>&1 | grep <workflow_id>
|   |
|   |-- Is the API key valid?
|   |   curl http://localhost:8001/api/v1/tenants/current \
|   |     -H "Authorization: Bearer $API_KEY"
|   |
|   |-- Is the feature flag enabled?
|   |   curl http://localhost:8001/api/v1/features/<flag> \
|   |     -H "Authorization: Bearer $API_KEY"
|   |
|   +-- Check for tool registry errors:
|       curl http://localhost:8001/api/v1/admin/contracts \
|   |     -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.violations'
|
|-- Workflows completing but with empty results
    |
    |-- Was the document successfully extracted?
    |   curl http://localhost:8001/api/v1/ingestion/documents/<doc_id> \
    |     -H "Authorization: Bearer $API_KEY" | jq '.extraction_status'
    |
    |-- Is the knowledge graph populated?
    |   curl http://localhost:8003/api/v1/knowledge/graph \
    |     -H "Authorization: Bearer $API_KEY" | jq '.graph.nodes | length'
    |
    +-- Try with a simpler query to rule out query complexity:
        Change inputs.query to something basic like "summarize"
```

### "Performance is degraded"

```
Which metric is degraded?
|
|-- High latency (P50/P95/P99)
|   |
|   |-- Check resource utilization:
|   |   docker stats --no-stream
|   |   # Look for CPU throttling or memory pressure
|   |
|   |-- Check database performance:
|   |   docker exec -it fabric4l-db psql -U fabric4l -c \
|   |     "SELECT query, mean_exec_time FROM pg_stat_statements \
|   |      ORDER BY mean_exec_time DESC LIMIT 10;"
|   |
|   |-- Enable query logging temporarily:
|   |   docker exec -it fabric4l-db psql -U fabric4l -c \
|   |     "ALTER SYSTEM SET log_min_duration_statement = '100'; \
|   |      SELECT pg_reload_conf();"
|   |
|   +-- Check for N+1 queries:
|       # Look for repeated similar queries in logs
|       docker logs fabric4l-api | grep "SELECT" | sort | uniq -c | sort -rn | head
|
|-- High error rate
|   |
|   |-- Check error logs:
|   |   docker logs fabric4l-api 2>&1 | grep ERROR
|   |
|   |-- Check recent deployments:
|   |   kubectl rollout history deployment/fabric4l-api
|   |
|   |-- Check feature flags (recently enabled?):
|   |   curl http://localhost:8001/api/v1/features \
|   |     -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.flags[] | select(.enabled)'
|   |
|   +-- Consider kill switch:
|       curl -X POST http://localhost:8001/api/v1/killswitches/<feature>/activate \
|         -H "Authorization: Bearer $ADMIN_TOKEN"
|
|-- Low throughput
    |
    |-- Check worker scaling:
    |   docker ps | grep fabric4l-worker
    |   # Scale if needed: docker compose up -d --scale worker=5
    |
    |-- Check queue backlog:
    |   docker exec -it fabric4l-redis redis-cli LLEN celery
    |
    |-- Check database connection pool:
    |   docker exec -it fabric4l-db psql -U fabric4l -c \
    |     "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
    |
    +-- Check for resource contention:
        # Are other services consuming shared resources?
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

---

## Quick Command Reference

| Task | Command |
|------|---------|
| Check health | `curl http://localhost:8001/api/v1/health/detailed \| jq` |
| View logs | `docker logs fabric4l-api --tail 100 -f` |
| Run migrations | `make migrate` |
| Run tests | `make test` |
| Scale workers | `docker compose up -d --scale worker=5` |
| Reset environment | `make clean && make setup` |
| Check SLOs | `curl /api/v1/slos -H "Authorization: Bearer $ADMIN_TOKEN" \| jq` |
| View contracts | `curl /api/v1/admin/contracts -H "Authorization: Bearer $ADMIN_TOKEN" \| jq` |
| List feature flags | `curl /api/v1/features -H "Authorization: Bearer $API_KEY" \| jq` |
| Activate kill switch | `curl -X POST /api/v1/killswitches/<key>/activate` |
| Export audit log | `curl /api/v1/admin/audit-log/export -d '{"format":"json"}'` |
| GDPR data export | `curl -X POST /api/v1/gdpr/data-export -d '{"subject_id":"..."}'` |
| Run chaos experiment | `curl -X POST /api/v1/chaos/experiments -d '{"type":"latency","target":"api"}'` |

---

## Version Information

- **Documentation Version:** v1.2.0
- **Last Updated:** 2026-07-14
- **Compatible Versions:** v1.2.0+
- **Maintainer:** Fabric 4L Documentation Team

For changes to this FAQ, submit a PR to [`docs/reference/faq.md`](https://github.com/bmsull560/Fabric_4L/blob/main/docs/reference/faq.md).
