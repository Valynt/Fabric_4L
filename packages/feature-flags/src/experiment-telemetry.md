# Experimentation Telemetry Specification

> **Version:** 1.2.0  
> **Status:** Production  
> **Applies to:** Feature Flags SDK (TypeScript + Python)

---

## 1. Purpose

This document defines the telemetry schema, collection strategy, and privacy guarantees for A/B testing and experimentation within Fabric_4L's feature flag system.

Goals:
- Enable data-driven feature rollouts through A/B test analysis.
- Ensure **per-tenant experiment isolation** — no cross-tenant contamination.
- Preserve user privacy through **hashed identifiers**.
- Integrate cleanly with existing OpenTelemetry infrastructure.

---

## 2. Flag Impression Events

An **impression** is recorded every time a feature flag is evaluated for a user.

### 2.1 Schema

```json
{
  "eventType": "flag_impression",
  "eventVersion": "1.0",
  "flagKey": "new-dashboard-v2",
  "tenantId": "tenant-42",
  "userId": "u_a3f7d2e1b4c8",
  "variation": "enabled",
  "timestamp": "2024-01-15T09:23:47.123Z",
  "sdkVersion": "1.2.0",
  "source": "rule",
  "sessionId": "sess_8f2e9d1a",
  "metadata": {
    "ruleIndex": 1,
    "percentage": 50,
    "tenantTier": "enterprise"
  }
}
```

### 2.2 Field reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventType` | `string` | Yes | Always `"flag_impression"` |
| `eventVersion` | `string` | Yes | Schema version (e.g. `"1.0"`) |
| `flagKey` | `string` | Yes | The feature flag identifier |
| `tenantId` | `string` | Yes | Tenant scope — used for isolation |
| `userId` | `string` | Yes | **Hashed** user identifier |
| `variation` | `string` | Yes | `"enabled"` or `"disabled"` |
| `timestamp` | `string` | Yes | ISO-8601 with millisecond precision |
| `sdkVersion` | `string` | Yes | SDK version that emitted the event |
| `source` | `string` | Yes | Evaluation source: `default`, `rule`, `override`, `kill_switch` |
| `sessionId` | `string` | No | Frontend session for deduplication |
| `metadata` | `object` | No | Additional evaluation context |

### 2.3 Emission strategy

| Platform | Trigger | Transport | Batching |
|----------|---------|-----------|----------|
| **React (frontend)** | `useFeatureFlag()` evaluates | POST to `/analytics/ingest` | Debounced, 5s flush |
| **Python (backend)** | `is_enabled()` evaluates | Async background queue | 100 events or 10s |

### 2.4 Deduplication

To prevent double-counting when a flag is evaluated multiple times per session:

```
Dedup key: {sessionId}:{flagKey}:{variation}
Window:    5 minutes (frontend), 1 minute (backend)
```

Events with the same dedup key within the window are dropped.

---

## 3. Conversion Tracking

A **conversion** records when a user achieves a goal that is part of an experiment.

### 3.1 Schema

```json
{
  "eventType": "experiment_conversion",
  "eventVersion": "1.0",
  "experimentKey": "new-dashboard-v2",
  "tenantId": "tenant-42",
  "userId": "u_a3f7d2e1b4c8",
  "goalName": "dashboard_load_time_under_2s",
  "value": 1.0,
  "timestamp": "2024-01-15T09:25:12.456Z",
  "sdkVersion": "1.2.0",
  "attributionWindow": "24h",
  "metadata": {
    "flagVariation": "enabled",
    "pagePath": "/dashboard/v2",
    "deviceType": "desktop"
  }
}
```

### 3.2 Field reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `eventType` | `string` | Yes | Always `"experiment_conversion"` |
| `eventVersion` | `string` | Yes | Schema version |
| `experimentKey` | `string` | Yes | Links to the flag being tested |
| `tenantId` | `string` | Yes | Tenant scope |
| `userId` | `string` | Yes | **Hashed** user identifier |
| `goalName` | `string` | Yes | The conversion goal (e.g. `"signup_completed"`) |
| `value` | `number` | No | Numeric value (e.g. revenue, count) |
| `timestamp` | `string` | Yes | ISO-8601 |
| `sdkVersion` | `string` | Yes | SDK version |
| `attributionWindow` | `string` | No | Lookback window for attribution (default `"24h"`) |
| `metadata` | `object` | No | Additional context |

### 3.3 Goal naming convention

```
{category}_{action}_{criteria}

Examples:
  - page_dashboard_loaded_under_2s
  - feature_adopted_within_7d
  - revenue_checkout_completed
  - error_rate_below_0_1_pct
  - retention_d7_returned
```

### 3.4 Attribution model

Fabric_4L uses **last-touch attribution** within a configurable window:

1. When a conversion event is received, look up recent impressions for `(userId, experimentKey)`.
2. If an impression exists within the attribution window (default 24h), attribute the conversion to that variation.
3. If no impression is found, the conversion is **orphaned** and excluded from analysis.

---

## 4. Per-Tenant Experiment Isolation

### 4.1 Problem

In a multi-tenant system, experiment results from one tenant must never leak into another tenant's analysis. Cross-tenant contamination invalidates statistical inference.

### 4.2 Solution

Every telemetry event **MUST** include `tenantId`. All downstream analytics **MUST** partition by `tenantId` before computing:

- Conversion rates
- Lift percentages
- Statistical significance (p-values)

### 4.3 Analytics query pattern

```sql
-- Correct: per-tenant analysis
SELECT
  tenant_id,
  variation,
  COUNT(DISTINCT user_id) AS users,
  COUNT(DISTINCT CASE WHEN converted THEN user_id END) AS converters,
  AVG(CASE WHEN converted THEN value END) AS avg_value
FROM experiment_results
WHERE experiment_key = 'new-dashboard-v2'
GROUP BY tenant_id, variation;

-- WRONG: global aggregation (cross-tenant contamination)
-- SELECT variation, ... FROM experiment_results GROUP BY variation;
```

### 4.4 Tenant-level rollups

Global metrics are computed by **aggregating tenant-level results**, not by aggregating raw events:

```python
# Correct methodology
tenant_results = [analyze_tenant(t) for t in tenants]
global_rate = weighted_average(
    [r.conversion_rate for r in tenant_results],
    weights=[r.user_count for r in tenant_results],
)
```

---

## 5. Privacy-Preserving Analytics

### 5.1 Identifier hashing

All `userId` fields in telemetry events are **hashed before emission**:

```python
import hmac, hashlib, os

SECRET = os.environ["FEATURE_FLAG_HMAC_SECRET"]

def hash_user_id(tenant_id: str, raw_user_id: str) -> str:
    """Deterministic, irreversible hash."""
    message = f"{tenant_id}:{raw_user_id}".encode()
    digest = hmac.new(SECRET.encode(), message, hashlib.sha256).hexdigest()
    return f"u_{digest[:16]}"
```

Properties:
- **Deterministic**: Same input always produces same output (required for attribution).
- **Irreversible**: Without the secret, the original user ID cannot be recovered.
- **Tenant-scoped**: Hash includes `tenantId` to prevent cross-tenant correlation.

### 5.2 What is NOT collected

The following are **never** included in telemetry events:

| Field | Reason |
|-------|--------|
| Raw email address | PII |
| IP address | PII, fingerprinting risk |
| Geolocation | Sensitive |
| Device advertising ID | Tracking risk |
| Full user agent | Fingerprinting risk |

### 5.3 Data retention

| Event Type | Retention | Rationale |
|------------|-----------|-----------|
| Flag impressions | 90 days | Sufficient for experiment analysis |
| Conversion events | 90 days | Sufficient for experiment analysis |
| Aggregated results | 2 years | Long-term trend analysis |

### 5.4 GDPR / CCPA compliance

- Users can request deletion via the tenant admin.
- Deletion is implemented by **removing the HMAC secret slice** for that tenant, which anonymizes all their hashed user IDs.
- No raw user data is stored in the analytics pipeline.

---

## 6. OpenTelemetry Integration

### 6.1 Span attributes

Flag evaluations are annotated on the current OpenTelemetry span:

```python
from opentelemetry import trace

tracer = trace.get_tracer("fabric.feature_flags")

# Inside is_enabled():
span = trace.get_current_span()
span.set_attribute("feature_flag.key", flag_key)
span.set_attribute("feature_flag.enabled", result.enabled)
span.set_attribute("feature_flag.source", result.source)
span.set_attribute("feature_flag.tenant_id", tenant_id)
```

### 6.2 Span events

For significant flag decisions (kill switches, override matches):

```python
span.add_event(
    "feature_flag.evaluated",
    {
        "flag_key": flag_key,
        "enabled": result.enabled,
        "source": result.source,
        "rule_index": result.rule_index or -1,
    },
)
```

### 6.3 Metrics

Prometheus metrics exported by the SDK:

```
# Counter: total evaluations
fabric_feature_flag_evaluations_total{flag_key="...", source="...", variation="..."}

# Counter: kill switch hits
fabric_kill_switch_hits_total{flag_key="..."}

# Histogram: evaluation latency
fabric_feature_flag_eval_duration_seconds_bucket{flag_key="..."}

# Counter: telemetry events emitted
fabric_feature_flag_telemetry_events_total{event_type="..."}
```

### 6.4 Trace sampling

Flag evaluation spans are **low-overhead** (< 1μs) and always recorded. Telemetry event emission spans are sampled at 1% in production to reduce export volume.

---

## 7. Experiment Lifecycle

### 7.1 Phases

```
1. CREATED      → Flag created, default=false, no rules
2. CONFIGURED   → Rules added, percentage rollout set
3. RUNNING      → Flag enabled for test cohort, telemetry flowing
4. ANALYZING    → Experiment ended, data being analyzed
5. DECIDED      → Decision made (ship / rollback)
6. SHIPPED      → Flag default=true, rules removed, cleanup scheduled
7. ARCHIVED     → Flag deleted after 30-day grace period
```

### 7.2 Minimum experiment duration

- **7 days** — to account for weekly seasonality.
- **100 users per variation** — minimum for statistical significance.
- Both conditions must be met before a decision can be made.

### 7.3 Stopping rules

An experiment MUST be stopped early if:

1. **Guardrail metric violated** — error rate increases > 0.5% (relative).
2. **Kill switch activated** — feature is disabled globally.
3. **Sample ratio mismatch** — significant imbalance between variations (p < 0.01).

---

## 8. Data Pipeline

### 8.1 Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  React SDK   │     │ Python SDK   │     │  Admin API   │
│  (impression)│     │ (impression) │     │ (experiment  │
│              │     │  (conversion)│     │   lifecycle) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                ┌───────────▼────────────┐
                │   Kafka (telemetry)    │
                │   topic: ff.events     │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │   ClickHouse           │
                │   (raw events 90d)     │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │   dbt models           │
                │   (per-tenant rollup)  │
                └───────────┬────────────┘
                            │
                ┌───────────▼────────────┐
                │   Grafana / Looker     │
                │   (experiment reports) │
                └────────────────────────┘
```

### 8.2 Kafka topic schema

```yaml
topic: ff.events
partitions: 24  # 1 per tenant shard
replication: 3
retention.ms: 7776000000  # 90 days
compression.type: zstd
```

### 8.3 Event validation

Events are validated against JSON Schema before ingestion:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["eventType", "eventVersion", "flagKey", "tenantId", "userId", "timestamp"],
  "properties": {
    "eventType": { "enum": ["flag_impression", "experiment_conversion"] },
    "eventVersion": { "const": "1.0" },
    "flagKey": { "type": "string", "maxLength": 128 },
    "tenantId": { "type": "string", "maxLength": 64 },
    "userId": { "type": "string", "pattern": "^u_[a-f0-9]{16}$" },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```

---

## 9. SDK Implementation Guide

### 9.1 TypeScript (React)

```tsx
import {
  bootstrapFlags,
  registerTelemetrySink,
  setEvaluationContext,
} from "@fabric_4l/feature-flags";

// Register telemetry sink
registerTelemetrySink(async (event) => {
  // Batch and flush
  telemetryBuffer.push(event);
  if (telemetryBuffer.length >= 10 || flushDue()) {
    await fetch("/analytics/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(telemetryBuffer),
      keepalive: true,
    });
    telemetryBuffer.length = 0;
  }
});

// Track conversions
function trackConversion(goalName: string, value?: number) {
  // Fetch current experiment context from the SDK
  const ctx = getEvaluationContext();
  if (!ctx) return;

  const event: ExperimentConversionEvent = {
    eventType: "experiment_conversion",
    experimentKey: "new-dashboard-v2", // the flag being tested
    tenantId: ctx.tenantId,
    userId: hashUserId(ctx.userId ?? "anonymous"),
    goalName,
    value,
    timestamp: new Date().toISOString(),
  };
  // Emit through the registered sink
  emitTelemetry(event);
}
```

### 9.2 Python

```python
from fabric_feature_flags import is_enabled, record_conversion

# Evaluations automatically emit impressions when telemetry is configured

# Track a conversion
def on_dashboard_loaded(tenant_id: str, user_id: str, load_time_ms: float):
    record_conversion(
        experiment_key="new-dashboard-v2",
        tenant_id=tenant_id,
        user_id=user_id,
        goal_name="dashboard_load_time_under_2s",
        value=1.0 if load_time_ms < 2000 else 0.0,
    )
```

---

## 10. Quality Assurance

### 10.1 Data quality checks

| Check | Threshold | Action on failure |
|-------|-----------|-------------------|
| Impression volume drop > 50% | 15-min window | Page on-call |
| Conversion rate > 100% | Per tenant | Alert data team |
| Orphaned conversion rate > 10% | Daily | Investigate attribution pipeline |
| Duplicate event rate > 5% | Hourly | Check deduplication logic |

### 10.2 A/A testing

Before any experiment goes live, an **A/A test** runs for 7 days:
- Both variations receive the same experience.
- Confirms that the telemetry pipeline reports no significant difference (p > 0.05).
- Validates that randomization and bucketing are working correctly.

---

## Appendix A: Event Schema (TypeScript)

```typescript
interface FlagImpressionEvent {
  eventType: "flag_impression";
  eventVersion: "1.0";
  flagKey: string;
  tenantId: string;
  userId: string;
  variation: "enabled" | "disabled";
  timestamp: string;
  sdkVersion: string;
  source: "default" | "rule" | "override" | "kill_switch";
  sessionId?: string;
  metadata?: Record<string, unknown>;
}

interface ExperimentConversionEvent {
  eventType: "experiment_conversion";
  eventVersion: "1.0";
  experimentKey: string;
  tenantId: string;
  userId: string;
  goalName: string;
  value?: number;
  timestamp: string;
  sdkVersion: string;
  attributionWindow?: string;
  metadata?: Record<string, unknown>;
}
```

---

*End of specification.*
