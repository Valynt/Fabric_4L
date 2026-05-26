# Value Fabric Kubernetes Deployment

Production-grade Kubernetes manifests for the Value Fabric platform.

This directory supports both:
- Legacy flat manifests (`kubectl apply -f k8s/`) for compatibility.
- Canonical Kustomize deployments organised into four composable axes:
  - `k8s/base/` — core application workloads (Deployments, Services, ConfigMaps, NetworkPolicies, HPAs, PDBs).
  - `k8s/envs/{dev,staging,prod}/` — environment overlays (replicas, image pinning, ExternalSecrets).
  - `k8s/routing/{nginx,gateway-api,istio}/` — mutually exclusive external routing strategies. Routing stacks do **not** import `../../base`.
  - `k8s/deployments/{dev-nginx,staging-nginx,prod-nginx,prod-gateway-api,prod-istio}/` — final deployable compositions, each importing exactly one env and one routing stack.

> Legacy path `k8s/overlays/{dev,prod}` has been replaced by `k8s/envs/{dev,staging,prod}`. Use `k8s/deployments/<env>-<routing>/` for final deployable targets.

## Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Container images built and available in registry
- **metrics-server** installed (required for HorizontalPodAutoscaler)

## Security Hardening

This deployment includes production-grade security controls:

### Secret Management Default (All Cluster Types)

- **Default path for dev/shared/staging/prod:** External Secrets Operator + Vault or Infisical.
- `k8s/secrets.yml` is a legacy local-only file path and is blocked by commit/CI guardrails.
- Shared dev clusters must not contain manually managed plaintext/base64 Kubernetes Secret manifests.

### Pod Security Contexts

All deployments run with:
- Non-root user (UID 1000)
- Read-only root filesystem
- Dropped all capabilities
- No privilege escalation
- Runtime default seccomp profile

### Network Policies

Zero-trust network segmentation is enforced via `k8s/network-policies/`:
- Default deny-all for ingress/egress
- Explicit allow rules for required service-to-service communication
- DNS resolution allowed cluster-wide
- Layer-specific policies enforce least-privilege access

### Horizontal Pod Autoscaler (HPA)

Auto-scaling configured for:
- **layer2-extraction**: 2-6 replicas at 70% CPU
- **layer4-agents**: 2-10 replicas at 70% CPU / 80% memory
- **frontend**: 2-8 replicas at 70% CPU

**Scaling Behavior:**
- Scale-up: 100% increase per minute after 60s stabilization
- Scale-down: 50% decrease per minute after 300s stabilization (prevents flapping)

Requires metrics-server: `kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`

### Pod Disruption Budgets

Critical services maintain availability during disruptions:
- **layer4-agents**: `minAvailable: 1`

### Image Registry

Service images are published to `ghcr.io/bmsull560/fabric_4l/<service>`.

The `k8s/base/kustomization.yaml` `images:` block maps the placeholder names
used in manifests (`services/<name>:main`) to the real registry paths.
Environment overlays override `newTag` to pin a specific version.

**CI secrets required:**

| Secret | Purpose |
|---|---|
| `GHCR_TOKEN` | Push/pull access to `ghcr.io/bmsull560/fabric_4l/*` |
| `GHCR_USERNAME` | Registry username (defaults to `github.actor`) |

**Cross-org base images (`ghcr.io/value-fabric/base-images/`):**

These images are **private** — a `GHCR_TOKEN` with read access to the
`value-fabric` org is required. The CI workflow (`build-deploy.yml`) has a
`Verify cross-org base image access` step that falls back to public Docker Hub
images if the `value-fabric` org images are inaccessible. If the primary images
are unavailable and you need them, add a PAT with `read:packages` scope to the
`GHCR_TOKEN` secret in the repository settings.

### Image Pinning

Production overlay uses SHA256 digest pinning (immutable references):
```bash
# CI updates digests via:
kustomize edit set image "ghcr.io/bmsull560/fabric_4l/layer4-agents@sha256:abc123..."
```

## Recommended: Kustomize Deployment

Deploy a final composition from `k8s/deployments/`. Each composition imports
exactly one env overlay and exactly one routing stack.

Phase 1 supported targets:

| Target | Env | Routing | Status |
|---|---|---|---|
| `dev-nginx` | dev | NGINX Ingress + cert-manager | Supported |
| `staging-nginx` | staging | NGINX Ingress + cert-manager | Supported (pre-production validation) |
| `prod-nginx` | prod | NGINX Ingress + cert-manager | Supported (default production path) |
| `prod-gateway-api` | prod | Gateway API + cert-manager | Supported (requires Gateway API CRDs + controller) |
| `prod-istio` | prod | Istio Gateway / VirtualService | EXPERIMENTAL (CI-render only) |

```bash
# Render manifests (use --load-restrictor=LoadRestrictionsNone for prod
# because the prod env overlay imports k8s/external-secrets/).
kustomize build k8s/deployments/dev-nginx --load-restrictor=LoadRestrictionsNone
kustomize build k8s/deployments/staging-nginx --load-restrictor=LoadRestrictionsNone
kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone
kustomize build k8s/deployments/prod-gateway-api --load-restrictor=LoadRestrictionsNone

# Validate against API server (recommended in staging/prod clusters)
kustomize build k8s/deployments/dev-nginx  --load-restrictor=LoadRestrictionsNone | kubectl apply --dry-run=server -f -
kustomize build k8s/deployments/staging-nginx --load-restrictor=LoadRestrictionsNone | kubectl apply --dry-run=server -f -
kustomize build k8s/deployments/prod-nginx --load-restrictor=LoadRestrictionsNone | kubectl apply --dry-run=server -f -

# Deploy
kubectl apply -k k8s/deployments/dev-nginx
# or
kubectl apply -k k8s/deployments/staging-nginx
# or
kubectl apply -k k8s/deployments/prod-nginx
# or (requires Gateway API CRDs + controller pre-installed)
kustomize build k8s/deployments/prod-gateway-api --load-restrictor=LoadRestrictionsNone | kubectl apply -f -
```

Hostnames per deployment are sourced from a single `routing-host` ConfigMap
in each `k8s/deployments/<name>/hostname-config.yaml`. Edit that file to
change the external hostnames; Kustomize `replacements:` propagate the
values into every Ingress/Gateway/HTTPRoute/VirtualService/Certificate field
at render time.

### Overlay Policy

- `dev` overlay: pragmatic defaults for local development. Uses placeholder SHA digests (will fail without image build).
- `staging` overlay: **production mirror** — SHA256 digest pinned images, ExternalSecrets, 2 replicas. Validates production-like configuration with lower blast radius.
- `prod` overlay: **SHA256 digest pinned images** (immutable), ExternalSecrets, 2 replicas, production resource settings.

## Deployment Order

Deploy in this order to satisfy dependencies:

```bash
# 1. Create namespace
kubectl apply -f namespace.yml

# 2. Configure secret back-end and sync (all envs)
# Preferred: Vault integration
kubectl apply -f k8s/external-secrets/vault-integration.yml
# Alternative: Infisical integration manifests under k8s/infisical/

# 3. Create config maps
kubectl apply -f configmap-global.yml

# 4. Deploy infrastructure (Neo4j, Postgres, Redis)
kubectl apply -f neo4j.yml
kubectl apply -f postgres.yml
kubectl apply -f redis.yml

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n value-fabric --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n value-fabric --timeout=60s
kubectl wait --for=condition=ready pod -l app=neo4j -n value-fabric --timeout=180s

# 5. Deploy application layers L1-L4
kubectl apply -f layer1-ingestion.yml
kubectl apply -f layer2-extraction.yml
kubectl apply -f layer3-knowledge.yml
kubectl apply -f layer4-agents.yml

# Wait for L1-L4 to be ready (required for L5/L6 dependencies)
kubectl wait --for=condition=ready pod -l app=layer1-ingestion -n value-fabric --timeout=120s
kubectl wait --for=condition=ready pod -l app=layer2-extraction -n value-fabric --timeout=120s
kubectl wait --for=condition=ready pod -l app=layer3-knowledge -n value-fabric --timeout=120s
kubectl wait --for=condition=ready pod -l app=layer4-agents -n value-fabric --timeout=120s

# 6. Deploy application layers L5-L6
kubectl apply -f layer5-ground-truth.yml
kubectl apply -f layer6-benchmarks.yml

# 7. Deploy monitoring stack
kubectl apply -f k8s/base/monitoring-alertmanager.yml
kubectl apply -f monitoring-prometheus.yml

# Verify all services
kubectl get pods -n value-fabric
```

## Quick Deploy All

```bash
kubectl apply -f .
```

> `kubectl apply -f .` is for quick smoke/dev validation only. For shared environments, deploy via `k8s/deployments/*` with External Secrets configured first.

## Service Dependencies

```
layer1-ingestion → postgres, redis
layer2-extraction → redis, neo4j
layer3-knowledge → neo4j, redis
layer4-agents → redis, neo4j, postgres
layer5-ground-truth → postgres, layer3-knowledge
layer6-benchmarks → (standalone - no deps)
frontend → layer4-agents, layer5-ground-truth, layer6-benchmarks
```

## Health Checks

All services expose health endpoints:

| Service | Health Endpoint |
|---------|-----------------|
| layer1 | `/api/v1/ingestion/health` |
| layer2 | `/health` |
| layer3 | `/health` |
| layer4 | `/health` |
| layer5 | `/api/v1/health` |
| layer6 | `/health` |
| frontend | `/` |

## Monitoring

Prometheus metrics available at `/metrics` on all services.

Monitoring manifests:

- `base/monitoring-alertmanager.yml` - Canonical Alertmanager manifest used by overlays
- `monitoring-prometheus.yml` - Prometheus server with alerting rules
- `monitoring/jaeger-deployment.yaml` - Jaeger all-in-one deployment with persistent span storage configured via OpenSearch/Elasticsearch

### Jaeger Storage and Recovery Runbook

- **Storage backend**: Jaeger uses `SPAN_STORAGE_TYPE=elasticsearch` and connects to the cluster endpoint from `ConfigMap/jaeger-storage-config` (`ES_SERVER_URLS`, TLS toggle, and index prefix). Credentials are loaded from `Secret/jaeger-storage-credentials` and should be supplied by External Secrets or Infisical in non-dev clusters.
- **Retention policy**: Trace retention is governed by the OpenSearch/Elasticsearch Index State Management (or ILM) policy for the `jaeger-span*` index prefix. Default platform target is **7 days hot retention** unless SRE sets an environment-specific override.
- **Recovery expectations after pod restart**: Jaeger UI/query/collector restarts do **not** erase historical spans; traces remain queryable as long as they are still retained in OpenSearch/Elasticsearch. Only in-memory buffers for in-flight requests are lost during abrupt termination.
- **Failure mode**: If storage is unavailable or credentials are invalid, Jaeger admin readiness (`:14269`) fails and the pod remains unready until storage connectivity is restored.

### Alertmanager Configuration

Alertmanager is configured with multi-channel routing:

| Severity | Slack | PagerDuty | Webhook |
|----------|-------|-----------|---------|
| critical | #vf-alerts-critical | ✅ | fallback |
| warning | #vf-alerts | - | fallback |
| info | #vf-alerts | - | fallback |

**Prerequisites:**

1. **External Secrets Operator** must be installed and configured with Vault/Infisical
2. **Slack webhook URL** configured in Vault at `value-fabric/monitoring/slack-webhook-url`
3. **PagerDuty integration key** (optional) at `value-fabric/monitoring/pagerduty-integration-key`

**Deploy Alertmanager:**

```bash
# 1. Create external secret for Alertmanager
kubectl apply -f k8s/external-secrets/alertmanager-secrets.yaml

# 2. Deploy Alertmanager
kubectl apply -k k8s/envs/prod

# 3. Verify deployment
kubectl wait --for=condition=ready pod -l app=alertmanager -n value-fabric --timeout=60s
```

**Alertmanager features:**
- Slack notifications with rich templates (includes runbook links)
- PagerDuty escalation for critical alerts
- Inhibition rules (warning suppressed when critical firing)
- Grouping by alertname and severity
- Persistent storage for alert history

**Validate notification routing:**

```bash
# Port-forward to Alertmanager
kubectl port-forward -n value-fabric svc/alertmanager 9093:9093

# Check Alertmanager status
curl -fsS http://localhost:9093/api/v2/status

# Test alert reception
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Test alert"}}]'
```

Runtime verification playbook:

```bash
# Forward monitoring services locally
kubectl port-forward -n value-fabric svc/prometheus 9090:9090
kubectl port-forward -n value-fabric svc/alertmanager 9093:9093

# Verify target health and scrape status
curl -fsS http://localhost:9090/api/v1/targets

# Verify loaded rules and evaluation health
curl -fsS http://localhost:9090/api/v1/rules

# Verify active alerts in Prometheus
curl -fsS http://localhost:9090/api/v1/alerts

# Verify Alertmanager pipeline endpoint
curl -fsS http://localhost:9093/api/v2/status

# Smoke an alert directly into Alertmanager
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels":{"alertname":"Task46Smoke","severity":"warning"},"annotations":{"summary":"Task 46 smoke alert"}}]'
```

## Secrets Management

**WARNING**: Default secrets are provided for development only.

CI and admission enforce a **secret placeholder guardrail**:

- `.github/workflows/k8s-readiness.yml` runs `scripts/security/placeholder_secret_scan.py`.
- `k8s/policy/kyverno-secret-placeholder-guardrails.yaml` rejects unguarded Secret placeholder values at admission time.
- `k8s/monitoring/placeholder-secret-scanner-cronjob.yaml` provides a six-hour runtime cluster scan for Secrets and ConfigMaps.
- Dev-only placeholder Secret manifests must carry `value-fabric.io/environment: dev`, `value-fabric.io/non-prod-only: "true"`, `value-fabric.io/secret-scope: dev-placeholder`, and `value-fabric.io/allowed-namespaces`.

### Secret Guardrail Remediation

If CI fails with a secret guardrail error:
1. Open the file and line reported by the workflow log.
2. Replace weak defaults with strong local-development values or wire the value from your secrets manager.
3. For staging and production, replace direct `Secret` resources with `ExternalSecret` or Infisical `InfisicalSecret` mappings.
4. Keep placeholder tokens only in explicitly guarded dev manifests or templates.
5. Re-run checks locally before pushing:
   ```bash
   python scripts/security/placeholder_secret_scan.py k8s --allow-guarded-dev
   ```

For production:
1. Use External Secrets Operator or Infisical for secret injection.
2. Apply Kyverno guardrails before app manifests:
   ```bash
   kubectl apply -f k8s/policy/kyverno-secret-placeholder-guardrails.yaml
   ```
3. Enable periodic runtime scanning:
   ```bash
   kubectl apply -f k8s/monitoring/placeholder-secret-scanner-cronjob.yaml
   ```
4. Never commit real secrets to git.

## Resource Requirements

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit |
|-----------|-------------|----------------|-----------|--------------|
| Neo4j | 500m | 2Gi | 2000m | 4Gi |
| Postgres | 100m | 256Mi | 500m | 1Gi |
| Redis | 100m | 128Mi | 500m | 512Mi |
| Layer 1-6 | 100m | 128Mi | 500m | 512Mi |

## Persistent Storage

| PVC | Size | Purpose |
|-----|------|---------|
| neo4j-data | 20Gi | Neo4j graph data |
| neo4j-logs | 5Gi | Neo4j logs |
| postgres-pvc | 10Gi | PostgreSQL data |

## Troubleshooting

Check pod status:
```bash
kubectl get pods -n value-fabric
```

View logs:
```bash
kubectl logs -n value-fabric deployment/layer5-ground-truth
```

Check service endpoints:
```bash
kubectl get svc -n value-fabric
```

Port forward for local testing:
```bash
kubectl port-forward -n value-fabric svc/layer5-ground-truth 8005:8005
```

## Migration Note

Flat manifests are intentionally preserved during migration. New CI and production checks should target `k8s/deployments/<env>-<routing>/` first.
