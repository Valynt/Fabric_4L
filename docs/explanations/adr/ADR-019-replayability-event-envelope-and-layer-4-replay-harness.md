# ADR-019: Replayability Event Envelope and Layer 4 Replay Harness

- **Status:** Accepted
- **Date:** 2026-05-12
- **Owners:** Platform Architecture / Layer 4 / Layer 5

## Context

Value Fabric requires deterministic replay for incident analysis, regression verification, and auditability without weakening tenant isolation or exposing sensitive payloads. Existing workflow event streaming focuses on client progress updates; it does not define a platform-wide immutable replay envelope with explicit schema-versioning and retention boundaries.

## Decision

### 1) Replayable domains

The following domains are replayable, with a domain marker in the immutable envelope:

- `layer4.workflow_state` — workflow lifecycle/state transitions (`created`, `started`, `node_transition`, `paused`, `resumed`, `failed`, `completed`).
- `layer4.business_object` — key Layer 4 business object mutations (e.g., case lifecycle state changes) that influence agent orchestration decisions.
- `layer4.integration_callback` — external integration callbacks received by Layer 4 that alter workflow progression.
- `layer5.truth_object` — Layer 5 truth-object validation events that can be correlated with Layer 4 decisions.

### 2) Immutable event envelope schema

Replay events MUST conform to `contracts/jsonschema/layer4-workflow-replay-event-envelope-v1.schema.json`.

Required fields:

- `event_id` (immutable unique ID)
- `tenant_id` (authoritative tenant scope)
- `actor` (system/user principal)
- `timestamp` (RFC3339 UTC timestamp)
- `correlation_id` (cross-layer trace/correlation key)
- `schema_version` (currently `1.x`)
- `domain` (replayable domain identifier)
- `event_type` (domain-specific event name)
- `payload_pointer` (immutable pointer to redacted payload object)
- `payload_checksum` (checksum for payload integrity verification)
- `payload_redacted` (deterministic, non-secret replay projection)

Envelope records are append-only and must not be mutated in-place.

### 3) Storage, retention, authorization, and audit boundaries

- **Layer 4:**
  - Stores immutable replay envelope stream for workflow-state and integration-callback domains.
  - Retains full replay stream per policy tier (minimum 90 days online for operational replay), then transitions to cold archive where configured.
- **Layer 5:**
  - Stores immutable replay envelope stream for truth-object mutation/validation domain.
  - Retains online stream for validation audit windows (minimum 180 days), with archive per governance policy.
- **Cross-layer boundary:**
  - `correlation_id` links Layer 4 and Layer 5 replay chains.
  - Raw sensitive payloads remain in controlled stores; replay envelope only stores redacted projection + pointer + checksum.
- **Replay job authorization:**
  - Replay execution is restricted to non-production environments (`local`, `dev`, `test`, `staging`, `non-production`).
  - Caller must hold `replay:execute` role and tenant match must be enforced per event.
- **Replay job auditability:**
  - Every replay invocation emits an auditable record containing tenant, actor, workflow ID/type, ticket/reference, and applied event IDs.

### 4) Initial implementation boundary

Initial harness implementation is provided at Layer 4 service boundary:

- `services/layer4-agents/src/layer4_agents/workflows/replay.py`

It replays `layer4.workflow_state` events into `BaseAgentState` deterministically for non-production use.
The harness now exposes a repository interface boundary (`ReplayEventStream`) via
`replay_from_stream(...)` so service adapters can provide immutable event streams
without coupling replay logic to one storage backend.

### Storage / retention boundary matrix

| Layer | Replayable domains | Primary retention boundary | Archive boundary |
| --- | --- | --- | --- |
| Layer 1 | `layer1.ingestion_job` (future) | 30-day hot retention for operational debugging | Cold archive per compliance profile |
| Layer 2 | `layer2.extraction_batch` (future) | 60-day hot retention for extraction incident replay | Cold archive with provenance chain |
| Layer 3 | `layer3.graph_mutation` (future) | 90-day hot retention for index/graph forensic replay | Cold archive with graph snapshot references |
| Layer 4 | `layer4.workflow_state`, `layer4.business_object`, `layer4.integration_callback` | **Minimum 90-day hot retention** for operational replay | Cold archive with pointer/checksum integrity |
| Layer 5 | `layer5.truth_object` | **Minimum 180-day hot retention** for audit validation windows | Cold archive for governance hold requirements |
| Layer 6 | `layer6.benchmark_run` (future) | 90-day hot retention for benchmark replayability | Cold archive by dataset lineage policy |

### 5) Compatibility and deterministic replay testing

Contract and behavior tests enforce:

- Event envelope schema version remains backward compatible (`1.x` pattern, required immutable fields preserved).
- Replay of historical event streams remains deterministic (same inputs produce identical terminal state and event application order).

## Consequences

### Positive

- Deterministic replay for workflow debugging and audit verification.
- Contract-first, tenant-scoped envelope that is cross-layer correlatable.
- Reduced risk of payload leakage by using redacted projections and pointer/checksum semantics.

### Trade-offs

- Additional operational burden for event retention and archive policies.
- Replay remains intentionally scoped to non-production execution, requiring controlled promotion paths for forensic needs.

## Follow-up

1. Implement persistent event-stream repository abstraction for Layer 4 and Layer 5 storage backends.
2. Expose admin-only replay orchestration endpoint behind governance middleware.
3. Add runbook entry for replay incident workflow and retention controls.
