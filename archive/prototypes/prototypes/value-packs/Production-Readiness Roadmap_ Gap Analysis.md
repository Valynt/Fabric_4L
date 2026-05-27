# Production-Readiness Roadmap: Gap Analysis

This document provides a comprehensive gap analysis of the proposed "Production-Readiness Audit & Remediation Roadmap Plan" against the actual state of the `Fabric_4L` repository.

While the proposed roadmap is highly structured and covers the majority of standard CI/CD, testing, and deployment gates, it misses several critical, domain-specific production requirements that are currently absent from the codebase. If the roadmap is executed exactly as written, the resulting system will pass all CI gates but will still fail in a real-world production environment.

---

## 1. Critical Gaps (P0 - Production Blockers)

These are missing from both the codebase and the proposed roadmap.

### 1.1 The Entire Tenant Management Workstream
The roadmap mentions checking "Neo4j read paths flagged in prior audit" (Phase 4.1), but it completely misses the broader tenant management overhaul that is currently in progress.
* **The Gap:** The codebase currently has a broken RLS implementation in Layer 5 (the `db_session()` generator does not execute `SET LOCAL app.tenant_id`), meaning RLS is not enforced at the session level [1]. Furthermore, Layer 1 and Layer 5 use `organization_id` instead of `tenant_id`, breaking the middleware contract.
* **Why it matters:** Without fixing the Layer 5 RLS gap, cross-tenant data leakage is guaranteed in the Ground Truth layer.
* **Recommendation:** The roadmap must explicitly incorporate the execution of the `tenant-management-phase-1-rls-hardening-rescoped.md` plan.

### 1.2 Missing Ingress and TLS Infrastructure
The roadmap checks `k8s/` manifests for resource limits, probes, and HPAs (Phase 4.11), but misses the entrypoint.
* **The Gap:** There are **zero** Ingress manifests, Gateway API routes, or Istio VirtualServices in the `k8s/` directory [2]. There is also no `cert-manager` configuration for TLS.
* **Why it matters:** The application can be deployed to Kubernetes, but it cannot receive any external traffic from the internet.
* **Recommendation:** Add an infrastructure audit phase specifically for external routing, DNS, and TLS termination.

### 1.3 Missing External Secrets for Layers 5 & 6
The roadmap checks `.infisical.json` and `vault-integration.yml` (Phase 4.2).
* **The Gap:** The `k8s/external-secrets/` directory contains manifests for Layers 1-4, Neo4j, and Redis, but it is missing `layer5-secrets.yaml` and `layer6-secrets.yaml` [3].
* **Why it matters:** Layers 5 and 6 will fail to boot in production because their Kubernetes `Secret` resources will never be populated by the External Secrets Operator.
* **Recommendation:** Add a specific check for ExternalSecret manifest completeness across all 6 layers.

---

## 2. High-Priority Gaps (P1 - Reliability & Security)

### 2.1 Missing Kubernetes Scaling & Resilience Primitives
The roadmap claims to check for HPAs and PDBs (Phase 4.11).
* **The Gap:**
  * **Missing HPAs:** Layer 1, Layer 3, Layer 5, and Layer 6 have no HorizontalPodAutoscaler manifests [4].
  * **Missing PDBs:** Layer 1, Layer 5, and Layer 6 have no PodDisruptionBudget manifests [5].
* **Why it matters:** During node upgrades or traffic spikes, these layers will either drop traffic (no PDB) or fall over from load (no HPA).

### 2.2 Unfiltered Neo4j Read Paths
The roadmap mentions checking Neo4j read paths (Phase 4.1), but underestimates the scope.
* **The Gap:** A scan of `services/layer3-knowledge/src/api/main.py` reveals at least 10 `MATCH` queries that do not include a `tenant_id` filter (e.g., lines 1964, 1977, 2040, 3343) [6].
* **Why it matters:** This is a direct cross-tenant data exposure vulnerability.
* **Recommendation:** Elevate this from a "check" to a mandatory remediation item.

### 2.3 Duplicate and Conflicting CI Gates
The roadmap plans to run all 34 GitHub Actions workflows (Phase 1.3).
* **The Gap:** The repo currently has two conflicting contract enforcement workflows: `contract-compliance.yml` and `platform-contract-gate.yml` [7]. Furthermore, the Python linting script (`platform_contract_lint.py`) flags `get_db_with_tenant()` as an error, which conflicts with the actual Layer 4 implementation.
* **Why it matters:** Running the gates as-is will result in false negatives and conflicting enforcement rules.
* **Recommendation:** The roadmap must include a step to consolidate duplicate CI workflows before running the audit.

---

## 3. Medium-Priority Gaps (P2 - Operational Readiness)

### 3.1 Missing Application-Level Defenses
* **Rate Limiting:** There is no rate limiting, throttling, or `slowapi` implementation in any of the FastAPI layers [8].
* **CORS:** There is no `CORSMiddleware` configured in the backend layers [9], which will block the frontend from communicating with the APIs in a production environment.
* **Connection Pooling:** Layer 1 hardcodes its database connection pool (`pool_size=5, max_overflow=10`) rather than reading from environment variables [10], which will cause connection exhaustion under load.

### 3.2 Missing Observability Coverage
The roadmap checks for OTel wiring and dashboards (Phase 4.5).
* **The Gap:** OpenTelemetry and Prometheus metrics are only implemented in the Layer 1 crawler (`playwright_crawler.py` and `prometheus_metrics.py`) [11]. Layers 2 through 6 have no instrumentation.
* **Why it matters:** The Grafana dashboards exist, but they will be empty for 80% of the application.

### 3.3 Missing Data Retention Policies
* **The Gap:** There are no data retention, TTL, or purge mechanisms implemented for the PostgreSQL databases or the Redis queues [12].
* **Why it matters:** The database will grow unbounded, eventually causing performance degradation and storage exhaustion.

---

## 4. Summary Recommendation

The proposed roadmap is an excellent framework for a CI/CD and static analysis audit. However, to achieve true **production readiness**, the roadmap must be amended to include:

1. **Infrastructure Completeness:** Audit for Ingress, TLS, and missing ExternalSecrets.
2. **Tenant Management:** Execute the rescoped Phase 1 RLS hardening plan to fix the Layer 5 enforcement gap.
3. **Application Defenses:** Add checks for CORS, rate limiting, and configurable connection pooling.
4. **Observability Parity:** Ensure OTel/Prometheus instrumentation exists across all 6 layers, not just Layer 1.

## References
[1] `services/layer5-ground-truth/src/layer5_ground_truth/database.py`
[2] `find k8s/ -name "*ingress*"` (Returns empty)
[3] `ls k8s/external-secrets/`
[4] `ls k8s/base/hpa/`
[5] `ls k8s/base/pdb/`
[6] `services/layer3-knowledge/src/api/main.py`
[7] `.github/workflows/`
[8] `grep -rn "rate.limit" services/` (Returns empty)
[9] `grep -rn "CORSMiddleware" services/` (Returns empty)
[10] `services/layer1-ingestion/src/shared/database.py`
[11] `services/layer1-ingestion/src/metrics/prometheus_metrics.py`
[12] `grep -rn "retention\|purge" services/` (Returns empty)
