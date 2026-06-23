---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Monitoring

This page documents the observability stack for the Value Fabric platform,
including health checks, log aggregation, metrics collection, alerting thresholds,
dashboard recommendations, and infrastructure-specific monitoring for Neo4j,
PostgreSQL, Redis, and Keycloak.

## Health Checks per Service

Every service exposes structured health, readiness, and liveness endpoints.
Kubernetes uses these for probes; operators use them for quick operational checks.

| Service | Liveness | Readiness | Metrics | Port |
|---|---|---|---|---|
| Layer 1 Ingestion | `/health/live` | `/ready` | `/api/v1/ingestion/metrics` | 8000 |
| Layer 2 Extraction | `/health` | `/health` | `/metrics` | 8000 |
| Layer 3 Knowledge | `/health` | `/health` | `/metrics` | 8001 |
| Layer 4 Agents | `/health` | `/health` | `/metrics` | 8000 |
| Layer 5 Ground Truth | `/health` | `/api/v1/health` | `/metrics` | 8005 |
| Layer 6 Benchmarks | `/health` | `/health` | `/metrics` | 8006 |
| API Gateway | `/health` | `/health` | `/metrics` | 8000 |
| Frontend | `/` | `/` | — | 3001 |

!!! note "Kubernetes probe configuration"
    Liveness probes use `failureThreshold: 3`, `periodSeconds: 30`, and an
    `initialDelaySeconds` appropriate to the service (typically 60s for Python
    services). Readiness probes use `periodSeconds: 10` so traffic is cut quickly
    when dependencies fail.

### Quick Health Verification

```bash
# Local development
curl -fsS http://localhost:8001/api/v1/ingestion/health
curl -fsS http://localhost:8002/health
curl -fsS http://localhost:8004/health

# Kubernetes (port-forward)
kubectl port-forward -n value-fabric svc/layer4-agents 8004:8004
curl -fsS http://localhost:8004/health
```

## Log Aggregation

Value Fabric uses **Fluent Bit** for log shipping and **Loki** for log storage
and querying. Grafana provides the primary search interface.

### Fluent Bit Configuration

Fluent Bit is configured in `monitoring/fluent-bit/fluent-bit.conf`:

- **Inputs**: `tail` for host logs (`/var/log/*.log`), Docker container logs
  (`/var/lib/docker/containers/*/*.log`), Kubernetes containerd logs
  (`/var/log/containers/*.log`), and a `forward` listener on port `24224` for
  direct application shipping.
- **Filter**: Adds `cluster=local` and `namespace=value-fabric` labels to every
  record.
- **Output**: Forwards all logs to Loki at `loki:3100` with JSON line format.

### Loki Configuration

Loki is configured in `monitoring/loki/local-config.yaml`:

- **Retention**: Hot retention is **30 days** (`retention_period: 720h`).
  Logs older than 30 days are deleted from primary storage.
- **Cold archival**: For retention beyond 30 days (up to 1 year), ship logs to
  object storage (S3/GCS) via the compactor or a Fluentd/Fluent-Bit S3 sink.
- **Ingestion limits**: `ingestion_rate_mb: 64`, `ingestion_burst_size_mb: 128`.
- **Query**: `http_listen_port: 3100`, `grpc_listen_port: 9096`.

!!! warning "Log retention compliance"
    Do not increase hot retention beyond 30 days without updating the
    log-retention policy in `monitoring/docs/log-retention-policy.md` and
    verifying compliance sign-off.

### Investigating Logs

```bash
# Via kubectl (Kubernetes)
kubectl logs -n value-fabric deployment/layer4-agents --tail=500 -f

# Via Loki (Grafana)
# Query example: {namespace="value-fabric", app="layer4-agents"} |= "ERROR"

# Via Docker Compose (local)
docker compose -f docker-compose.dev.yml logs -f layer4
```

## Metrics Collection Points

### Prometheus Scraping

Prometheus is configured in `monitoring/prometheus/prometheus.yml` with a
`scrape_interval: 15s` and `evaluation_interval: 15s`.

Scrape targets:

| Job Name | Target | Metrics Path | Timeout |
|---|---|---|---|
| `prometheus` | `localhost:9090` | `/metrics` | 15s |
| `layer1-ingestion` | `layer1-ingestion:8000` | `/api/v1/ingestion/metrics` | 10s |
| `layer2-extraction` | `layer2-extraction:8000` | `/metrics` | 10s |
| `layer3-knowledge` | `layer3-knowledge:8001` | `/metrics` | 10s |
| `layer4-agents` | `layer4-agents:8000` | `/metrics` | 10s |
| `layer5-ground-truth` | `layer5-ground-truth:8005` | `/metrics` | 10s |
| `layer6-benchmarks` | `layer6-benchmarks:8006` | `/metrics` | 10s |

### Key Metric Categories

| Category | Examples | Use Case |
|---|---|---|
| HTTP request latency | `http_request_duration_seconds` | SLO tracking, latency regression |
| Error rates | `http_requests_total{status=~"5.."}` | Alerting on elevated failure rates |
| Database connections | `db_pool_size`, `db_overflow` | Connection exhaustion detection |
| Redis operations | `redis_command_duration_seconds` | Cache slowdown identification |
| Celery task metrics | `celery_task_total`, `celery_task_failed_total` | Queue health and worker backpressure |
| LLM cost tracking | `llm_request_total`, `llm_tokens_total` | FinOps visibility, cost anomaly detection |
| Tenant-scoped metrics | `requests_total{tenant_id="..."}` | Per-tenant usage and isolation verification |

## Alerting Thresholds

### Alertmanager Routing

Alertmanager (`monitoring/alertmanager/alertmanager.yml`) routes alerts by
severity and alert name:

| Severity | Primary Receiver | Secondary | Repeat Interval |
|---|---|---|---|
| `critical` | PagerDuty (`pagerduty-critical`) | Slack `#vf-alerts-critical` | 15m |
| `warning` | Slack `#vf-alerts-warning` | — | 2h |
| `info` | Slack `#vf-alerts-info` | — | 24h |
| `HighLLMCostRate` | Slack `#vf-finops-alerts` | — | 1h |
| `HighLLMCostCritical` | PagerDuty (`pagerduty-critical`) | — | 10m |
| `WebSocketCrossTenantProbeCritical` | PagerDuty + `#vf-security-alerts` | — | 10m |
| `FormulaApprovalRequired` | Slack `#vf-formula-approvals` | — | 30m |

### Inhibition Rules

- Critical alerts silence warnings of the same `alertname` and `namespace`.
- `ServiceDown` silences all dependent component alerts in the same namespace.
- `HighErrorRate` silences individual error alerts in the same namespace.

### Layer-Specific Alert Files

| File | Scope |
|---|---|
| `monitoring/layer1-alerts.yml` | Ingestion queue depth, crawler failure rate |
| `monitoring/layer2-alerts.yml` | Extraction latency, LLM provider errors |
| `monitoring/layer4-alert-rules.yaml` | Agent workflow failure, checkpoint lag, LLM cost |
| `monitoring/alerting/rules-production.yml` | Platform-wide SLO burn-rate alerts |
| `monitoring/alerting/layer-sli-rules-production.yml` | Per-layer SLI evaluation rules |

## Dashboard Recommendations

Grafana dashboards are provisioned from `monitoring/grafana/dashboards/`:

| Dashboard | File | Purpose |
|---|---|---|
| Value Fabric Overview | `value-fabric-overview.json` | Platform health at a glance |
| Value Fabric Operational | `value-fabric-operational.json` | Detailed operational metrics |
| SLO Detailed | `slo-detailed.json` | Service-level objective tracking |
| SLO Error Budget Burn Rate | `slo-error-budget-burn-rate.json` | Burn-rate alerting visualization |
| Frontend Performance | `frontend-performance.json` | Web vitals, bundle size, API latency |
| Layer 1 Ingestion | `layer1-ingestion.json` | Crawler throughput, queue depth |
| Layer 2 Extraction | `layer2-extraction.json` | Extraction throughput, model latency |
| Layer 3 Knowledge | `layer3-knowledge.json` | Graph query performance, retrieval latency |
| Layer 4 Agents | `layer4-agents.json` | Workflow state, checkpoint health, LLM cost |
| Layer 5 Ground Truth | `layer5-ground-truth.json` | Validation queue, maturity ladder progress |
| Layer 6 Benchmarks | `layer6-benchmarks.json` | Benchmark execution, statistical drift |
| Neo4j Performance | `neo4j-performance.json` | Query latency, heap usage, transaction rates |
| Redis Performance | `redis-performance.json` | Memory usage, hit rate, eviction rates |
| DB Connection Pool | `db-connection-pool.json` | Pool saturation, overflow, wait times |
| Rate Limiting | `rate-limiting-observability.json` | Per-tenant and global rate-limit hits |
| LLM Costs | `llm-costs.json` | Token usage, cost per model, per tenant |
| Business KPIs | `business-kpis.json` | Revenue-aligned platform metrics |
| Journey Launch SLOs | `journey-launch-slos.json` | Golden-path journey latency and reliability |
| Billing Revenue | `billing-revenue.json` | Subscription and usage revenue tracking |

!!! note "Dashboard provisioning"
    Dashboards are auto-provisioned via `monitoring/grafana/provisioning/dashboards/value-fabric.yml`.
    Data sources are configured in `monitoring/grafana/provisioning/datasources/`.

## Neo4j Monitoring

Neo4j exposes metrics via JMX and the Browser interface:

- **Browser**: `http://localhost:7474` (local) or via port-forward in Kubernetes.
- **Query performance**: Monitor `dbms.queryJmx` and slow query logs.
- **APOC plugin**: Verify plugin load in logs; APOC is required for several
  Layer 3 graph procedures.
- **Heap and GC**: Watch for GC pressure in clusters with large graph traversals.

```bash
# Port-forward Neo4j Browser
kubectl port-forward -n value-fabric svc/neo4j 7474:7474

# Check Neo4j status via Cypher
curl -u neo4j:devpassword http://localhost:7474/dbms/health
```

## PostgreSQL Monitoring

PostgreSQL is monitored through several lenses:

- **pgAudit**: Audit logging is enabled via `postgresql.conf` mounted from
  `k8s/base/postgresql.conf`. Logs are shipped to Loki by Fluent Bit.
- **PgBouncer**: Connection pool metrics are exposed via `SHOW stats` and
  Prometheus-compatible exporters where deployed.
- **Connection pool**: Each service layer manages its own SQLAlchemy async pool.
  Tune `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and `DB_POOL_TIMEOUT` via environment
  variables.
- **Patroni**: High-availability PostgreSQL uses the Patroni manifest
  (`k8s/base/postgres-patroni.yaml`). Monitor leader election and replication
  lag via Patroni REST API.

```bash
# Check PostgreSQL readiness
kubectl exec -n value-fabric deployment/postgres -- pg_isready -U postgres

# Check active connections
kubectl exec -n value-fabric deployment/postgres -- psql -U postgres -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

## Redis Monitoring

Redis is the Celery broker, result backend, and cache for all layers.

- **Memory**: Watch `used_memory` and `maxmemory`. Eviction policy should be
  `allkeys-lru` or `volatile-lru` depending on deployment.
- **Hit rate**: Monitor `keyspace_hits` vs `keyspace_misses`.
- **Connections**: Track `connected_clients` against the configured maximum.
- **Celery backend**: Monitor `celery-task-meta-*` key explosion under high
  task volume; set result expiry appropriately.

```bash
# Local Redis checks
redis-cli -a ${REDIS_PASSWORD} info memory
redis-cli -a ${REDIS_PASSWORD} info stats
redis-cli -a ${REDIS_PASSWORD} --bigkeys

# Kubernetes
kubectl exec -n value-fabric deployment/redis -- redis-cli info memory
```

## Keycloak Monitoring

Keycloak exposes health and metrics endpoints:

- **Health**: `http://keycloak:8080/health/ready` (readiness) and
  `/health/live` (liveness).
- **Metrics**: Keycloak 25.x exposes Micrometer metrics on `/metrics` when
  enabled. In dev, the metrics endpoint is available but may require
  `metrics-enabled=true` in the realm configuration for production.
- **Realm events**: Login errors, token refresh failures, and brute-force
  detection events are logged and should be alerted in production.

```bash
# Check Keycloak health
kubectl exec -n value-fabric deployment/keycloak -- curl -fsS http://localhost:8080/health/ready

# Check realm events (admin CLI)
kubectl exec -n value-fabric deployment/keycloak -- /opt/keycloak/bin/kc.sh admin-cli.sh get events -r fabric
```

## Validation

Run observability-specific tests to validate the monitoring pipeline:

```bash
# Observability tests
pnpm run test:observability

# Alertmanager configuration validation
pnpm ops:incident:check

# SLO and alerting rule validation
python -m pytest tests/observability/ -v --tb=short

# Log retention policy verification
python -m pytest tests/data_lifecycle/ -v --tb=short
```
