# RFC-002: Add journey_id to L4 AgentStreamRequest and AgentGovernanceMetadata

**Status:** Pending Council Review  
**Author:** Frontend Engineering  
**Date:** 2026-08-27  
**Layer:** L4 Agents  
**Council Reviewers:** Backend Engineering, Platform/Security  
**Tracking:** Issue #1387 · Implementation PR #1385

---

## 1. Summary

Add an optional `journey_id` field to the L4 `AgentStreamRequest` and `AgentGovernanceMetadata`
contract surfaces. This is a non-breaking, additive change that enables journey-level
observability and traceability across the ValuePilot conversation pipeline (Intelligence →
Value Studio → Narrative).

## 2. Motivation

The Core ValuePilot journey is currently scored 5.0/8.0. One key gap is the absence of a stable
journey identifier linking all turns, tabs, and sessions for a single account across the pipeline.
Without `journey_id`:

- **Audit events cannot be grouped by journey** — only by tenant or session. This makes it
  impossible to reconstruct the full account progression timeline from telemetry alone.
- **Replayability and determinism work** (roadmap step 4) has no stable key to anchor deterministic
  replays across turns and sessions.
- **The self-improvement loop into L5** (roadmap step 5) cannot correlate downstream outcomes (e.g.
  validated evidence, business-case quality) back to the originating journey.

A stable journey identifier is the foundation for all three of these capabilities.

## 3. Proposed Changes

### Contract surfaces affected

Two schemas in `contracts/openapi/layer4-agents.json` gain an optional field:

| Schema | Field | Wire alias | Type |
|---|---|---|---|
| `AgentStreamRequest` | `journey_id` | `journeyId` | `string \| null`, optional |
| `AgentGovernanceMetadata` | `journey_id` | — | `string \| null`, optional |

### Before

```json
{
  "AgentStreamRequest": {
    "properties": {
      "messages": { "type": "array", "items": { "$ref": "#/components/schemas/AgentStreamMessage" }, "minItems": 1 },
      "activeTab": { "type": "string", "minLength": 1 },
      "account": { "anyOf": [{ "$ref": "#/components/schemas/AgentStreamAccountContext" }, { "type": "null" }] }
    },
    "required": ["messages", "activeTab"]
  }
}
```

```json
{
  "AgentGovernanceMetadata": {
    "properties": {
      "trace_id": { "type": "string" },
      "workflow_id": { "type": "string" },
      "tenant_id": { "type": "string" },
      "tool_name": { "type": "string" },
      "audit_event_id": { "type": "string" },
      "emitted_at": { "type": "string" }
    }
  }
}
```

### After

```json
{
  "AgentStreamRequest": {
    "properties": {
      "messages": { "type": "array", "items": { "$ref": "#/components/schemas/AgentStreamMessage" }, "minItems": 1 },
      "activeTab": { "type": "string", "minLength": 1 },
      "account": { "anyOf": [{ "$ref": "#/components/schemas/AgentStreamAccountContext" }, { "type": "null" }] },
      "journeyId": {
        "anyOf": [{ "type": "string" }, { "type": "null" }],
        "title": "Journeyid"
      }
    },
    "required": ["messages", "activeTab"]
  }
}
```

```json
{
  "AgentGovernanceMetadata": {
    "properties": {
      "trace_id": { "type": "string" },
      "workflow_id": { "type": "string" },
      "tenant_id": { "type": "string" },
      "tool_name": { "type": "string" },
      "audit_event_id": { "type": "string" },
      "emitted_at": { "type": "string" },
      "journey_id": {
        "anyOf": [{ "type": "string" }, { "type": "null" }],
        "title": "Journey Id"
      }
    }
  }
}
```

### Behavior

- `journey_id` is **optional**. Callers that do not send it continue to work; the service derives
  one deterministically.
- An **explicit caller-provided `journey_id` takes precedence**. A whitespace-only value is treated
  as absent and the deterministic derivation is used instead.
- When absent, `journey_id` is **derived as a stable `uuid5`** from `(tenant_id, account_id)`:
  - `uuid5(JOURNEY_NAMESPACE, f"{tenant_id}:{account_id}")` when an account is selected.
  - `uuid5(JOURNEY_NAMESPACE, f"{tenant_id}:no-account")` when no account is selected, so unscoped
    turns still carry a non-null journey link.
- **Tenant-safe by construction:** different tenants with the same `account_id` derive different
  `journey_id` values, preserving tenant isolation.

The derivation lives in `services/layer4-agents/src/layer4_agents/services/conversation.py`
(`_resolve_journey_id`). The field is threaded through the `AgentStreamRequest` model in
`services/layer4-agents/src/layer4_agents/api/routes/agent_stream.py` and surfaced to the
`AgentGovernanceMetadata` response.

## 4. Breaking Change Assessment

- [x] **Non-breaking:** The new field is additive and optional on both surfaces.
  - No existing field is removed or renamed.
  - Existing clients that do not send `journey_id` continue to work — the server derives it.
  - No version bump required: the response shape is unchanged except for the new optional field.

### OpenAPI / Generated Client Updates (Additive)

- `contracts/openapi/layer4-agents.json` — regenerated (additive field).
- `apps/web/src/api/generated/l4/index.ts` — regenerated (additive field).
- `packages/platform-contract/src/typescript/generated/layer4_agents.ts` — regenerated (additive
  field).
- `sdk/python/src/valuefabric/generated/l4/__init__.py` — regenerated (additive field).

No backend service, repository, or migration change is required.

## 5. Security & Governance Impact

- [ ] Exposes new data fields — **No.** The response already surfaces tenant/account/trace context;
      `journey_id` is a derived, non-PII identifier.
- [ ] Changes authentication/authorization requirements — **No.** Same tenant-scoped governance
      middleware applies unchanged.
- [x] Modifies tenant scoping — **No.** `journey_id` derivation is tenant-scoped by construction:
      `uuid5(tenant_id, account_id)` means two tenants with the same `account_id` can never share a
      journey identifier. An explicit caller-provided value is accepted as-is (the caller owns it),
      but the default path is tenant-isolated.

## 6. Alternatives Considered

**Alternative A: Session-scoped id only.** Sessions are per-tab and do not link account progression
across workspaces (Intelligence → Value Studio → Narrative). Rejected — insufficient for
journey-level traceability.

**Alternative B: Use `account_id` directly as the grouping key.** Not tenant-safe if used alone
(the same account could be referenced across tenants). Rejected — `uuid5(tenant_id, account_id)`
is tenant-scoped by construction while still deterministic.

---

## Council Decision

**Status: Pending council review.** The Contract Council decision for this RFC will be recorded
here when review concludes on issue #1387. At least two approving reviews (from different domains)
are required before the corresponding implementation PR (#1385) may be merged.