---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Runbooks

This page contains step-by-step operational procedures for common scenarios
encountered when running the Value Fabric platform. Each runbook includes
prerequisites, exact commands, file paths, and validation steps.

## Database Backup and Restore

### Backup Strategy Overview

Value Fabric uses a dual-track backup strategy:

- **Active path**: `pg_dump` logical backups run daily at 02:00 UTC via the
  `postgres-backup` CronJob (`k8s/base/postgres-backup-cronjob.yaml`). Backups
  are stored on a 50Gi PVC and retained for 7 days.
- **Staged path**: WAL-G physical base backups to S3 are intentionally disabled
  (`ENABLE_WALG_BACKUP=false`) until restore drills are completed and evidence
  is captured.

### Databases Backed Up

All application databases are backed up: `ingestion`, `extraction`,
`signal_refinery`, `layer4_agents`, `ground_truth`, `benchmarks`.

### Verify Backup Exists

```bash
# List recent backup jobs
kubectl get cronjobs -n value-fabric postgres-backup
kubectl get jobs -n value-fabric | grep postgres-backup

# Check backup files inside the backup PVC pod
kubectl exec -n value-fabric deployment/postgres-backup -- ls -la /backups/postgres/

# Validate backup integrity (dry-run restore)
# Port-forward or exec into the backup pod and run:
pg_restore -l /backups/postgres/backup_layer4_agents_YYYYMMDD_HHMMSS.dump
```

### Restore from pg_dump Backup

!!! danger "Restore is destructive"
    Restoring a database overwrites current data. Coordinate with the team,
    snapshot the current PVC if possible, and perform the restore during a
    maintenance window.

```bash
# 1. Scale down the affected service to prevent writes
kubectl scale deployment/layer4-agents --replicas=0 -n value-fabric

# 2. Drop and recreate the target database
kubectl exec -n value-fabric deployment/postgres -- psql -U postgres -c "DROP DATABASE IF EXISTS layer4_agents;"
kubectl exec -n value-fabric deployment/postgres -- psql -U postgres -c "CREATE DATABASE layer4_agents;"

# 3. Restore from backup
kubectl cp /backups/postgres/backup_layer4_agents_YYYYMMDD_HHMMSS.dump \
  value-fabric/postgres-backup-xxx:/tmp/restore.dump

kubectl exec -n value-fabric deployment/postgres -- pg_restore \
  -U postgres -d layer4_agents --no-owner --no-privileges /tmp/restore.dump

# 4. Scale the service back up
kubectl scale deployment/layer4-agents --replicas=2 -n value-fabric

# 5. Verify health
kubectl port-forward -n value-fabric svc/layer4-agents 8004:8004
curl -fsS http://localhost:8004/health
```

### WAL-G Physical Backup (Staging Path)

Do not enable WAL-G until the enablement checklist in
`k8s/base/postgres-backup-cronjob.yaml` is complete. To verify readiness:

```bash
# Check WAL-G gate
pnpm ops:walg:gate

# Dry-run restore evidence
pnpm ops:restore:dry-run

# Validate backup/restore tests
pnpm ops:backup:verify
```

## Redis Cache Clearing

### When to Clear Cache

Clear Redis when tenant config is stale after flag changes, Celery task metadata
is corrupted, or memory pressure approaches `maxmemory`.

### Identify Keys by Pattern

```bash
# Local development
redis-cli -a ${REDIS_PASSWORD} --scan --pattern '*tenant:abc123*'
# Kubernetes
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} --scan --pattern '*celery-task-meta-*' | head -20
```

### Clear Specific Keys

```bash
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} eval \
  "local keys = redis.call('keys', ARGV[1]); for i=1,#keys do redis.call('del', keys[i]); end; return #keys;" \
  0 'celery-task-meta-*'
```

### Flush All Databases

!!! danger "Destructive operation"
    `FLUSHALL` removes every key in every Redis database. This will invalidate
    all caches, Celery broker state, and session data. Use only during a
    controlled maintenance window.

```bash
# In Kubernetes
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} FLUSHALL

# In local Docker Compose
docker compose -f docker-compose.dev.yml exec redis redis-cli -a ${REDIS_PASSWORD} FLUSHALL
```

### Verify Cache State After Clear

```bash
redis-cli -a ${REDIS_PASSWORD} info keyspace && redis-cli -a ${REDIS_PASSWORD} dbsize
```

## Queue Monitoring and Retry

### Celery Architecture

Layer 1 and Layer 2 run Celery workers backed by Redis:

- **Broker**: Redis (`CELERY_BROKER_URL`)
- **Result backend**: Redis (`CELERY_RESULT_BACKEND`)
- **Scheduler**: RedBeat (`redbeat.RedBeatScheduler`) for distributed cron
- **Monitoring**: Flower dashboard on port `5555`

### Monitor Queue Depth

```bash
# List Redis queues and lengths
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} llen celery
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} llen ingestion
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} llen processing
```

### Inspect Failed Tasks

```bash
# Using Flower (port-forward required)
kubectl port-forward -n value-fabric svc/flower 5555:5555
open http://localhost:5555

# Or query Redis directly for dead-letter inspection
kubectl exec -n value-fabric deployment/redis -- redis-cli -a ${REDIS_PASSWORD} keys '*celery-task-meta-*' | wc -l
```

### Retry Failed Tasks

```bash
# Retry via Flower UI, or programmatically:
kubectl exec -n value-fabric deployment/layer1-celery-worker -- \
  celery -A layer1_ingestion.shared.tasks call my_task.retry --kwargs='{"task_id": "abc-123"}'

# Purge all tasks from a queue (emergency only)
kubectl exec -n value-fabric deployment/layer1-celery-worker -- \
  celery -A layer1_ingestion.shared.tasks purge -f
```

### Restart Celery Workers

```bash
# Rolling restart of Layer 1 workers
kubectl rollout restart deployment/layer1-celery-worker -n value-fabric
kubectl rollout status deployment/layer1-celery-worker -n value-fabric

# Restart Layer 2 workers (sidecar in the layer2 Deployment)
kubectl rollout restart deployment/layer2-extraction -n value-fabric
```

## Service Restart Procedures

### Docker Compose (Local Development)

```bash
# Restart a single service
docker compose -f docker-compose.dev.yml restart layer4

# Restart all services
docker compose -f docker-compose.dev.yml restart

# Recreate with fresh env
docker compose -f docker-compose.dev.yml up -d --force-recreate layer4
```

### Kubernetes

```bash
# Rolling restart of a Deployment
kubectl rollout restart deployment/layer4-agents -n value-fabric
kubectl rollout status deployment/layer4-agents -n value-fabric

# Restart all application layers
for dep in layer1-ingestion layer2-extraction layer3-knowledge layer4-agents layer5-ground-truth layer6-benchmarks; do
  kubectl rollout restart deployment/$dep -n value-fabric
done

# Scale to zero and back (hard restart)
kubectl scale deployment/layer4-agents --replicas=0 -n value-fabric
sleep 10
kubectl scale deployment/layer4-agents --replicas=2 -n value-fabric
```

### Frontend Only

```bash
# Local dev server
pnpm dev:web

# Docker Compose
docker compose -f docker-compose.dev.yml restart frontend

# Kubernetes
kubectl rollout restart deployment/frontend -n value-fabric
```

## Tenant Isolation Verification

### Automated Gates

Run the canonical tenant isolation test suites before any production deployment
or after an incident involving data access:

```bash
# Full tenant isolation suite
make gate-tenant-isolation

# Hostile tenant security contracts
pnpm test:security:hostile

# Tenant boundary pytest markers
pytest -m tenant_boundary -v --tb=short
```

### Manual Verification Steps

```bash
# 1. Create two test tenants (or use existing E2E tenants)
TENANT_A=00000000-0000-4000-e2e0-000000000001
TENANT_B=00000000-0000-4000-e2e0-000000000002

# 2. Write data as Tenant A
curl -X POST http://localhost:8004/api/v1/agents/workflows \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "X-Tenant-ID: $TENANT_A" \
  -d '{"name": "isolation-test-a"}'

# 3. Attempt to read as Tenant B (must fail with 403)
curl -X GET http://localhost:8004/api/v1/agents/workflows \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "X-Tenant-ID: $TENANT_B"
# Expected: 403 Forbidden or empty scoped result

# 4. Verify database query scoping
kubectl exec -n value-fabric deployment/postgres -- psql -U postgres -d layer4_agents -c \
  "SELECT tenant_id, count(*) FROM workflows GROUP BY tenant_id;"
```

## Log Investigation Steps

### Loki (Preferred)

Use Grafana's Explore view with Loki data source:

```text
# All errors for a service
{namespace="value-fabric", app="layer4-agents"} |= "ERROR"

# Tenant-scoped errors
{namespace="value-fabric", app="layer4-agents"} |= "tenant_id=00000000-0000-4000-e2e0-000000000001" |= "ERROR"

# Slow queries in Layer 3
{namespace="value-fabric", app="layer3-knowledge"} |= "slow query"

# Auth failures across all layers
{namespace="value-fabric"} |= "401" or {namespace="value-fabric"} |= "403"
```

### kubectl Logs

```bash
# Follow logs for a deployment
kubectl logs -n value-fabric deployment/layer4-agents --tail=500 -f

# Previous container logs (after crash/restart)
kubectl logs -n value-fabric deployment/layer4-agents --previous

# All pods for a service
kubectl logs -n value-fabric -l app=layer4-agents --tail=100

# Logs since a specific time
kubectl logs -n value-fabric deployment/layer4-agents --since=30m
```

### Structured Log Fields

All backend services emit JSON-structured logs with these standard fields:

| Field | Description | Example Filter |
|---|---|---|
| `timestamp` | ISO-8601 with timezone | — |
| `level` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `level="ERROR"` |
| `logger` | Python logger name | `logger="layer4_agents.api.routes"` |
| `tenant_id` | Authenticated tenant context | `tenant_id="..."` |
| `request_id` | Correlation ID from `X-Request-ID` | `request_id="abc-123"` |
| `user_id` | Authenticated user ID | `user_id="..."` |
| `path` | HTTP path or operation name | `path="/api/v1/agents/workflows"` |
| `latency_ms` | Request duration in milliseconds | `latency_ms > 5000` |
| `status_code` | HTTP response status | `status_code=500` |

## Keycloak User and Tenant Management

### Local Development Keycloak

Local development uses Keycloak at `http://localhost:8080` with the `fabric` realm.

```bash
# Admin credentials (dev only)
Username: admin
Password: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
```

### Manage Realm Roles and Users

```bash
# Obtain admin token
TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=${KEYCLOAK_ADMIN_PASSWORD}&grant_type=password&client_id=admin-cli" \
  | jq -r '.access_token')

# Create role
curl -X POST http://localhost:8080/admin/realms/fabric/roles \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "analyst", "description": "Read-only analyst role"}'

# Create user with tenant attribute
curl -X POST http://localhost:8080/admin/realms/fabric/users \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username":"new.user@example.com","email":"new.user@example.com","enabled":true,"emailVerified":true,"attributes":{"tenant_id":["00000000-0000-4000-8000-000000000001"]}}'

# Verify tenant_id claim in issued token
curl -s -X POST http://localhost:8080/realms/fabric/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=new.user@example.com&password=${DEV_SEED_ADMIN_PASSWORD}&grant_type=password&client_id=fabric-api" \
  | jq -r '.access_token' | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.tenant_id'
```

### Production: Clerk IdP

Production uses **Clerk** as the primary identity provider. Keycloak is not used
in production. For Clerk user and organization management:

- Use the Clerk Dashboard at `https://dashboard.clerk.com`.
- Backend verification uses `CLERK_JWKS_URL` and `CLERK_JWT_AUDIENCE`.
- Tenant mapping is derived from Clerk Organizations.

!!! warning "Do not mix Keycloak and Clerk in production"
    Production services must never fall back to Keycloak if Clerk is configured.
    Verify via `AUTH_REQUIRED=true` and `VITE_AUTH_PROVIDER=clerk`.

## Validation

Run operational validation tests after executing any runbook:

```bash
# Backup/restore readiness
make gate-backup-restore-readiness
pnpm ops:backup:verify

# Restore dry-run evidence
pnpm ops:restore:dry-run

# Security and tenant isolation
make gate-security
pnpm test:security

# Full platform verification
make verify
```
