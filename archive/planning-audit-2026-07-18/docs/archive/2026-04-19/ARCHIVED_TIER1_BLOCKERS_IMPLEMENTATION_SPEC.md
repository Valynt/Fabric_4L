# Tier 1 Production Blockers - Implementation Specification

> ⚠️ **ARCHIVED CONTENT** (Date: 2026-04-19)
> This document records superseded implementation plans. All blockers are resolved. See [ROADMAP.md](../../ROADMAP.md) and the [Archive Registry](../archive-registry.md).

**Date:** April 17, 2026
**Status:** Ready for Execution
**Order:** (1) Vault Integration → (2) L1 Celery/Redis → (3) Monitoring Tuning

---

## BLOCKER 1: Vault Integration Completion

### Current State
- ✅ External Secrets Operator manifests exist
- ✅ ExternalSecret CRDs defined for all 6 layers
- ⚠️ Vault backend not configured
- ⚠️ No ClusterSecretStore pointing to actual Vault
- ⚠️ Kubernetes auth method not configured in Vault

### Target State
External Secrets Operator syncs secrets from HashiCorp Vault to Kubernetes Secrets automatically. All pods receive secrets via environment variables from synced Kubernetes Secrets.

---

### Implementation Steps

#### Step 1.1: Deploy Vault (if not deployed)

**Files to Create:**
- `k8s/vault/vault-deployment.yaml`

```yaml
# Vault Deployment for Development/Testing
# For production, use Helm chart: helm install vault hashicorp/vault
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vault
  namespace: vault
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vault
  template:
    metadata:
      labels:
        app: vault
    spec:
      containers:
      - name: vault
        image: hashicorp/vault:1.15.0
        ports:
        - containerPort: 8200
        env:
        - name: VAULT_DEV_ROOT_TOKEN_ID
          value: "dev-root-token"  # CHANGE IN PRODUCTION
        - name: VAULT_DEV_LISTEN_ADDRESS
          value: "0.0.0.0:8200"
```

**Commands:**
```bash
# Create vault namespace
kubectl create namespace vault

# Deploy Vault
kubectl apply -f k8s/vault/vault-deployment.yaml

# Expose Vault (for dev)
kubectl port-forward -n vault deployment/vault 8200:8200 &

# Verify Vault is running
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='dev-root-token'
vault status
```

**Validation:**
- [ ] Vault pod running: `kubectl get pods -n vault`
- [ ] Vault responsive: `vault status` returns "Sealed: false"

---

#### Step 1.2: Enable Kubernetes Auth in Vault

**Commands:**
```bash
# Set Vault environment
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='dev-root-token'

# Enable Kubernetes auth method
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
  kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create policy for reading secrets
cat > /tmp/fabric-policy.hcl << 'EOF'
path "secret/data/fabric/*" {
  capabilities = ["read"]
}
path "secret/data/ci/*" {
  capabilities = ["read"]
}
EOF

vault policy write fabric-policy /tmp/fabric-policy.hcl

# Create Kubernetes auth role
vault write auth/kubernetes/role/fabric-eso \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=fabric-policy \
  ttl=1h
```

**Validation:**
- [ ] Kubernetes auth enabled: `vault auth list | grep kubernetes`
- [ ] Policy created: `vault policy read fabric-policy`
- [ ] Role created: `vault read auth/kubernetes/role/fabric-eso`

---

#### Step 1.3: Store Secrets in Vault

**Commands:**
```bash
# Enable KV secrets engine
vault secrets enable -path=secret kv-v2

# Store Layer 1 secrets
vault kv put secret/fabric/layer1 \
  database_url="postgresql://layer1:password@postgres:5432/layer1_db" \
  redis_url="redis://redis:6379/0" \
  jwt_secret="dev-jwt-secret-change-in-production"

# Store Layer 2 secrets
vault kv put secret/fabric/layer2 \
  openai_api_key="sk-..." \
  redis_url="redis://redis:6379/1"

# Store Layer 3 secrets
vault kv put secret/fabric/layer3 \
  neo4j_url="bolt://neo4j:7687" \
  neo4j_user="neo4j" \
  neo4j_password="password"

# Store Layer 4 secrets
vault kv put secret/fabric/layer4 \
  database_url="postgresql://layer4:password@postgres:5432/layer4_db" \
  redis_url="redis://redis:6379/2" \
  openai_api_key="sk-..."

# Verify secrets
vault kv get secret/fabric/layer1
vault kv get secret/fabric/layer2
vault kv get secret/fabric/layer3
vault kv get secret/fabric/layer4
```

**Validation:**
- [ ] All secrets stored: `vault kv list secret/fabric/`
- [ ] Can retrieve each secret: `vault kv get secret/fabric/layer{N}`

---

#### Step 1.4: Update ClusterSecretStore

**File to Modify:**
- `k8s/external-secrets/cluster-secret-store.yaml`

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "http://vault.vault.svc.cluster.local:8200"  # Update with actual Vault URL
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "fabric-eso"
          serviceAccountRef:
            name: external-secrets
            namespace: external-secrets
```

**Commands:**
```bash
# Apply updated ClusterSecretStore
kubectl apply -f k8s/external-secrets/cluster-secret-store.yaml

# Verify ClusterSecretStore is ready
kubectl get ClusterSecretStore vault-backend
# Should show: Status: Ready
```

**Validation:**
- [ ] ClusterSecretStore status: `kubectl get ClusterSecretStore vault-backend -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` returns "True"

---

#### Step 1.5: Update ExternalSecret Resources

**Files to Modify:**
For each layer, update `k8s/external-secrets/layer{N}-secrets.yaml`:

Example for Layer 1 (`k8s/external-secrets/layer1-secrets.yaml`):
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: layer1-secrets
  namespace: value-fabric
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: vault-backend  # Use the ClusterSecretStore
    kind: ClusterSecretStore
  target:
    name: layer1-secrets
    creationPolicy: Owner
  data:
  - secretKey: DATABASE_URL
    remoteRef:
      key: secret/fabric/layer1
      property: database_url
  - secretKey: REDIS_URL
    remoteRef:
      key: secret/fabric/layer1
      property: redis_url
  - secretKey: JWT_SECRET
    remoteRef:
      key: secret/fabric/layer1
      property: jwt_secret
```

**Commands:**
```bash
# Apply all ExternalSecrets
kubectl apply -f k8s/external-secrets/layer1-secrets.yaml
kubectl apply -f k8s/external-secrets/layer2-secrets.yaml
kubectl apply -f k8s/external-secrets/layer3-secrets.yaml
kubectl apply -f k8s/external-secrets/layer4-secrets.yaml
kubectl apply -f k8s/external-secrets/layer5-secrets.yaml
kubectl apply -f k8s/external-secrets/layer6-secrets.yaml

# Verify secrets are synced
kubectl get externalsecret -n value-fabric
kubectl get secrets -n value-fabric | grep layer
```

**Validation:**
- [ ] All ExternalSecrets show "Ready": `kubectl get externalsecret -n value-fabric`
- [ ] Kubernetes Secrets created: `kubectl get secrets -n value-fabric`
- [ ] Secrets contain data: `kubectl get secret layer1-secrets -n value-fabric -o jsonpath='{.data.DATABASE_URL}' | base64 -d`

---

#### Step 1.6: Update Deployments to Use Secrets

**Files to Modify:**
For each layer deployment, add environment variables from secrets:

Example for Layer 1 (`k8s/base/layer1-ingestion.yml`):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: layer1-ingestion
spec:
  template:
    spec:
      containers:
      - name: layer1
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: REDIS_URL
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: JWT_SECRET
```

**Commands:**
```bash
# Apply updated deployments
kubectl apply -k k8s/base/

# Verify pods are running with secrets
kubectl get pods -n value-fabric
kubectl describe pod <layer1-pod> -n value-fabric | grep -A 5 "Environment"
```

**Validation:**
- [ ] Pods start successfully
- [ ] Environment variables injected: `kubectl exec <pod> -- env | grep DATABASE_URL`

---

### Rollback Procedure

If Vault integration fails:

```bash
# 1. Revert to static secrets
kubectl apply -f k8s/base/secrets-static/  # Use original SecretKeyRef approach

# 2. Delete ExternalSecrets
kubectl delete externalsecret -n value-fabric --all

# 3. Delete ClusterSecretStore
kubectl delete clustersecretstore vault-backend

# 4. Scale deployments back up
kubectl rollout restart deployment -n value-fabric
```

---

### Acceptance Criteria

- [ ] All secrets stored in Vault, not in Git
- [ ] External Secrets Operator syncing secrets to Kubernetes
- [ ] All pods receive secrets via environment variables
- [ ] Secret rotation works (change in Vault → reflected in pods within 1 hour)
- [ ] No secrets in logs or error messages
- [ ] Documentation updated: `docs/operations/VAULT_SETUP.md`

---

## BLOCKER 2: L1 Celery/Redis Full Orchestration

### Current State
- ✅ Celery configuration exists (`layer1-ingestion/src/shared/tasks.py`)
- ✅ Redis configured for caching
- ⚠️ No Celery worker service in docker-compose.yml
- ⚠️ No Kubernetes Deployment for Celery workers
- ⚠️ No task result backend configured
- ⚠️ No Flower UI for monitoring

### Target State
Layer 1 uses Celery with Redis for async task processing. Celery workers scale independently. Flower provides monitoring UI.

---

### Implementation Steps

#### Step 2.1: Update Celery Configuration

**File to Modify:**
- `services/layer1-ingestion/src/shared/tasks.py`

```python
from celery import Celery
from celery.signals import task_failure, task_success
import os

# Create Celery app
celery_app = Celery(
    'layer1',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    include=['layer1_ingestion.src.shared.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour timeout
    worker_prefetch_multiplier=1,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Task failure handler
@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Log task failures for monitoring"""
    print(f"Task {task_id} failed: {exception}")

# Task success handler
@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Log task completion for monitoring"""
    print(f"Task {sender.name} completed successfully")
```

**Validation:**
- [ ] Celery app imports without errors
- [ ] Configuration includes result backend

---

#### Step 2.2: Create Celery Tasks

**File to Create:**
- `services/layer1-ingestion/src/crawler/celery_tasks.py`

```python
from layer1_ingestion.src.shared.tasks import celery_app
from layer1_ingestion.src.crawler.ingestion import IngestionEngine
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_url_task(self, url: str, tenant_id: str, source_type: str = "web"):
    """
    Celery task to crawl a URL and ingest content.

    Args:
        url: URL to crawl
        tenant_id: Tenant identifier for isolation
        source_type: Type of source (web, pdf, sec)

    Returns:
        dict: Ingestion result with document_id
    """
    try:
        engine = IngestionEngine(tenant_id=tenant_id)
        result = engine.ingest_url(url, source_type=source_type)

        logger.info(f"Successfully ingested {url} for tenant {tenant_id}")
        return {
            "status": "success",
            "url": url,
            "document_id": result.document_id,
            "tenant_id": tenant_id
        }
    except Exception as exc:
        logger.error(f"Failed to ingest {url}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task(bind=True, max_retries=3)
def process_document_task(self, document_id: str, tenant_id: str):
    """
    Process an already ingested document (extract, parse, store).

    Args:
        document_id: Document identifier
        tenant_id: Tenant identifier

    Returns:
        dict: Processing result
    """
    try:
        engine = IngestionEngine(tenant_id=tenant_id)
        result = engine.process_document(document_id)

        logger.info(f"Successfully processed document {document_id}")
        return {
            "status": "success",
            "document_id": document_id,
            "extracted_entities": len(result.entities)
        }
    except Exception as exc:
        logger.error(f"Failed to process document {document_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task
def cleanup_old_documents_task(days: int = 30):
    """Scheduled task to clean up old documents"""
    from layer1_ingestion.src.shared.models import Document
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)
    old_docs = Document.query.filter(Document.created_at < cutoff).all()

    count = 0
    for doc in old_docs:
        doc.delete()
        count += 1

    logger.info(f"Cleaned up {count} old documents")
    return {"cleaned": count}
```

**Validation:**
- [ ] Tasks import without errors
- [ ] Task signatures correct

---

#### Step 2.3: Add Celery Worker to Docker Compose

**File to Modify:**
- `docker-compose.full.yml`

```yaml
version: '3.8'

services:
  # Existing services...

  # Celery Worker for Layer 1
  layer1-worker:
    build:
      context: ./layer1-ingestion
      dockerfile: Dockerfile
    command: celery -A layer1_ingestion.src.shared.tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://layer1:password@postgres:5432/layer1_db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - PYTHONPATH=/app
    depends_on:
      - postgres
      - redis
    volumes:
      - ./layer1-ingestion:/app
    networks:
      - fabric-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "celery", "-A", "layer1_ingestion.src.shared.tasks", "inspect", "--timeout", "5"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Beat for Scheduled Tasks
  layer1-beat:
    build:
      context: ./layer1-ingestion
      dockerfile: Dockerfile
    command: celery -A layer1_ingestion.src.shared.tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://layer1:password@postgres:5432/layer1_db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - PYTHONPATH=/app
    depends_on:
      - postgres
      - redis
      - layer1-worker
    volumes:
      - ./layer1-ingestion:/app
    networks:
      - fabric-network
    restart: unless-stopped

  # Flower - Celery Monitoring UI
  flower:
    build:
      context: ./layer1-ingestion
      dockerfile: Dockerfile
    command: celery -A layer1_ingestion.src.shared.tasks flower --port=5555 --url_prefix=/flower
    environment:
      - DATABASE_URL=postgresql://layer1:password@postgres:5432/layer1_db
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - PYTHONPATH=/app
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - layer1-worker
    networks:
      - fabric-network
    restart: unless-stopped
```

**Validation:**
- [ ] Docker compose syntax valid: `docker-compose config`

---

#### Step 2.4: Create Celery Kubernetes Deployment

**File to Create:**
- `k8s/base/layer1-celery-worker.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: layer1-celery-worker
  namespace: value-fabric
  labels:
    app: layer1-celery-worker
spec:
  replicas: 2  # Scale as needed
  selector:
    matchLabels:
      app: layer1-celery-worker
  template:
    metadata:
      labels:
        app: layer1-celery-worker
    spec:
      serviceAccountName: layer1-sa
      containers:
      - name: celery-worker
        image: ghcr.io/bmsull560/fabric_4l/layer1-ingestion:latest
        command: ["celery"]
        args:
          - "-A"
          - "layer1_ingestion.src.shared.tasks"
          - "worker"
          - "--loglevel=info"
          - "--concurrency=4"
          - "-Q"
          - "celery,ingestion,processing"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: REDIS_URL
        - name: PYTHONPATH
          value: "/app"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - layer1_ingestion.src.shared.tasks
            - inspect
            - --timeout
            - "5"
          initialDelaySeconds: 30
          periodSeconds: 30
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: layer1-celery-beat
  namespace: value-fabric
  labels:
    app: layer1-celery-beat
spec:
  replicas: 1  # Only one beat scheduler
  selector:
    matchLabels:
      app: layer1-celery-beat
  template:
    metadata:
      labels:
        app: layer1-celery-beat
    spec:
      serviceAccountName: layer1-sa
      containers:
      - name: celery-beat
        image: ghcr.io/bmsull560/fabric_4l/layer1-ingestion:latest
        command: ["celery"]
        args:
          - "-A"
          - "layer1_ingestion.src.shared.tasks"
          - "beat"
          - "--loglevel=info"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: layer1-secrets
              key: REDIS_URL
        - name: PYTHONPATH
          value: "/app"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

**Validation:**
- [ ] Kubernetes manifest valid: `kubectl apply --dry-run=client -f k8s/base/layer1-celery-worker.yaml`

---

#### Step 2.5: Add Celery Beat Schedule

**File to Create:**
- `services/layer1-ingestion/celerybeat-schedule.py`

```python
from celery.schedules import crontab
from layer1_ingestion.src.shared.tasks import celery_app

celery_app.conf.beat_schedule = {
    'cleanup-old-documents': {
        'task': 'layer1_ingestion.src.crawler.celery_tasks.cleanup_old_documents_task',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
        'args': (30,),  # Clean documents older than 30 days
    },
    'health-check': {
        'task': 'layer1_ingestion.src.crawler.celery_tasks.health_check_task',
        'schedule': 60.0,  # Run every minute
    },
}
```

**Validation:**
- [ ] Schedule loads without errors

---

#### Step 2.6: Test Celery End-to-End

**Commands:**
```bash
# Build and start services
cd value-fabric
docker-compose up -d redis postgres layer1-worker layer1-beat

# Verify worker is running
docker-compose logs layer1-worker | tail -20

# Test task execution
docker-compose exec layer1-ingestion python << 'EOF'
from layer1_ingestion.src.shared.tasks import celery_app
from layer1_ingestion.src.crawler.celery_tasks import crawl_url_task

# Send test task
result = crawl_url_task.delay("https://example.com", "test-tenant")
print(f"Task ID: {result.id}")

# Wait for result
try:
    output = result.get(timeout=30)
    print(f"Result: {output}")
except Exception as e:
    print(f"Task failed: {e}")
EOF

# Check Flower UI
curl http://localhost:5555/flower/
```

**Validation:**
- [ ] Worker processes running: `docker-compose ps | grep worker`
- [ ] Task submitted successfully
- [ ] Task completes without error
- [ ] Flower UI accessible

---

### Rollback Procedure

If Celery fails:

```bash
# 1. Stop Celery services
docker-compose stop layer1-worker layer1-beat flower

# 2. Revert to synchronous processing
# Update layer1 code to call functions directly instead of .delay()

# 3. Restart layer1 without Celery
docker-compose restart layer1-ingestion
```

---

### Acceptance Criteria

- [ ] Celery worker processes tasks asynchronously
- [ ] Redis broker and result backend operational
- [ ] Tasks retry on failure with exponential backoff
- [ ] Flower UI shows task queue and worker status
- [ ] Celery Beat runs scheduled tasks
- [ ] Health checks pass for worker pods
- [ ] Horizontal scaling works (add more worker replicas)

---

## BLOCKER 3: Monitoring and Alert Tuning

### Current State
- ✅ Prometheus metrics exposed
- ✅ Alert rules defined
- ✅ Alertmanager configuration exists
- ⚠️ Alert thresholds not tuned for production
- ⚠️ Alert routing (PagerDuty/Slack) not configured
- ⚠️ No SLOs defined

### Target State
Production-grade alerting with appropriate thresholds, proper routing to on-call systems, and documented SLOs.

---

### Implementation Steps

#### Step 3.1: Tune Prometheus Alert Rules

**File to Modify:**
- `monitoring/alerting/rules.yml`

Add production-tuned alerts:

```yaml
groups:
  - name: fabric-production-alerts
    interval: 30s
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            / sum(rate(http_requests_total[5m]))
          ) > 0.01
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over 5m"
          runbook_url: "https://wiki.internal/runbooks/high-error-rate"

      # High Latency (p99)
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, layer)
          ) > 2.0
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High latency detected in {{ $labels.layer }}"
          description: "p99 latency is {{ $value }}s"

      # LLM Cost Spike
      - alert: HighLLMCostRate
        expr: |
          (
            sum(increase(llm_cost_total[1h]))
            > 50  # $50/hour threshold
          )
        for: 15m
        labels:
          severity: warning
          team: finops
        annotations:
          summary: "High LLM cost rate"
          description: "LLM cost is ${{ $value }} in the last hour"

      # Critical LLM Cost
      - alert: HighLLMCostCritical
        expr: |
          (
            sum(increase(llm_cost_total[1h]))
            > 100  # $100/hour threshold
          )
        for: 5m
        labels:
          severity: critical
          team: finops
        annotations:
          summary: "CRITICAL: Excessive LLM cost"
          description: "LLM cost is ${{ $value }} in the last hour - immediate attention required"

      # Celery Queue Depth
      - alert: CeleryQueueBacklog
        expr: |
          celery_queue_length > 100
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Celery queue backlog"
          description: "Queue {{ $labels.queue_name }} has {{ $value }} pending tasks"

      # Disk Space
      - alert: DiskSpaceLow
        expr: |
          (
            node_filesystem_avail_bytes{mountpoint="/"}
            / node_filesystem_size_bytes{mountpoint="/"}
          ) < 0.15
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Disk space low on {{ $labels.instance }}"
          description: "{{ $value | humanizePercentage }} disk space remaining"

      # Memory Usage
      - alert: MemoryUsageHigh
        expr: |
          (
            container_memory_usage_bytes
            / container_spec_memory_limit_bytes
          ) > 0.85
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High memory usage in {{ $labels.pod }}"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # Pod CrashLoop
      - alert: PodCrashLooping
        expr: |
          rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Pod {{ $labels.pod }} is crash looping"
          description: "Pod has restarted {{ $value }} times in 15m"
```

**Validation:**
- [ ] Rules syntax valid: `promtool check rules monitoring/alerting/rules.yml`

---

#### Step 3.2: Configure Alertmanager Routing

**File to Modify:**
- `monitoring/alertmanager/alertmanager.yml`

```yaml
global:
  resolve_timeout: 5m
  # Slack webhook URL from Kubernetes secret
  slack_api_url_file: '/etc/alertmanager/secrets/slack_webhook_url'
  # PagerDuty integration key from Kubernetes secret
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

# Inhibit alerts of lower severity when higher severity fires
inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'namespace']

route:
  receiver: 'default-null'
  group_by: ['alertname', 'severity', 'namespace']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    # LLM cost alerts go to FinOps
    - match:
        team: finops
      receiver: 'slack-finops'
      continue: true
      repeat_interval: 1h

    # Critical alerts: PagerDuty + Slack
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true
      repeat_interval: 15m

    # Warning alerts: Slack only
    - match:
        severity: warning
      receiver: 'slack-warning'
      repeat_interval: 2h

receivers:
  - name: 'default-null'
    # No notifications for unmatched alerts (prevents spam)

  - name: 'slack-finops'
    slack_configs:
      - channel: '#finops-alerts'
        send_resolved: true
        title: '💰 {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Summary:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Severity:* {{ .Labels.severity }}
          *Runbook:* {{ .Annotations.runbook_url }}
          {{ end }}

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key_file: '/etc/alertmanager/secrets/pagerduty_key'
        description: '{{ .GroupLabels.alertname }}: {{ .GroupLabels.namespace }}'
        severity: '{{ .GroupLabels.severity }}'
        details:
          summary: '{{ .Annotations.summary }}'
          description: '{{ .Annotations.description }}'
          runbook: '{{ .Annotations.runbook_url }}'

  - name: 'slack-warning'
    slack_configs:
      - channel: '#platform-alerts'
        send_resolved: true
        title: '⚠️ {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *Summary:* {{ .Annotations.summary }}
          *Description:* {{ .Annotations.description }}
          *Namespace:* {{ .Labels.namespace }}
          {{ end }}
```

**Validation:**
- [ ] Config syntax valid: `amtool check-config monitoring/alertmanager/alertmanager.yml`

---

#### Step 3.3: Create Alertmanager Secrets

**File to Create:**
- `k8s/monitoring/alertmanager-secrets.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-secrets
  namespace: monitoring
type: Opaque
stringData:
  slack_webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  pagerduty_key: "YOUR_PAGERDUTY_INTEGRATION_KEY"
```

**Commands:**
```bash
# Apply secrets (DO NOT COMMIT THIS FILE)
kubectl apply -f k8s/monitoring/alertmanager-secrets.yaml

# Verify secrets
kubectl get secret alertmanager-secrets -n monitoring
```

**Validation:**
- [ ] Secrets created in Kubernetes
- [ ] Alertmanager can access secrets

---

#### Step 3.4: Define SLOs and Error Budgets

**File to Create:**
- `docs/operations/SLOs.md`

```markdown
# Service Level Objectives (SLOs)

## Layer 1 - Ingestion

### Availability
- **SLO:** 99.9% uptime
- **Measurement:** HTTP 200 responses / total requests
- **Window:** 30 days
- **Error Budget:** 0.1% = ~43 minutes downtime/month

### Latency
- **SLO:** p99 < 2 seconds for ingest requests
- **Measurement:** histogram_quantile(0.99, http_request_duration_seconds)
- **Window:** 7 days

### Celery Task Success
- **SLO:** 99.5% task completion
- **Measurement:** successful_tasks / total_tasks
- **Window:** 7 days

## Layer 2 - Extraction

### Availability
- **SLO:** 99.5% uptime
- **Measurement:** HTTP 200 responses
- **Window:** 30 days

### LLM Cost
- **SLO:** <$100/hour average
- **Measurement:** sum(llm_cost_total[1h])
- **Window:** 24 hours

## Alert Response Times

| Severity | Response Time | Resolution Time |
|----------|----------------|-----------------|
| Critical | 15 minutes | 2 hours |
| Warning | 1 hour | 8 hours |
| Info | 4 hours | 24 hours |
```

**Validation:**
- [ ] SLOs documented
- [ ] Teams briefed on response times

---

#### Step 3.5: Deploy Monitoring Stack

**Commands:**
```bash
# Apply Prometheus rules
kubectl apply -f monitoring/alerting/rules.yml

# Apply Alertmanager config
kubectl apply -f k8s/monitoring/alertmanager-configmap.yaml

# Restart Alertmanager to pick up new config
kubectl rollout restart deployment/alertmanager -n monitoring

# Verify alerts are firing
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
curl http://localhost:9090/api/v1/alerts
```

**Validation:**
- [ ] Prometheus rules loaded
- [ ] Alertmanager routing configured
- [ ] Test alert fires successfully

---

#### Step 3.6: Test Alert Firing

**Commands:**
```bash
# Test Slack notification
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "namespace": "test"
    },
    "annotations": {
      "summary": "Test alert",
      "description": "Testing alert routing"
    }
  }]'

# Check Slack channel for test alert

# Test PagerDuty integration
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestCritical",
      "severity": "critical",
      "namespace": "test"
    },
    "annotations": {
      "summary": "Test critical alert",
      "description": "Testing PagerDuty integration"
    }
  }]'

# Verify incident created in PagerDuty
```

**Validation:**
- [ ] Test alert appears in Slack
- [ ] Critical alert creates PagerDuty incident
- [ ] Alerts resolve correctly

---

### Rollback Procedure

If monitoring tuning fails:

```bash
# 1. Revert to previous alert rules
kubectl apply -f monitoring/alerting/rules-previous.yml

# 2. Disable alert routing
kubectl apply -f monitoring/alertmanager/alertmanager-no-routing.yml

# 3. Restart Alertmanager
kubectl rollout restart deployment/alertmanager -n monitoring
```

---

### Acceptance Criteria

- [ ] All critical alerts have runbook links
- [ ] Alerts route to correct channels (Slack/PagerDuty)
- [ ] SLOs defined and documented
- [ ] Alert thresholds tuned for production
- [ ] On-call rotation configured
- [ ] Alert noise minimized (no spam)
- [ ] Alertmanager resolves alerts when conditions clear

---

## Verification Commands Summary

### Blocker 1 (Vault) Verification
```bash
# Check Vault status
vault status

# Check ESO sync
kubectl get externalsecret -n value-fabric
kubectl get secrets -n value-fabric

# Verify secrets in pods
kubectl exec <layer1-pod> -n value-fabric -- env | grep DATABASE_URL
```

### Blocker 2 (Celery) Verification
```bash
# Check worker status
docker-compose ps | grep worker
kubectl get pods -n value-fabric | grep celery

# Test task execution
python -c "from layer1_ingestion.src.crawler.celery_tasks import crawl_url_task; print(crawl_url_task.delay('https://example.com', 'test'))"

# Check Flower
curl http://localhost:5555/flower/
```

### Blocker 3 (Monitoring) Verification
```bash
# Check Prometheus rules
kubectl get prometheusrule -n monitoring

# Check Alertmanager
kubectl get configmap alertmanager-config -n monitoring -o yaml

# Test alert
curl -X POST http://alertmanager:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"Test","severity":"warning"},"annotations":{"summary":"test"}}]'
```

---

## Implementation Order

**Week 1:**
- **Day 1-2:** Blocker 1 - Vault Integration
- **Day 3-5:** Blocker 2 - L1 Celery/Redis
- **Day 6-7:** Blocker 3 - Monitoring Tuning

**Do not proceed to next blocker until previous is verified.**
