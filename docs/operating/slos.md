# SLO Definition & Error Budget Framework — Fabric_4L v1.2.0

**Author:** SRE Team (Staff+)  
**Status:** Production-Ready  
**Last Updated:** 2024-06-15  
**Review Cycle:** Quarterly (every 90 days)

---

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [SLO 1: API Availability](#slo-1-api-availability)
3. [SLO 2: API Latency (p95)](#slo-2-api-latency-p95)
4. [SLO 3: Agent Workflow Success Rate](#slo-3-agent-workflow-success-rate)
5. [SLO 4: Tenant Isolation Enforcement](#slo-4-tenant-isolation-enforcement)
6. [SLO 5: Data Ingestion Throughput](#slo-5-data-ingestion-throughput)
7. [SLO 6: Frontend LCP](#slo-6-frontend-lcp)
8. [Error Budget Policy](#error-budget-policy)
9. [Burn Rate Alerting Reference](#burn-rate-alerting-reference)
10. [Dashboard Integration](#dashboard-integration)

---

## Framework Overview

### SLO Document Conventions

Each SLO in this document follows this structure:

| Field | Description |
|-------|-------------|
| **SLI** | Service Level Indicator — the measurable metric |
| **SLO** | Service Level Objective — the target over a compliance window |
| **SLA** | Service Level Agreement — customer-facing commitment (if applicable) |
| **Error Budget** | Allowed failures = 100% − SLO target |
| **Burn Rate** | How fast the error budget is being consumed |
| **Measurement** | PromQL query for the SLI |
| **Dashboard** | Grafana panel JSON for visualization |

### Multi-Tenancy Considerations

All SLOs are measured **globally** (across all tenants) unless explicitly noted. Per-tenant SLO tracking is available via `tenant_id` labels but is not part of the core error budget calculation.

### SLO Summary Matrix

| SLO | Target | Window | Severity | Burn Rate Alert |
|-----|--------|--------|----------|-----------------|
| API Availability | 99.9% | 30d | Critical | Fast: 14.4x, Slow: 2x |
| API Latency (p95) | p95 < 200ms | 7d | Critical | Fast: 6x, Slow: 1x |
| Agent Workflow Success | 99.5% | 7d | High | Fast: 14.4x, Slow: 2x |
| Tenant Isolation | 100% | Real-time | Critical | Immediate (0s for) |
| Data Ingestion Throughput | 10,000 docs/hr | 1d | Medium | Fast: 14.4x, Slow: 2x |
| Frontend LCP | < 2.5s (p75) | 7d | Medium | Fast: 6x, Slow: 1x |

---

## SLO 1: API Availability

### Specification

- **SLI:** Ratio of successful HTTP requests (status < 500) to total HTTP requests across all 6 backend layers.
- **SLO:** 99.9% of requests succeed over a 30-day rolling window.
- **SLA:** 99.5% — if breached, customer credits apply per the Customer Agreement.
- **Error Budget:** 0.1% of requests may fail over 30 days.
  - For 1,000,000 requests/month: **1,000 failed requests allowed**.

### Rationale

API availability is the foundational SLO. A 99.9% target means no more than ~43 minutes of downtime per month. This balances reliability with the agility needed for ML model deployments and schema migrations.

### Error Budget Calculation

```
Error Budget (requests) = (1 − 0.999) × total_requests_30d
                        = 0.001 × total_requests_30d

Error Budget Burn Rate = actual_errors / error_budget

Example: If 500 requests fail on day 1 of 30 (with 100k daily requests):
  Error Budget = 0.001 × 3,000,000 = 3,000 requests
  Burn Rate = 500 / (3,000/30) = 500 / 100 = 5x
```

### Measurement (PromQL)

```promql
# SLI: Availability ratio over 30d
(
  sum(rate(http_requests_total{status!~"5.."}[30d]))
  /
  sum(rate(http_requests_total[30d]))
) * 100

# Error budget remaining (0 to 1, where 1 = 100% remaining)
1 - (
  sum(rate(http_requests_total{status=~"5.."}[30d]))
  /
  (0.001 * sum(rate(http_requests_total[30d])))
)

# Burn rate over 1h window
(
  sum(rate(http_requests_total{status=~"5.."}[1h]))
  /
  sum(rate(http_requests_total[1h]))
) / (1 - 0.999)
```

### Recording Rule

See `recording-rules.yml`: `record: slo:api_availability:ratio_30d`

### Grafana Panel JSON

```json
{
  "id": 101,
  "title": "SLO-1: API Availability (30d)",
  "type": "stat",
  "targets": [
    {
      "expr": "slo:api_availability:ratio_30d",
      "legendFormat": "Availability",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit",
      "min": 0.995,
      "max": 1,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 0.995},
          {"color": "green", "value": 0.999}
        ]
      }
    }
  },
  "options": {
    "graphMode": "area",
    "colorMode": "value",
    "justifyMode": "center"
  },
  "gridPos": {"h": 4, "w": 8, "x": 0, "y": 0}
}
```

### Burn Rate Alerts

| Burn Rate | Alert Window | Long Window | Action |
|-----------|-------------|-------------|--------|
| 14.4x | 2m | 1h | Page on-call SRE immediately |
| 2x | 5m | 6h | Create P1 ticket, notify team Slack |

---

## SLO 2: API Latency (p95)

### Specification

- **SLI:** 95th percentile of HTTP request latency across all 6 backend layers.
- **SLO:** p95 latency < 200ms over a 7-day rolling window.
- **SLA:** p95 < 500ms — customer-facing commitment.
- **Error Budget:** 5% of requests may exceed 200ms over 7 days.
  - This is a **distribution-based** SLO using histogram buckets.

### Rationale

Latency directly impacts user experience. The 200ms p95 target ensures that the vast majority of API calls feel instantaneous while allowing headroom for complex L4 agent workflows and L3 graph queries.

### Error Budget Calculation

```
SLI = histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[7d]))
Error Budget = requests where latency > 200ms

Burn Rate = (requests_over_200ms_1h / total_requests_1h) / 0.05

Example: If 8% of requests exceed 200ms over 1h:
  Burn Rate = 0.08 / 0.05 = 1.6x
```

### Measurement (PromQL)

```promql
# SLI: p95 latency over 7d
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[7d])) by (le)
)

# Fraction of requests under 200ms (good / total)
sum(rate(http_request_duration_seconds_bucket{le="0.2"}[7d]))
/
sum(rate(http_request_duration_seconds_count[7d]))

# Burn rate: fraction of slow requests over 1h divided by budget
(
  sum(rate(http_request_duration_seconds_bucket{le="0.2"}[1h]))
  /
  sum(rate(http_request_duration_seconds_count[1h]))
) / 0.95
```

### Recording Rule

See `recording-rules.yml`: `record: slo:api_latency:p95_7d`

### Grafana Panel JSON

```json
{
  "id": 102,
  "title": "SLO-2: API Latency p95 (7d)",
  "type": "timeseries",
  "targets": [
    {
      "expr": "slo:api_latency:p95_7d * 1000",
      "legendFormat": "p95 latency (ms)",
      "refId": "A"
    },
    {
      "expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[7d])) by (le)) * 1000",
      "legendFormat": "p50 latency (ms)",
      "refId": "B"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ms",
      "min": 0,
      "max": 1000,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "green", "value": null},
          {"color": "yellow", "value": 200},
          {"color": "red", "value": 500}
        ]
      },
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10,
        "gradientMode": "opacity",
        "axisLabel": "Latency (ms)"
      }
    }
  },
  "options": {
    "legend": {"displayMode": "table", "placement": "right", "calcs": ["mean", "max", "lastNotNull"]},
    "tooltip": {"mode": "multi"}
  },
  "gridPos": {"h": 8, "w": 12, "x": 8, "y": 0}
}
```

### Burn Rate Alerts

| Burn Rate | Alert Window | Long Window | Action |
|-----------|-------------|-------------|--------|
| 6x | 2m | 1h | Page on-call SRE |
| 1x | 5m | 6h | Slack notification, create ticket |

---

## SLO 3: Agent Workflow Success Rate

### Specification

- **SLI:** Ratio of successfully completed agent workflows to total initiated workflows on L4.
- **SLO:** 99.5% of workflows complete successfully over a 7-day rolling window.
- **SLA:** 99.0% — customer-facing commitment for enterprise tier.
- **Error Budget:** 0.5% of workflows may fail over 7 days.
  - For 100,000 workflows/week: **500 failed workflows allowed**.

### Rationale

L4 is the intelligence layer. Failed workflows represent lost productivity. This SLO specifically measures workflow completion, not intermediate LLM call success (which is tracked separately via SLO-2 latency).

### Error Budget Calculation

```
Error Budget (workflows) = (1 − 0.995) × total_workflows_7d
                         = 0.005 × total_workflows_7d

Burn Rate = actual_failures / (error_budget / 7 * hours_elapsed)

Example: If 50 workflows fail on day 1 (with 14,285 daily workflows):
  Error Budget = 0.005 × 100,000 = 500 workflows
  Burn Rate = 50 / (500/7) = 50 / 71.4 = 0.7x (no alert)
```

### Measurement (PromQL)

```promql
# SLI: Workflow success ratio over 7d
(
  sum(rate(agent_workflow_completed_total{status="success"}[7d]))
  /
  sum(rate(agent_workflow_total[7d]))
) * 100

# Error budget remaining
1 - (
  sum(rate(agent_workflow_failed_total[7d]))
  /
  (0.005 * sum(rate(agent_workflow_total[7d])))
)

# Burn rate: fast burn window (1h)
(
  sum(rate(agent_workflow_failed_total[1h]))
  /
  sum(rate(agent_workflow_total[1h]))
) / (1 - 0.995)
```

### Recording Rule

See `recording-rules.yml`: `record: slo:agent_workflow_success:ratio_7d`

### Grafana Panel JSON

```json
{
  "id": 103,
  "title": "SLO-3: Agent Workflow Success (7d)",
  "type": "gauge",
  "targets": [
    {
      "expr": "slo:agent_workflow_success:ratio_7d",
      "legendFormat": "Success Rate",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit",
      "min": 0.98,
      "max": 1,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 0.99},
          {"color": "green", "value": 0.995}
        ]
      }
    }
  },
  "options": {
    "showThresholdLabels": true,
    "showThresholdMarkers": true,
    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false}
  },
  "gridPos": {"h": 4, "w": 8, "x": 16, "y": 0}
}
```

### Burn Rate Alerts

| Burn Rate | Alert Window | Long Window | Action |
|-----------|-------------|-------------|--------|
| 14.4x | 2m | 1h | Page on-call SRE + Agents team |
| 2x | 5m | 6h | Slack notification to Agents channel |

---

## SLO 4: Tenant Isolation Enforcement

### Specification

- **SLI:** Number of cross-tenant data access attempts detected.
- **SLO:** 100% — zero cross-tenant access attempts over any time window.
- **SLA:** 100% — contractual guarantee for all tiers. **Any breach is a P0 incident.**
- **Error Budget:** **None.** This is a hard constraint, not a statistical SLO.

### Rationale

Tenant isolation is a security invariant, not a performance target. PostgreSQL RLS policies, application-level tenant checks, and network policies provide defense in depth. **Any breach triggers immediate incident response.**

### Measurement (PromQL)

```promql
# SLI: Cross-tenant access attempts (must always be 0)
sum(increase(cross_tenant_access_attempts_total[1m]))

# Per-layer breakdown
sum by (layer) (increase(cross_tenant_access_attempts_total[1m]))

# Per-tenant attempts (for forensics)
sum by (source_tenant, target_tenant) (
  increase(cross_tenant_access_attempts_total[1m])
)
```

### Recording Rule

See `recording-rules.yml`: `record: slo:tenant_isolation:breach_rate_1m`

### Grafana Panel JSON

```json
{
  "id": 104,
  "title": "SLO-4: Tenant Isolation (CRITICAL)",
  "type": "stat",
  "targets": [
    {
      "expr": "slo:tenant_isolation:breach_rate_1m",
      "legendFormat": "Cross-tenant attempts",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "min": 0,
      "max": 10,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "green", "value": null},
          {"color": "red", "value": 1}
        ]
      },
      "custom": {
        "displayMode": "color-background-solid"
      }
    }
  },
  "options": {
    "graphMode": "area",
    "colorMode": "background",
    "justifyMode": "center"
  },
  "gridPos": {"h": 4, "w": 8, "x": 0, "y": 4}
}
```

### Alert Configuration

```yaml
- alert: TenantIsolationBreached
  expr: increase(cross_tenant_access_attempts_total[1m]) > 0
  for: 0s          # Immediate alert — no grace period
  labels:
    severity: critical
    team: security
  annotations:
    summary: "TENANT ISOLATION BREACH DETECTED"
    runbook_url: "https://github.com/bmsull560/Fabric_4L/blob/main/ops/runbooks/TENANT_ISOLATION_BREACH.md"
```

### Incident Response

1. **Immediate (0-5 min):** Page Security On-Call + SRE Lead
2. **Containment (5-15 min):** Isolate affected tenant, revoke sessions
3. **Investigation (15-60 min):** Determine scope via audit logs
4. **Notification (within 1h):** Notify affected tenant(s) per DPA
5. **Post-incident:** Mandatory post-mortem within 24 hours

---

## SLO 5: Data Ingestion Throughput

### Specification

- **SLI:** Number of documents successfully ingested per hour on L1.
- **SLO:** Minimum 10,000 documents/hour sustained over a 24-hour window.
- **SLA:** 5,000 documents/hour — minimum guaranteed for basic tier.
- **Error Budget:** Throughput may drop below target for up to 1% of 1-hour windows over 30 days.
  - For 720 hourly windows in 30 days: **~7 hours of degraded throughput allowed**.

### Rationale

Ingestion throughput determines how quickly customers can onboard documents. The 10,000 docs/hour target supports batch imports from enterprise customers while leaving headroom for real-time crawling.

### Error Budget Calculation

```
Target = 10,000 docs/hour
Error Budget = 1% of hourly windows may be below target

For 30 days:
  Total windows = 30 × 24 = 720
  Allowed failures = 0.01 × 720 = ~7 windows

Burn Rate = actual_failures / (allowed_failures / days_elapsed)

Example: If throughput drops below target for 3 hours on day 1:
  Burn Rate = 3 / (7/30) = 3 / 0.23 = ~13x (CRITICAL)
```

### Measurement (PromQL)

```promql
# SLI: Documents ingested per hour (rate over 1h)
sum(rate(documents_ingested_total[1h])) * 3600

# Ratio of hours meeting target over 24h
(
  count_over_time(
    (sum(rate(documents_ingested_total[1h])) * 3600 >= 10000)[24h:1h]
  )
  /
  24
)

# Burn rate: hours below target over 6h vs allowed
(
  count_over_time(
    (sum(rate(documents_ingested_total[1h])) * 3600 < 10000)[6h:1h]
  )
  /
  (0.01 * 6)
)
```

### Recording Rule

See `recording-rules.yml`: `record: slo:ingestion_throughput:docs_per_hour_1d`

### Grafana Panel JSON

```json
{
  "id": 105,
  "title": "SLO-5: Ingestion Throughput (24h)",
  "type": "timeseries",
  "targets": [
    {
      "expr": "slo:ingestion_throughput:docs_per_hour_1d",
      "legendFormat": "Docs/hour",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "docs",
      "min": 0,
      "max": 20000,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 5000},
          {"color": "green", "value": 10000}
        ]
      },
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 15,
        "gradientMode": "scheme",
        "axisLabel": "Documents / hour"
      }
    }
  },
  "options": {
    "legend": {"displayMode": "list", "placement": "bottom"},
    "tooltip": {"mode": "single"}
  },
  "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
}
```

### Burn Rate Alerts

| Burn Rate | Alert Window | Long Window | Action |
|-----------|-------------|-------------|--------|
| 14.4x | 5m | 1h | Page on-call SRE |
| 2x | 15m | 6h | Slack notification |

---

## SLO 6: Frontend LCP

### Specification

- **SLI:** 75th percentile of Largest Contentful Paint (LCP) measurements from real user monitoring (RUM).
- **SLO:** p75 LCP < 2.5 seconds over a 7-day rolling window.
- **SLA:** p75 < 4.0 seconds — customer-facing commitment.
- **Error Budget:** 25% of page loads may exceed 2.5s over 7 days.
  - Based on Core Web Vitals "Good" threshold classification.

### Rationale

LCP is a Google Core Web Vital and directly impacts SEO ranking and user satisfaction. The 2.5s target aligns with Google's "Good" rating. Measurements come from the React frontend via the Web Vitals library.

### Error Budget Calculation

```
Target = p75 LCP < 2.5s
Error Budget = 25% of page loads may have LCP > 2.5s

Burn Rate = (fraction_of_slow_lcp_1h) / 0.25

Example: If 40% of page loads have LCP > 2.5s over 1h:
  Burn Rate = 0.40 / 0.25 = 1.6x
```

### Measurement (PromQL)

```promql
# SLI: p75 LCP over 7d (from web vitals histogram)
histogram_quantile(0.75,
  sum(rate(frontend_web_vitals_lcp_bucket[7d])) by (le)
)

# Fraction of "good" LCP (< 2.5s) over 7d
sum(rate(frontend_web_vitals_lcp_bucket{le="2.5"}[7d]))
/
sum(rate(frontend_web_vitals_lcp_count[7d]))

# Burn rate: fraction of slow LCP over 1h
(
  sum(rate(frontend_web_vitals_lcp_bucket{le="2.5"}[1h]))
  /
  sum(rate(frontend_web_vitals_lcp_count[1h]))
) / 0.75
```

### Recording Rule

See `recording-rules.yml`: `record: slo:frontend_lcp:p75_7d`

### Grafana Panel JSON

```json
{
  "id": 106,
  "title": "SLO-6: Frontend LCP p75 (7d)",
  "type": "gauge",
  "targets": [
    {
      "expr": "slo:frontend_lcp:p75_7d",
      "legendFormat": "LCP p75 (s)",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "s",
      "min": 0,
      "max": 5,
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "green", "value": null},
          {"color": "yellow", "value": 2.5},
          {"color": "red", "value": 4.0}
        ]
      }
    }
  },
  "options": {
    "showThresholdLabels": true,
    "showThresholdMarkers": true,
    "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false}
  },
  "gridPos": {"h": 4, "w": 8, "x": 8, "y": 4}
}
```

### Burn Rate Alerts

| Burn Rate | Alert Window | Long Window | Action |
|-----------|-------------|-------------|--------|
| 6x | 2m | 1h | Page frontend on-call |
| 1x | 5m | 6h | Slack notification |

---

## Error Budget Policy

### Budget Consumption Thresholds

| Budget Consumed | Time Remaining | Action |
|-----------------|----------------|--------|
| 2% | 98% of window | None — normal operation |
| 25% | 75% of window | Team notification in standup |
| 50% | 50% of window | Pause non-critical releases |
| 75% | 25% of window | Freeze all releases, escalate to VP Eng |
| 100% | 0% | **Full release freeze** until window resets; incident review required |

### Release Freeze Procedure

1. **Detection:** Automated alert when error budget reaches 100%
2. **Communication:** Post in #incidents Slack channel; notify Engineering Lead
3. **Enforcement:**
   - Block merges to `main` via GitHub branch protection
   - Cancel all pending CI/CD pipelines
   - Emergency hotfixes require VP Eng approval
4. **Reset:** Budget resets at the end of the compliance window
5. **Post-reset:** 24-hour monitoring period before lifting freeze

### Escalation Path

```
Burn Rate Alert
    │
    ├── Fast Burn (14.4x) ──► Page On-Call SRE ──► 15 min no ack ──► Page SRE Lead
    │                                                30 min no ack ──► Page Engineering Director
    │
    └── Slow Burn (2x) ──► Slack #alerts ──► 1h sustained ──► Create P1 ticket
```

---

## Burn Rate Alerting Reference

### Burn Rate Formula

```
Burn Rate = (Error Rate over Short Window) / (SLO Threshold)

Fast Burn Alert (14.4x):
  Short Window = 1h (or 5m for critical SLOs)
  Long Window  = 1h
  Consumes 2% of budget in 1 hour → would exhaust budget in 50 hours

Slow Burn Alert (2x):
  Short Window = 6h
  Long Window  = 3d
  Consumes 100% of budget over the full window
```

### Alert Rule Template

```yaml
groups:
  - name: slo-burn-rate
    rules:
      # --- Fast Burn: 14.4x ---------------------------------------------
      - alert: SLOBurnRateFast
        expr: |
          (
            slo:api_availability:ratio_1h < (1 - 0.001 * 14.4)
          and
            slo:api_availability:ratio_5m < (1 - 0.001 * 14.4)
          )
        for: 2m
        labels:
          severity: critical
          team: sre
          slo: api-availability
        annotations:
          summary: "Fast burn on API Availability SLO (14.4x)"
          description: "Error budget will exhaust in ~50 hours at current rate"
          runbook_url: "https://github.com/bmsull560/Fabric_4L/blob/main/ops/runbooks/SLO_BURN_RATE.md"

      # --- Slow Burn: 2x ------------------------------------------------
      - alert: SLOBurnRateSlow
        expr: |
          (
            slo:api_availability:ratio_6h < (1 - 0.001 * 2)
          and
            slo:api_availability:ratio_3d < (1 - 0.001 * 2)
          )
        for: 5m
        labels:
          severity: warning
          team: sre
          slo: api-availability
        annotations:
          summary: "Slow burn on API Availability SLO (2x)"
          description: "Error budget trending toward exhaustion"
          runbook_url: "https://github.com/bmsull560/Fabric_4L/blob/main/ops/runbooks/SLO_BURN_RATE.md"
```

---

## Dashboard Integration

All SLO panels are integrated into the `platform-overview.json` dashboard (see D3.3).
The dashboard follows the RED method with a dedicated **SLO Compliance** row
containing gauge panels for each of the 6 SLOs.

### Dashboard Tags

| Tag | Purpose |
|-----|---------|
| `slo` | Marks SLO-related panels |
| `critical` | Marks SLOs with 0% error budget |
| `burn-rate` | Marks burn rate trend panels |

### Alert Routing

```yaml
# alertmanager.yml route snippet
route:
  group_by: [alertname, slo]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        slo: tenant-isolation
      receiver: security-oncall
      group_wait: 0s
      repeat_interval: 5m
    - match:
        severity: critical
      receiver: sre-oncall
      group_wait: 30s
    - match:
        severity: warning
      receiver: team-slack
      group_wait: 5m
```

---

## Appendix: Metric Naming Convention

All SLO-related metrics follow this naming convention:

```
slo:{sl_name}:{aggregation}:{window}

Examples:
  slo:api_availability:ratio_30d
  slo:api_latency:p95_7d
  slo:agent_workflow_success:ratio_7d
  slo:tenant_isolation:breach_rate_1m
  slo:ingestion_throughput:docs_per_hour_1d
  slo:frontend_lcp:p75_7d
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2024-03-01 | SRE Team | Initial SLO definitions |
| 1.1.0 | 2024-05-15 | SRE Team | Added burn rate alerts, LCP SLO |
| 1.2.0 | 2024-06-15 | SRE Team | Production-ready with full Grafana JSON, recording rules |
