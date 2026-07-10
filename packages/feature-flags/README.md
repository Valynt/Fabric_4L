# @fabric_4l/feature-flags

> **Version:** 1.2.0  
> **License:** MIT  
> **Status:** Production

Production-grade, tenant-scoped feature flag SDK for Fabric_4L. Supports boolean flags, percentage rollouts, tier-based targeting, kill switches, and experimentation telemetry.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [React Hook](#react-hook)
4. [Backend (Python)](#backend-python)
5. [Evaluation Rules](#evaluation-rules)
6. [Kill Switches](#kill-switches)
7. [Telemetry](#telemetry)
8. [Architecture](#architecture)
9. [Configuration](#configuration)
10. [Troubleshooting](#troubleshooting)

---

## Installation

```bash
# npm / pnpm / yarn
npm install @fabric_4l/feature-flags

# Backend Python (available as part of the monorepo)
from fabric_feature_flags import is_enabled
```

---

## Quick Start

### 1. Bootstrap the SDK

Call `bootstrapFlags` once at app entry (e.g. `main.tsx`):

```tsx
import { bootstrapFlags, setEvaluationContext } from "@fabric_4l/feature-flags";

// After auth resolves:
setEvaluationContext({
  tenantId:   "tenant-42",
  tenantTier: "enterprise",
  userId:     "user-123",
  userSegments: ["beta", "internal"],
});

// Start polling (30s default interval)
const stopPolling = bootstrapFlags({
  apiBaseUrl: "https://api.fabric-4l.io",
  apiKey:     process.env.REACT_APP_FF_API_KEY,
});

// On logout / unmount:
// stopPolling();
```

### 2. Consume flags in components

```tsx
import { useFeatureFlag } from "@fabric_4l/feature-flags";

function Dashboard() {
  const showV2 = useFeatureFlag("new-dashboard-v2", { defaultValue: false });

  return showV2 ? <DashboardV2 /> : <DashboardV1 />;
}
```

---

## React Hook

### `useFeatureFlag(flagKey, options?) => boolean`

| Parameter      | Type     | Required | Default | Description                          |
|----------------|----------|----------|---------|--------------------------------------|
| `flagKey`      | `string` | Yes      | —       | Stable flag identifier (kebab-case)  |
| `options.defaultValue` | `boolean` | No | `false` | Fallback when flag is unknown |

**Fail-safe guarantee:** If the flag is not defined in the admin API, the hook always returns `false` (or the provided `defaultValue`).

**Reactivity:** The hook subscribes to the flag store. When an admin toggles a flag, all mounted components re-render automatically.

---

## Backend (Python)

The Python SDK mirrors the TypeScript semantics so percentage rollouts are consistent across stack layers.

```python
from fabric_feature_flags import is_enabled

# L4 service — workflow execution
def execute_workflow(tenant_id: str, payload: dict):
    if not is_enabled("layer4-parallel-execution", tenant_id=tenant_id):
        return WorkflowResponse(status="degraded", message="Feature disabled")

    return _execute_parallel(payload)
```

### Method signature

```python
def is_enabled(
    flag_key: str,
    *,
    tenant_id: str,
    tenant_tier: str | None = None,
    user_id: str | None = None,
    user_segments: list[str] | None = None,
    default: bool = False,
) -> bool: ...
```

### Caching

The Python SDK caches evaluations in Redis with a 30-second TTL. Hot-path latency: **< 2ms p99**.

---

## Evaluation Rules

Rules are evaluated **top-down, first-match wins**.

### Rule priority

1. **Tenant ID allow-list** — exact match, highest priority
2. **Tenant tier** — `shared | dedicated | enterprise`
3. **User segments** — e.g. `"beta"`, `"internal"`
4. **Percentage rollout** — deterministic hash, consistent per user

### Example configuration

```json
{
  "flagKey": "new-dashboard-v2",
  "defaultValue": false,
  "rules": [
    {
      "tenantIds": ["tenant-42", "tenant-99"],
      "percentage": 50
    },
    {
      "tenantTier": "enterprise",
      "userSegments": ["beta"]
    },
    {
      "tenantTier": "shared",
      "percentage": 10
    }
  ]
}
```

### Deterministic bucketing

Percentage rollouts use FNV-1a hashing on `(flagKey + tenantId + userId)`. This means:

- The same user always sees the **same variation**.
- Adjusting percentage from 10% → 20% adds users without flipping existing ones.

---

## Kill Switches

Kill switches are emergency overrides that **instantly disable** a feature for all tenants, bypassing all rules.

### Characteristics

- **No rule evaluation** — when killed, the feature returns `false` immediately.
- **Mandatory TTL** — auto-expires after 4 hours (max 24h).
- **PagerDuty alert** — every activation triggers a page.
- **Full audit trail** — logged in `feature_flag_audit_log`.

### Usage (Python)

```python
from value_fabric.shared.kill_switches import KillSwitch

ks = KillSwitch("layer4-workflow-execution")
if ks.is_killed():
    logger.warning("Kill switch active for workflow execution")
    return WorkflowResponse(status="degraded", message="Temporarily disabled")
```

### Usage (React)

```tsx
import { useKillSwitch } from "@fabric_4l/feature-flags";

function WorkflowRunner() {
  const killed = useKillSwitch("layer4-workflow-execution");
  if (killed) return <DegradedBanner />;
  return <WorkflowEngine />;
}
```

### Admin API

```bash
# Arm kill switch
POST /api/v1/admin/feature-flags/{flag_key}/kill
Body: { "reason": "Memory leak in L4 pipeline", "duration_seconds": 14400 }

# Check status
GET /api/v1/admin/feature-flags/{flag_key}/kill

# Manual reset
DELETE /api/v1/admin/feature-flags/{flag_key}/kill
```

---

## Telemetry

Flag impressions and experiment conversions are emitted as events.

### Register a telemetry sink

```tsx
import { registerTelemetrySink } from "@fabric_4l/feature-flags";

registerTelemetrySink(async (event) => {
  await fetch("/analytics/ingest", {
    method: "POST",
    body: JSON.stringify(event),
  });
});
```

### Event schemas

#### `flag_impression`

```json
{
  "eventType": "flag_impression",
  "flagKey": "new-dashboard-v2",
  "tenantId": "tenant-42",
  "userId": "u_a3f7d2e1",
  "variation": "enabled",
  "timestamp": "2024-01-15T09:23:00Z",
  "sdkVersion": "1.2.0",
  "source": "rule"
}
```

#### `experiment_conversion`

```json
{
  "eventType": "experiment_conversion",
  "experimentKey": "new-dashboard-v2",
  "tenantId": "tenant-42",
  "userId": "u_a3f7d2e1",
  "goalName": "dashboard_load_time_under_2s",
  "value": 1,
  "timestamp": "2024-01-15T09:25:00Z"
}
```

**Privacy:** User identifiers are hashed with HMAC-SHA256 before emission. No PII leaves the SDK.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React App     │     │  Python L1-L6    │     │   Admin UI      │
│  (useFeatureFlag)│    │  (is_enabled)    │     │  (CRUD page)    │
└────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
         │                       │                        │
         │  ① Bootstrap / Poll   │   ② Redis cache        │
         │◄─────────────────────►│◄──────────────────────►│
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │   FastAPI Admin Router     │
                    │   (api.py)                 │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   PostgreSQL 15            │
                    │   feature_flags.*          │
                    └────────────────────────────┘
```

### Data flow

1. **Bootstrap** — React app fetches all flags on load.
2. **Polling** — Background refresh every 30s.
3. **Evaluation** — Local, synchronous, zero network.
4. **Mutations** — Admin changes flow through FastAPI → PostgreSQL → Redis invalidation.
5. **Kill switch** — Checked first in Redis (< 1ms).

---

## Configuration

| Environment Variable            | Default    | Description                          |
|---------------------------------|------------|--------------------------------------|
| `FEATURE_FLAGS_API_URL`         | —          | Base URL of the admin API            |
| `FEATURE_FLAGS_API_KEY`         | —          | Read-only API key for polling        |
| `FEATURE_FLAGS_POLL_MS`         | `30000`    | Polling interval (ms)                |
| `FEATURE_FLAG_HMAC_SECRET`      | —          | Secret for hashing user identifiers  |
| `FEATURE_FLAGS_CACHE_TTL_S`     | `30`       | Server-side Redis cache TTL          |
| `PAGERDUTY_ROUTING_KEY`         | —          | Routing key for kill-switch alerts   |

---

## Troubleshooting

### Flag changes not reflecting

- Check that `bootstrapFlags()` was called.
- Verify `stopPolling()` was **not** called prematurely.
- Check browser Network tab for `GET /api/v1/admin/feature-flags`.

### All flags returning `false`

- This is the **fail-safe default**. Check:
  1. Flag key spelling (case-sensitive).
  2. Flag exists in the admin API.
  3. `setEvaluationContext()` was called with valid `tenantId`.

### Kill switch not auto-resetting

- Ensure the cron / worker that expires Redis keys is running.
- Max TTL is 24 hours; manual reset may be required.

---

## Changelog

### 1.2.0
- Kill switch framework with PagerDuty integration
- Experimentation telemetry (impressions + conversions)
- Per-tenant isolation with hashed identifiers
- Admin UI page (shadcn/ui)

### 1.1.0
- Percentage rollout support
- Tenant tier targeting
- Audit log

### 1.0.0
- Initial boolean flag support
- React hook + Python SDK
