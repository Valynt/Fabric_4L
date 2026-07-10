# Kill Switch Framework Specification

> **Version:** 1.2.0  
> **Status:** Production  
> **Last Updated:** 2024-01-15

---

## 1. Overview

A **kill switch** is an emergency feature flag that **immediately and globally disables** a feature for all tenants, bypassing all normal evaluation rules (default values, percentage rollouts, tenant targeting).

Kill switches exist for **incident response**: when a deployed feature causes outages, data corruption, performance degradation, or security vulnerabilities, the on-call engineer can activate its kill switch and the feature will be disabled within seconds across all 6 backend layers and the frontend.

---

## 2. Design Principles

| Principle | Description |
|-----------|-------------|
| **Instant effect** | Arming a kill switch takes effect in < 5 seconds globally. |
| **Mandatory TTL** | All kill switches auto-expire after 4 hours (configurable up to 24h). No permanent kills. |
| **Fail-safe** | When a kill switch is armed, the feature returns the **safest possible state** (disabled / degraded). |
| **Observable** | Every activation triggers a PagerDuty alert and is recorded in the audit log. |
| **Simple** | One command to arm, one command to disarm. No complex rule evaluation. |
| **Tenant-agnostic** | Kill switches apply globally — they do not discriminate by tenant. |

---

## 3. Activation Flow

```
On-call engineer → Admin UI / curl → FastAPI POST /feature-flags/{key}/kill
                                      ↓
                              Redis SETEX (TTL = 4h)
                                      ↓
                         PagerDuty alert fired (async)
                                      ↓
                         Audit log entry written
                                      ↓
                    All services see killed=true on next check (< 5s)
```

### Auto-expiry flow

```
Redis TTL expires → kill switch disarmed automatically
                                      ↓
                         Audit log entry: "kill_switch_expired"
                                      ↓
                    Services resume normal flag evaluation
```

---

## 4. Runtime Behaviour

### 4.1 Evaluation priority

When a service evaluates a feature flag, the kill switch is checked **first** — before any other rule:

```
1. Kill switch armed?  → return False (feature disabled)
2. Tenant override?    → evaluate override
3. Flag rules?         → first-match evaluation
4. Default value       → return flag.default_value
```

### 4.2 Service-side check (Python)

```python
from value_fabric.shared.kill_switches import KillSwitch

ks = KillSwitch("layer4-workflow-execution")
if ks.is_killed():
    # Feature is disabled — return graceful degradation
    logger.warning("Kill switch active for workflow execution")
    return WorkflowResponse(
        status="degraded",
        message="This feature is temporarily disabled due to an ongoing incident. "
                "Please try again later or contact support.",
    )

# Normal feature execution
return _execute_workflow(payload)
```

### 4.3 Frontend check (React)

```tsx
import { useKillSwitch } from "@fabric_4l/feature-flags";

function WorkflowRunner() {
  const killed = useKillSwitch("layer4-workflow-execution");

  if (killed) {
    return (
      <DegradedBanner
        title="Feature Temporarily Unavailable"
        message="We're working to resolve an issue. Please try again later."
      />
    );
  }

  return <WorkflowEngine />;
}
```

### 4.4 Graceful degradation patterns

| Service Layer | Feature Example | Kill Switch Behaviour |
|--------------|-----------------|----------------------|
| L1 (Ingestion) | New parser v2 | Return HTTP 503 with `Retry-After: 300` |
| L2 (Processing) | Parallel transforms | Fall back to sequential processing |
| L3 (Orchestration) | DAG optimizer | Skip optimization, run linear plan |
| L4 (Execution) | Parallel workflows | Run workflows sequentially |
| L5 (Analytics) | Real-time aggregations | Return cached / stale results |
| L6 (API Gateway) | New GraphQL schema | Fall back to REST endpoints |
| Frontend | New dashboard UI | Render previous version |

---

## 5. API Specification

### 5.1 Arm kill switch

```http
POST /api/v1/admin/feature-flags/{flag_key}/kill
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "reason": "Memory leak in L4 parallel execution causing OOMKills",
  "duration_seconds": 14400
}
```

**Response 200 OK:**
```json
{
  "flag_key": "layer4-workflow-execution",
  "killed": true,
  "armed_at": "2024-01-15T14:23:00Z",
  "expires_at": "2024-01-15T18:23:00Z",
  "reason": "Memory leak in L4 parallel execution causing OOMKills"
}
```

**Validation:**
- `reason`: minimum 5 characters, maximum 500.
- `duration_seconds`: defaults to 14,400 (4h), maximum 86,400 (24h).

### 5.2 Check kill switch status

```http
GET /api/v1/admin/feature-flags/{flag_key}/kill
Authorization: Bearer <admin-token>
```

**Response (armed):**
```json
{
  "flag_key": "layer4-workflow-execution",
  "killed": true,
  "armed_at": "2024-01-15T14:23:00Z",
  "reason": "Memory leak in L4 parallel execution causing OOMKills"
}
```

**Response (disarmed):**
```json
{
  "flag_key": "layer4-workflow-execution",
  "killed": false
}
```

### 5.3 Disarm kill switch

```http
DELETE /api/v1/admin/feature-flags/{flag_key}/kill
Authorization: Bearer <admin-token>
```

**Response 200 OK:**
```json
{
  "flag_key": "layer4-workflow-execution",
  "killed": false
}
```

---

## 6. TTL and Expiration

### 6.1 Default TTL

- **Default:** 4 hours (14,400 seconds)
- **Minimum:** 60 seconds
- **Maximum:** 24 hours (86,400 seconds)

### 6.2 Why mandatory TTL?

1. **Prevents shadow disables** — a kill switch left on indefinitely becomes an invisible feature toggle.
2. **Forces incident follow-up** — the TTL expiry is a reminder to either fix the root cause or formally disable the feature.
3. **Reduces blast radius** — if the wrong kill switch is activated, it automatically recovers.

### 6.3 Expiry handling

When Redis TTL expires:
1. `is_killed()` returns `False` on next check.
2. Normal flag evaluation resumes.
3. An audit log entry is written with action `kill_switch_expired`.
4. If the incident is not resolved, the on-call engineer must **re-arm** the kill switch.

---

## 7. Alerting

### 7.1 PagerDuty integration

Every kill switch activation triggers a PagerDuty event:

| Field | Value |
|-------|-------|
| Severity | `critical` |
| Source | `fabric-kill-switches` |
| Component | The `flag_key` |
| Deduplication | Per flag key per calendar day |
| Custom details | `flag_key`, `reason`, `actor_id`, `duration_seconds` |

### 7.2 Alert routing

```
PagerDuty → High-urgency escalation policy
    → Page on-call engineer (2-minute ack timeout)
    → Escalate to team lead (5-minute timeout)
    → Escalate to engineering manager (10-minute timeout)
```

### 7.3 Runbook link

Every PagerDuty alert includes a deep link to the incident runbook:
`https://wiki.fabric-4l.io/runbooks/kill-switch-activation`

---

## 8. Audit Trail

Every kill switch event is recorded in `feature_flag_audit_log`:

| Action | When |
|--------|------|
| `kill_switch_activated` | When POST /kill succeeds |
| `kill_switch_expired` | When Redis TTL expires (or manual DELETE) |

Example audit entries:

```json
{
  "id": 1042,
  "flag_key": "layer4-workflow-execution",
  "actor": "user:oncall-engineer-42",
  "action": "kill_switch_activated",
  "new_value": {
    "reason": "Memory leak in L4 parallel execution causing OOMKills",
    "duration_seconds": 14400,
    "expires_at": "2024-01-15T18:23:00Z"
  },
  "timestamp": "2024-01-15T14:23:00Z"
}
```

---

## 9. Security

### 9.1 Authorization

- Kill switch endpoints require **admin role**.
- The `actor` field in audit logs is non-repudiable (derived from auth token).
- All endpoints are behind the admin API gateway with rate limiting (10 req/min).

### 9.2 Rate limiting

| Endpoint | Limit |
|----------|-------|
| POST /kill | 10 per minute per admin |
| DELETE /kill | 20 per minute per admin |
| GET /kill | 60 per minute per admin |

### 9.3 Blast radius containment

- Kill switches are **global** — they affect all tenants.
- This is intentional: the scenarios requiring kill switches (security vulnerabilities, data corruption) are not tenant-specific.
- For tenant-scoped disables, use **regular flag overrides** (not kill switches).

---

## 10. Operational Guidelines

### 10.1 When to activate a kill switch

✅ **Activate when:**
- A feature is causing production incidents (outages, errors, data loss).
- A security vulnerability is discovered in a feature.
- A feature is causing cascading failures across layers.

❌ **Do NOT activate when:**
- A feature is merely unpopular — use regular flag disable.
- A single tenant is affected — use tenant-scoped override.
- A feature needs gradual rollback — use percentage rollout.

### 10.2 Post-activation checklist

1. [ ] Verify kill switch is active (check GET /kill).
2. [ ] Confirm incident metrics are improving (error rate, latency).
3. [ ] Page the feature team via PagerDuty (auto-done).
4. [ ] Create a Jira ticket for root cause analysis.
5. [ ] Set a calendar reminder for TTL expiry.
6. [ ] After fix deployed, manually disarm or let TTL expire.
7. [ ] Verify feature works correctly after disarm.

### 10.3 Metrics

Prometheus metrics exposed by the kill switch module:

```
fabric_kill_switch_activations_total{flag_key="..."}  # counter
fabric_kill_switch_active{flag_key="..."}              # gauge (0/1)
fabric_kill_switch_check_duration_seconds              # histogram
```

---

## 11. Implementation Details

### 11.1 Redis data model

```
Key:    ff:v1:kill:{flag_key}
Value:  {armed_at_iso}|{reason}|{actor_id}
TTL:    14400 (default) or user-specified
```

### 11.2 Local caching strategy

Services use a 5-second in-process LRU cache to avoid repeated Redis round-trips:

```
Service process
  └── LRU cache (5s TTL)
       └── Redis GET ff:v1:kill:{flag_key}
```

This means worst-case delay from arm to global effect is **5 seconds**.

### 11.3 Health check

Each service exposes a kill switch health endpoint:

```python
from value_fabric.shared.kill_switches import validate_kill_switch_health

@router.get("/health/kill-switches")
async def kill_switch_health():
    return await validate_kill_switch_health()
```

Expected response:
```json
{"status": "ok", "redis": "connected"}
```

---

## 12. Testing

### 12.1 Unit tests

```python
import pytest
from value_fabric.shared.kill_switches import KillSwitch

@pytest.mark.asyncio
async def test_kill_switch_arms_and_disarms():
    redis = FakeRedis()
    KillSwitch.configure(redis)

    ks = KillSwitch("test-feature")
    assert not ks.is_killed()

    await KillSwitch.arm("test-feature", "test incident", "tester-1", duration_seconds=60)
    assert ks.is_killed()

    await KillSwitch.disarm("test-feature", "tester-1")
    assert not ks.is_killed()
```

### 12.2 Integration tests

```python
@pytest.mark.asyncio
async def test_kill_switch_api_endpoint(client, admin_token):
    # Arm
    resp = await client.post(
        "/api/v1/admin/feature-flags/test-feature/kill",
        json={"reason": "integration test", "duration_seconds": 60},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["killed"] is True

    # Check
    resp = await client.get(
        "/api/v1/admin/feature-flags/test-feature/kill",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.json()["killed"] is True

    # Disarm
    resp = await client.delete(
        "/api/v1/admin/feature-flags/test-feature/kill",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.json()["killed"] is False
```

---

## Appendix A: Quick Reference Card

```
ARM:    POST /api/v1/admin/feature-flags/{key}/kill
        Body: {"reason": "...", "duration_seconds": 14400}

CHECK:  GET  /api/v1/admin/feature-flags/{key}/kill

DISARM: DELETE /api/v1/admin/feature-flags/{key}/kill

CODE:   ks = KillSwitch("flag-key")
        if ks.is_killed(): return degraded()
```

---

*End of specification.*
