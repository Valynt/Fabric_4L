# GATE Phase 3 — Memory Gateway & Deterministic Replay

**Status:** Design ready for review  
**Date:** 2026-06-15  
**Scope:** `packages/shared/src/value_fabric/shared/governance/`, `services/layer4-agents/src/layer4_agents/agents/base.py`, `services/layer4-agents/src/layer4_agents/services/conversation.py`, related tests and contracts  

---

## 1. Context

Phase 1 (cryptographic audit ledger) and Phase 2 (ABOM + ToolGateway) of the GATE framework are implemented. Phase 3 scaffolding already exists:

- `packages/shared/src/value_fabric/shared/governance/memory_gateway.py` — provenance-tracked retrieval proxy.
- `packages/shared/src/value_fabric/shared/governance/replay.py` — `ReplayRecorder` that commits a `REPLAY_SNAPSHOT` audit event.
- `services/layer4-agents/src/layer4_agents/agents/base.py` — injects `ToolGateway` and `ReplayRecorder` during `run()` and commits a replay snapshot on success.

The remaining work is to wire `MemoryGateway` into the agent runtime so that **memory accesses are captured in replay snapshots**, and to make the snapshot hash deterministic for post-incident replay.

---

## 2. Goals

1. Every agent run that performs retrieval must do so through a `MemoryGateway`.
2. Every `MemoryGateway` retrieval must emit a `MEMORY_ACCESS` audit record with `content_hash` and `source_lineage`.
3. The `ReplayRecorder` must include both tool invocations **and** memory accesses in the committed snapshot.
4. The snapshot hash must be deterministic for identical inputs (stable across replays).
5. Retrieval-time poisoning control: a lightweight source-ID blocklist must be enforceable inside `MemoryGateway`.
6. All new behavior must be covered by unit/contract tests; existing tests must keep passing.

---

## 3. Non-Goals

- Replacing Layer 3 retrieval engines (`GraphRAGEngine`, `HybridSearch`). `MemoryGateway` wraps them.
- Adding a live OPA dependency. Policy evaluation remains in the `ToolGateway`; memory ACLs use a local blocklist.
- Backfilling old audit events into the replay ledger.
- Adding UI changes for replay visualization.

---

## 4. Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  BaseAgent.run()                                            │
│  ───────────────                                            │
│  1. Loads ABOM                                              │
│  2. Creates ToolGateway from ctx["tool_registry"]           │
│  3. Creates MemoryGateway from ctx["retrieval_engine"]      │
│     (or reuses ctx["memory_gateway"])                       │
│  4. Creates ReplayRecorder                                  │
│  5. Injects ctx["tool_gateway"] & ctx["memory_gateway"]     │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐           ┌──────────────────┐
│  ToolGateway    │           │  MemoryGateway   │
│  ─────────────  │           │  ──────────────  │
│  ABOM/policy/   │           │  wraps retrieval │
│  invariant      │           │  content hash    │
│  enforcement    │           │  source lineage  │
└────────┬────────┘           │  MEMORY_ACCESS   │
         │                    └────────┬─────────┘
         │                             │
         │         ┌───────────────────┘
         │         ▼
         │  ┌──────────────┐
         │  │ ReplayRecorder
         │  │ ──────────── │
         │  │ records tools│
         │  │ records memory
         │  │ commit snapshot
         │  └──────┬───────┘
         │         │
         ▼         ▼
    ┌──────────────────────┐
    │  REPLAY_SNAPSHOT     │
    │  audit event         │
    └──────────────────────┘
```

---

## 5. Components & Changes

### 5.1 `MemoryGateway` enhancements

**File:** `packages/shared/src/value_fabric/shared/governance/memory_gateway.py`

- Add optional `source_blocklist: set[str] | list[str]` constructor parameter.
- After retrieval, filter out entities/relationships whose `source_id` is in the blocklist.
- Record the filtered result in the access log and audit event.
- Keep the existing `_provenance` enrichment and `access_log` API.

**New public helper:**

```python
async def query(..., source_blocklist: list[str] | None = None) -> dict[str, Any]:
    ...
```

If `source_blocklist` is provided per-call, it overrides the constructor-level list. `BaseAgent.run()` will seed the constructor-level list from `ctx["memory_source_blocklist"]`.

### 5.2 `BaseAgent.run()` integration

**File:** `services/layer4-agents/src/layer4_agents/agents/base.py`

After `ToolGateway` creation, create a `MemoryGateway`:

```python
memory_gateway = None
if "memory_gateway" in ctx:
    memory_gateway = ctx["memory_gateway"]
elif "retrieval_engine" in ctx and self.abom is not None:
    memory_gateway = MemoryGateway(
        retrieval_engine=ctx["retrieval_engine"],
        tenant_id=ctx.get("tenant_id"),
        agent_id=self.agent_id,
        trace_id=ctx.get("trace_id"),
    )
    ctx["memory_gateway"] = memory_gateway
```

Before replay commit, record memory accesses:

```python
if replay_recorder is not None:
    if tool_gateway is not None:
        replay_recorder.record_tool_invocations(tool_gateway.invocation_log)
    if memory_gateway is not None:
        replay_recorder.record_memory_accesses(memory_gateway.access_log)
    await replay_recorder.commit()
```

### 5.3 `ReplayRecorder` deterministic hashing

**File:** `packages/shared/src/value_fabric/shared/governance/replay.py`

The current `build_snapshot()` includes `completed_at`, which makes the hash non-deterministic across replays. Change the canonical hash to cover a stable payload:

```python
stable_payload = {
    "agent_id": self._agent_id,
    "agent_type": self._agent_type,
    "manifest_hash": manifest_hash,
    "tenant_id": self._tenant_id,
    "trace_id": self._trace_id,
    "started_at": self._started_at,
    "tool_invocations": self._tool_invocations,
    "memory_accesses": self._memory_accesses,
}
snapshot["snapshot_hash"] = canonical_hash(stable_payload)
```

The emitted `ReplaySnapshotRecord` remains unchanged (it already excludes timestamps).

Add an optional `clock` parameter so tests can freeze time:

```python
def __init__(..., clock: Clock | None = None):
    self._clock = clock or SystemClock()
    self._started_at = self._clock.now().isoformat()
```

### 5.4 `ConversationService` wiring

**File:** `services/layer4-agents/src/layer4_agents/services/conversation.py`

- Accept an optional `retrieval_engine` constructor argument.
- Pass it into `_build_gate_context()` as `ctx["retrieval_engine"]` so that `ConversationAgent` runs create a `MemoryGateway`.
- Keep existing `tool_registry` behavior.

This is the first production call-site that will exercise the new memory-gateway wiring end-to-end.

### 5.5 Audit model stability

**File:** `packages/shared/src/value_fabric/shared/audit/models.py`

No schema changes are required — `MemoryAccessRecord` and `ReplaySnapshotRecord` already exist and conform to their JSON Schemas.

### 5.6 Contract documentation

**File:** `packages/platform-contract/CONTRACT.md`

Add/update §3.10 and §3.11 to reflect:

- `MemoryGateway` is the required retrieval boundary for agent runs.
- `ReplaySnapshot` events include both tool and memory counts.
- Direct retrieval engine calls from agent code are deprecated.

Update `docs/platform-contract/DEPRECATION_MAP.md` accordingly.

---

## 6. Data Flow

### 6.1 Happy path

1. Caller constructs `BaseAgent` subclass and calls `await agent.run(task, ctx)`.
2. `BaseAgent.run()` loads ABOM, creates `ToolGateway`, creates `MemoryGateway`, creates `ReplayRecorder`.
3. `execute()` implementation calls `ctx["memory_gateway"].query(...)`.
4. `MemoryGateway` delegates to the wrapped engine, computes `content_hash`, builds `source_lineage`, appends to `access_log`, emits `MEMORY_ACCESS` audit event.
5. `execute()` may also call `ctx["tool_gateway"].execute(...)`; tool invocations are logged similarly.
6. On completion, `BaseAgent.run()` copies `tool_gateway.invocation_log` and `memory_gateway.access_log` into `ReplayRecorder`, then commits a `REPLAY_SNAPSHOT` audit event.

### 6.2 Error handling

- If `ctx["retrieval_engine"]` is missing, agents that need memory must fail with a clear runtime error or degrade gracefully (agent-specific decision).
- If `MemoryGateway` audit emission fails, retrieval must still succeed; log the emission failure.
- If `ReplayRecorder.commit()` fails, the agent run still returns its result but logs the replay failure and marks state metadata.

---

## 7. Testing Strategy

### 7.1 New unit tests

- `tests/shared/governance/test_memory_gateway_blocklist.py`
  - Blocklisted source IDs are removed from results.
  - Audit event still records the filtered counts.

- `tests/shared/governance/test_replay_recorder.py` (extend existing)
  - Same inputs produce identical `snapshot_hash`.
  - Memory accesses appear in the snapshot.
  - Frozen clock yields deterministic timestamps.

- `tests/layer4-agents/test_base_agent_memory_gateway.py`
  - `BaseAgent.run()` creates a `MemoryGateway` when `ctx["retrieval_engine"]` is present.
  - Reuses `ctx["memory_gateway"]` if already present.
  - Replay snapshot contains memory access records after a mocked retrieval.

### 7.2 Updated tests

- `tests/integration/test_gate_integration.py`
  - Add a test that runs a minimal agent with both `tool_registry` and `retrieval_engine` and asserts the replay snapshot has non-zero tool and memory counts.

- `services/layer4-agents/tests/test_conversation_gate_context.py`
  - Verify `_build_gate_context()` includes `retrieval_engine` when provided.

### 7.3 Contract tests

- Keep existing schema validation for `memory-access.schema.json` and `replay-snapshot.schema.json`.
- Validate that `MemoryAccessRecord` produced after blocklist filtering still conforms.

### 7.4 Validation command

```bash
pytest tests/shared/governance/test_gate_phase3.py \
       tests/shared/governance/test_memory_gateway_blocklist.py \
       tests/shared/governance/test_replay_recorder.py \
       tests/layer4-agents/test_base_agent_memory_gateway.py
```

---

## 8. Rollout & Configuration

- `AGENT_REPLAY_MODE` env var:
  - `enabled` (default) — commit replay snapshots for agent runs with a `ToolGateway`.
  - `disabled` — skip replay commit (for high-throughput scenarios).
- Memory source blocklist:
  - Per-run via `ctx["memory_source_blocklist"]`.
  - Default empty.

---

## 9. Acceptance Criteria

- [ ] `BaseAgent.run()` creates or reuses a `MemoryGateway` and injects it into `ctx`.
- [ ] `MemoryGateway.query()` emits `MEMORY_ACCESS` audit events with `content_hash` and `source_lineage`.
- [ ] `MemoryGateway` can block listed source IDs from retrieval results.
- [ ] `ReplayRecorder` snapshot hash is deterministic for identical tool/memory inputs.
- [ ] `ReplayRecorder` snapshot includes memory access records.
- [ ] `ConversationService` passes a `retrieval_engine` through `_build_gate_context()` when available.
- [ ] New tests pass and existing `make verify` regressions unrelated to this change are documented.
- [ ] `CONTRACT.md` and `DEPRECATION_MAP.md` updated.

---

## 10. Open Questions / Assumptions

1. **Integration pattern:** Assumed Option A — caller provides `retrieval_engine` and `BaseAgent.run` wraps it. If a pre-built `MemoryGateway` is passed, it is reused.
2. **Replay scope:** Assumed all agent runs with a `ToolGateway` commit a snapshot, controlled by `AGENT_REPLAY_MODE`.
3. **Blocklist source:** Assumed blocklist comes from run context only; exact precedence is per-call > constructor.
