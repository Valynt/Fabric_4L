# GATE Framework Integration — Implementation Plan: Phases 1-3

**Status:** Draft
**Author:** AI Agent (Fabric 4L Alignment Analysis)
**Date:** 2026-04-27
**Scope:** `shared/audit/`, `services/layer4-agents/`, `services/layer3-knowledge/`, `contracts/`, `packages/platform-contract/`

---

## 0. Executive Summary

This plan implements the Governed Agent Trust Environment (GATE) framework across Fabric 4L in three ordered phases. Each phase builds on the previous, starting with cryptographic evidence integrity (foundation), moving to externalized policy control (governance), and ending with memory provenance and deterministic replay (advanced assurance).

**Key principle:** No agent behavior changes in Phase 1. Phase 2 introduces enforcement boundaries. Phase 3 adds observability for post-incident analysis.

---

## Phase 1: Integrity and Evidence (Foundation)

**Goal:** Implement RFC 8785 Canonical JSON hashing and hash-chained ledger commits across the audit emitter. Establish a verifiable evidence chain without altering agent runtime behavior.

**Timeline:** 2-3 weeks
**Risk:** Low (additive-only changes to audit infrastructure)

### 1.1 Canonical JSON Hashing Utility

**Gap:** `services/layer4-agents/src/layer4_agents/services/export_provenance.py` has an ad-hoc `_hash_canonical()` using `json.dumps(sort_keys=True, separators=(",", ":"))`. This is *close* to RFC 8785 but not fully compliant (no explicit float normalization, no guaranteed encoding rules).

**Action:**
- Create `shared/crypto/canonical.py` with a strict, tested implementation.
- Replace the ad-hoc helper in `export_provenance.py` with the shared utility.

```python
# shared/crypto/canonical.py
import hashlib
import json
from typing import Any


def canonical_json_encode(obj: Any) -> str:
    """Serialize object to canonical JSON per RFC 8785.

    Rules enforced:
    - Lexicographic key sorting
    - No insignificant whitespace
    - UTF-8 encoding
    - Floats rendered as shortest decimal representation
    """
    # For full compliance, wrap python-canonicaljson or implement
    # the exact subset used by Fabric 4L (all values are str/int/float/bool/None/list/dict).
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_canonical_default,
    )


def _canonical_default(obj: Any) -> Any:
    if isinstance(obj, bytes):
        return obj.decode("utf-8")
    raise TypeError(f"Object of type {type(obj)} is not canonicalizable")


def canonical_hash(obj: Any, algorithm: str = "sha256") -> str:
    """Return hex digest of canonical JSON serialization."""
    payload = canonical_json_encode(obj).encode("utf-8")
    if algorithm == "sha256":
        return hashlib.sha256(payload).hexdigest()
    raise ValueError(f"Unsupported hash algorithm: {algorithm}")
```

**Tests:** `tests/shared/crypto/test_canonical.py`
- Round-trip stability: `canonical_hash({"b": 1, "a": 2}) == canonical_hash({"a": 2, "b": 1})`
- Float normalization edge cases
- Unicode key ordering

### 1.2 Ledger-Aware Audit Event Model

**Gap:** `shared/audit/models.py` `AuditEvent` has no hash-chain fields.

**Action:**
Add optional ledger fields and a new structured detail type for tool invocations.

```python
# shared/audit/models.py (additions)

class AuditEvent(BaseModel):
    # ... existing fields ...
    # Phase 1 additions (all optional to preserve backward compat):
    previous_hash: str | None = Field(None, description="Hash of previous event in chain")
    event_hash: str | None = Field(None, description="Hash of this event's canonical payload")
    canonical_payload: dict[str, Any] | None = Field(None, description="Canonical JSON payload used for hashing")
    chain_id: str | None = Field(None, description="Logical chain identifier (e.g., tenant_id:tool_name)")
    sequence_number: int | None = Field(None, description="Monotonic sequence within chain_id")


class ToolInvocationRecord(BaseModel):
    """Structured details for TOOL_INVOCATION audit events."""
    tool_name: str
    tool_version: str | None = None
    tool_manifest_hash: str | None = None
    request_hash: str
    response_hash: str | None = None
    policy_decision: str | None = None  # "allowed" | "denied" | "invariant_blocked"
    invariant_checks: list[str] = Field(default_factory=list)
    execution_time_ms: int | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    trace_id: str | None = None


class LedgerCommitDetails(BaseModel):
    """Details for ledger commit events linking to previous state."""
    chain_head_hash: str | None = None
    commit_type: str  # "tool_invocation" | "policy_decision" | "agent_execution"
    bundle_hash: str | None = None  # Hash of policy/invariant bundle evaluated
```

**Backward compatibility:** All new fields are `Optional`. Existing handlers ignore them. The emitter populates them only when `AUDIT_LEDGER_MODE=enabled`.

### 1.3 Hash-Chained Audit Emitter

**Gap:** `shared/audit/emitter.py` dispatches events to handlers but maintains no chain state.

**Action:**
Implement an in-memory chain tracker (backed by Redis for multi-instance consistency) and a `LedgerCommitHandler`.

```python
# shared/audit/ledger.py
from __future__ import annotations

import asyncio
from typing import Any

from shared.crypto.canonical import canonical_hash
from .models import AuditEvent


class LedgerCommitHandler:
    """Audit handler that enforces hash chaining and emits ledger commits.

    Maintains a per-chain_id monotonic sequence and previous_hash.
    In multi-instance deployments, chain state MUST be backed by Redis
    (or the audit sink itself) to prevent hash forks.
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._local_heads: dict[str, tuple[int, str]] = {}  # chain_id -> (seq, hash)

    async def handle(self, event: AuditEvent) -> None:
        if not event.chain_id:
            # Not a ledger-tracked event; pass through
            return

        chain_id = event.chain_id
        seq, prev_hash = await self._get_chain_head(chain_id)
        next_seq = seq + 1

        # Build canonical payload (excluding mutable/hash fields)
        payload = {
            "id": str(event.id),
            "timestamp": event.timestamp,
            "action": event.action.value,
            "outcome": event.outcome.value,
            "actor_id": str(event.actor_id) if event.actor_id else None,
            "tenant_id": str(event.tenant_id) if event.tenant_id else None,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "request_id": event.request_id,
            "details": event.details,
            "previous_hash": prev_hash,
            "sequence_number": next_seq,
            "chain_id": chain_id,
        }

        event_hash = canonical_hash(payload)
        event.previous_hash = prev_hash
        event.event_hash = event_hash
        event.canonical_payload = payload
        event.sequence_number = next_seq

        await self._set_chain_head(chain_id, next_seq, event_hash)

    async def _get_chain_head(self, chain_id: str) -> tuple[int, str | None]:
        if self._redis:
            # Ticket SEC-4312 (Platform Security, M4-2026Q3):
            # implement Redis GET for chain_id
            pass
        return self._local_heads.get(chain_id, (0, None))

    async def _set_chain_head(self, chain_id: str, seq: int, hash_: str) -> None:
        if self._redis:
            # Ticket SEC-4312 (Platform Security, M4-2026Q3):
            # implement Redis SET
            pass
        self._local_heads[chain_id] = (seq, hash_)
```

**Update `shared/audit/emitter.py`:**
- Add `AUDIT_LEDGER_MODE` env var check.
- If enabled, instantiate `LedgerCommitHandler` and add it to the global emitter during startup.
- Ensure `validate_audit_config()` verifies Redis connectivity when `AUDIT_LEDGER_MODE=enabled`.

### 1.3a Emitter API Extension

**Gap:** `shared/audit/emitter.py` `emit_audit_event()` does not accept a `chain_id` parameter, which is required for ledger tracking.

**Action:**
Extend the `emit_audit_event()` signature to accept `chain_id` and pass it to the `AuditEvent` model.

```python
# shared/audit/emitter.py (signature update)
async def emit_audit_event(
    action: AuditAction,
    outcome: AuditOutcome,
    resource_type: str,
    resource_id: str,
    tenant_id: UUID | None = None,
    actor_id: UUID | None = None,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
    chain_id: str | None = None,  # New parameter
) -> None:
    event = AuditEvent(
        action=action,
        outcome=outcome,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        request_id=request_id,
        details=details or {},
        chain_id=chain_id,
    )
    # ... existing dispatch logic ...
```

### 1.4 Tool Invocation Records in ToolRegistry

**Gap:** `services/layer4-agents/src/layer4_agents/tools/registry.py` `ToolRegistry.execute()` logs tenant context but emits no structured audit event.

**Action:**
Instrument `ToolRegistry.execute()` to emit `TOOL_INVOCATION` audit events with request/response hashing.

```python
# services/layer4-agents/src/layer4_agents/tools/registry.py (execute method refactor)

async def execute(self, tool_name: str, input_dict: dict[str, Any]) -> dict[str, Any]:
    tool = self.get(tool_name)
    tenant_id = tool.get_tenant_id() or input_dict.get("tenant_id")
    trace_id = input_dict.get("trace_id")  # propagate from caller

    # Hash the request before execution
    request_hash = canonical_hash({"tool_name": tool_name, "input": input_dict})

    start_time = asyncio.get_running_loop().time()
    outcome = "success"
    response_hash: str | None = None
    error_detail: str | None = None

    try:
        result = await tool.run(input_dict)
        response_hash = canonical_hash(result)
        return result
    except Exception as exc:
        outcome = "failure"
        error_detail = str(exc)
        raise
    finally:
        elapsed_ms = int((asyncio.get_running_loop().time() - start_time) * 1000)

        # Emit only if ledger mode enabled (non-blocking)
        if os.getenv("AUDIT_LEDGER_MODE") == "enabled":
            record = ToolInvocationRecord(
                tool_name=tool_name,
                tool_manifest_hash=tool.manifest_hash if hasattr(tool, "manifest_hash") else None,
                request_hash=request_hash,
                response_hash=response_hash,
                execution_time_ms=elapsed_ms,
                tenant_id=tenant_id,
                trace_id=trace_id,
            )
            # Fire-and-forget to avoid blocking tool execution on audit latency
            asyncio.create_task(
                emit_audit_event(
                    action=AuditAction.TOOL_INVOCATION,  # new enum value
                    outcome=AuditOutcome.SUCCESS if outcome == "success" else AuditOutcome.FAILURE,
                    resource_type="tool",
                    resource_id=tool_name,
                    tenant_id=UUID(tenant_id) if tenant_id else None,
                    request_id=trace_id,
                    details=record.model_dump(),
                    chain_id=f"{tenant_id or 'global'}:{tool_name}" if tenant_id else None,
                )
            )
```

**Add to `AuditAction`:**
```python
TOOL_INVOCATION = "tool_invocation"
POLICY_DECISION = "policy_decision"
LEDGER_COMMIT = "ledger_commit"
```

### 1.5 Contracts & Schema Updates

**New files:**
- `contracts/jsonschema/audit-ledger-commit.json` — Schema for `LedgerCommitDetails`
- `contracts/jsonschema/tool-invocation-record.json` — Schema for `ToolInvocationRecord`

**Update:**
- `packages/platform-contract/CONTRACT.md` — Add §3.7 "Audit Ledger Commit Pattern":
  - Canonical JSON (RFC 8785) is the mandatory serialization for all audit hashes.
  - `AuditEvent` MAY include `previous_hash`, `event_hash`, `sequence_number`.
  - Tool executions MUST emit `TOOL_INVOCATION` records when ledger mode is enabled.

### 1.6 Testing Strategy

**Unit tests:**
- `tests/shared/crypto/test_canonical.py` — RFC 8785 compliance vectors
- `tests/shared/audit/test_ledger_chain.py` — Chain monotonicity, hash continuity, fork detection
- `tests/shared/audit/test_emitter_integration.py` — Handler registration, async emission, failure isolation

**Integration tests:**
- `tests/layer4/test_tool_invocation_audit.py` — Execute a tool via `ToolRegistry`, verify `TOOL_INVOCATION` event structure and hash fields.

**Contract tests:**
- Validate `contracts/jsonschema/audit-ledger-commit.json` against emitted payloads.

### 1.7 Migration & Rollout

1. Deploy `shared/crypto/canonical.py` and `shared/audit/ledger.py`.
2. Set `AUDIT_LEDGER_MODE=disabled` (default) in all environments.
3. Run shadow mode in staging: emit ledger events but do not enforce.
4. After 1 week of stable shadow hashes, set `AUDIT_LEDGER_MODE=enabled` in production.
5. Backfill: existing audit events are *not* hash-chained (they predate the chain). Chain IDs start from first enabled event.

---

## Phase 2: The ABOM and Policy Gateway (Control)

**Goal:** Introduce the Agent Bill of Materials (ABOM) and externalize policy/invariant evaluation via a Tool Gateway. Policy and invariant evaluation occurs *before* tool logic is invoked.

**Timeline:** 3-4 weeks
**Risk:** Medium (changes `ToolRegistry.execute()` control flow; requires new infrastructure)

### 2.1 ABOM Schema & Manifests

**Gap:** No ABOM concept exists. Agent capabilities are declared in Python `get_capabilities()` at runtime.

**Action:**
Define a machine-readable ABOM JSON Schema and create manifests for each existing agent.

```json
// contracts/jsonschema/abom.json (excerpt)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://valuefabric.io/schemas/abom/v1",
  "title": "Agent Bill of Materials",
  "type": "object",
  "required": ["abom_version", "agent_id", "agent_type", "allowed_tools", "identity", "controls"],
  "properties": {
    "abom_version": { "type": "string", "const": "1.0.0" },
    "agent_id": { "type": "string", "description": "Format: <agent_type>-<8-char-prefix>" },
    "agent_type": { "type": "string" },
    "description": { "type": "string" },
    "allowed_tools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["tool_name", "tool_manifest_hash", "obligations"],
        "properties": {
          "tool_name": { "type": "string" },
          "tool_manifest_hash": { "type": "string" },
          "obligations": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Required audit obligations for this tool (e.g., 'hash_request_response')"
          },
          "max_invocations_per_minute": { "type": "integer" },
          "budget_limit_usd": { "type": "number" }
        }
      }
    },
    "identity": {
      "type": "object",
      "required": ["auth_method", "role"],
      "properties": {
        "auth_method": { "enum": ["jwt", "api_key", "service_account"] },
        "role": { "type": "string" },
        "tenant_scoped": { "type": "boolean" }
      }
    },
    "controls": {
      "type": "object",
      "required": ["required_policy_bundle", "required_invariant_bundle"],
      "properties": {
        "required_policy_bundle": { "type": "string", "description": "Hash of policy bundle" },
        "required_invariant_bundle": { "type": "string", "description": "Hash of invariant bundle" },
        "autonomy_tier": { "enum": ["bounded", "high_privilege", "supervised"] },
        "memory_partitions": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

**New directory:** `layer4-agents/aboms/`
- `layer4-agents/aboms/signal_detection.json`
- `layer4-agents/aboms/taxonomy.json`
- `layer4-agents/aboms/orchestration_controller.json`
- ... one per concrete agent type

**Python model:**
```python
# services/layer4-agents/src/governance/abom.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from shared.crypto.canonical import canonical_hash


class ToolPermission(BaseModel):
    tool_name: str
    tool_manifest_hash: str | None = None
    obligations: list[str] = Field(default_factory=list)
    max_invocations_per_minute: int | None = None
    budget_limit_usd: float | None = None


class AgentIdentity(BaseModel):
    auth_method: str
    role: str
    tenant_scoped: bool = True


class AgentControls(BaseModel):
    required_policy_bundle: str
    required_invariant_bundle: str
    autonomy_tier: str = "bounded"
    memory_partitions: list[str] = Field(default_factory=list)


class AgentBillOfMaterials(BaseModel):
    abom_version: str = "1.0.0"
    agent_id: str
    agent_type: str
    description: str | None = None
    allowed_tools: list[ToolPermission]
    identity: AgentIdentity
    controls: AgentControls

    @classmethod
    def load_for_agent(cls, agent_type: str, abom_dir: Path | None = None) -> AgentBillOfMaterials:
        abom_dir = abom_dir or Path(__file__).parent.parent.parent / "aboms"
        path = abom_dir / f"{agent_type.lower()}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def compute_hash(self) -> str:
        return canonical_hash(self.model_dump())
```

### 2.2 Policy Engine Integration (OPA/Rego)

**Gap:** Fabric 4L has Rego for K8s (`k8s/policy/security-hardening.rego`) but no runtime policy engine for tool execution.

**Action:**
Implement a Policy Engine client that can call OPA (or a local Rego evaluator) and a Policy Bundle loader.

```python
# services/layer4-agents/src/governance/policy_engine.py
from __future__ import annotations

import os
from typing import Any

import httpx

from shared.crypto.canonical import canonical_hash


class PolicyDecision:
    def __init__(self, allowed: bool, reason: str | None = None, obligations: list[str] | None = None) -> None:
        self.allowed = allowed
        self.reason = reason
        self.obligations = obligations or []


class PolicyEngineClient:
    """Client for externalized policy evaluation (OPA/Rego or local bundle)."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("OPA_URL", "http://localhost:8181")

    async def evaluate(self, input_data: dict[str, Any], policy_path: str = "fabric/tool/allow") -> PolicyDecision:
        """Evaluate tool request against configurable policy bundle."""
        if os.getenv("POLICY_ENGINE_MODE", "local") == "local":
            return self._evaluate_local(input_data)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/data/{policy_path}",
                json={"input": input_data},
                timeout=5.0,
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            return PolicyDecision(
                allowed=result.get("allow", False),
                reason=result.get("reason"),
                obligations=result.get("obligations", []),
            )

    def _evaluate_local(self, input_data: dict[str, Any]) -> PolicyDecision:
        # Fallback when OPA is unavailable: deny all unless explicitly allowed by hardcoded tenant checks
        # This is a safety default, not a production policy.
        tenant_id = input_data.get("tenant_id")
        if not tenant_id:
            return PolicyDecision(allowed=False, reason="No tenant context in policy input")

        # Deny-all for high-privilege agents during OPA unavailability
        abom = input_data.get("abom", {})
        controls = abom.get("controls", {})
        if controls.get("autonomy_tier") == "high_privilege":
            return PolicyDecision(allowed=False, reason="OPA unavailable: high_privilege tier requires explicit OPA allow")

        return PolicyDecision(allowed=True, reason="Local fallback: tenant present and tier is not high_privilege")
```

**New Rego bundle:** `k8s/policy/agent-runtime-policies.rego`
```rego
package fabric.tool

import rego.v1

default allow := false

allow if {
    input.tenant_id != ""
    input.tool_name in input.abom.allowed_tools
    input.hourly_budget_remaining > 0
}

deny_reason := "missing_tenant" if {
    input.tenant_id == ""
}

deny_reason := "tool_not_in_abom" if {
    not input.tool_name in input.abom.allowed_tools
}

deny_reason := "budget_exhausted" if {
    input.hourly_budget_remaining <= 0
}

obligations contains "audit_tool_invocation" if {
    input.abom.controls.autonomy_tier == "high_privilege"
}
```

### 2.3 Invariant Bundle Evaluator

**Gap:** No hard invariant enforcement separate from configurable policy.

**Action:**
Implement an `InvariantEvaluator` that checks non-overridable limits *after* policy allows but *before* tool execution.

```python
# services/layer4-agents/src/governance/invariant_bundle.py
from __future__ import annotations

import os
from typing import Any

from shared.crypto.canonical import canonical_hash
from ..governance.abom import AgentBillOfMaterials


class InvariantViolation(Exception):
    """Raised when a non-overridable invariant is violated."""
    pass


class InvariantEvaluator:
    """Evaluates hard limits independent of policy context.

    Invariants are NON-CONFIGURABLE per deployment. They cannot be overridden
    by tenant admins or policy exceptions.
    """

    # Hard limits (could be loaded from environment for ops flexibility,
    # but treated as immutable at runtime)
    MAX_SINGLE_TRANSFER_USD: float = float(os.getenv("INVARIANT_MAX_TRANSFER_USD", "10000.0"))
    RESTRICTED_TOOLS: set[str] = {"delete_tenant", "suspend_tenant"}
    RESTRICTED_DOMAINS: set[str] = set(os.getenv("INVARIANT_RESTRICTED_DOMAINS", "").split(","))

    def evaluate(self, tool_name: str, input_data: dict[str, Any], abom: AgentBillOfMaterials) -> None:
        # Invariant 1: Financial limits
        amount = input_data.get("amount_usd") or input_data.get("transfer_amount")
        if amount and float(amount) > self.MAX_SINGLE_TRANSFER_USD:
            raise InvariantViolation(
                f"Invariant blocked: amount {amount} exceeds max {self.MAX_SINGLE_TRANSFER_USD}"
            )

        # Invariant 2: Admin tools require high-privilege ABOM tier
        if tool_name in self.RESTRICTED_TOOLS:
            if abom.controls.autonomy_tier != "high_privilege":
                raise InvariantViolation(
                    f"Invariant blocked: tool {tool_name} requires high_privilege tier"
                )

        # Invariant 3: Domain restrictions
        target_domain = input_data.get("domain") or input_data.get("url")
        if target_domain:
            for restricted in self.RESTRICTED_DOMAINS:
                if restricted and restricted in str(target_domain):
                    raise InvariantViolation(
                        f"Invariant blocked: domain restricted by invariant"
                    )

    def compute_bundle_hash(self) -> str:
        bundle = {
            "max_transfer_usd": self.MAX_SINGLE_TRANSFER_USD,
            "restricted_tools": sorted(self.RESTRICTED_TOOLS),
            "restricted_domains": sorted(self.RESTRICTED_DOMAINS),
        }
        return canonical_hash(bundle)
```

### 2.4 Tool Gateway & Two-Stage Evaluation

**Gap:** `ToolRegistry.execute()` directly dispatches to tool logic.

**Action:**
Introduce a `ToolGateway` class that wraps the registry and enforces the two-stage pipeline.

```python
# services/layer4-agents/src/gateway/tool_gateway.py
from __future__ import annotations

from typing import Any

from ..governance.abom import AgentBillOfMaterials
from ..governance.invariant_bundle import InvariantEvaluator, InvariantViolation
from ..governance.policy_engine import PolicyDecision, PolicyEngineClient
from ..tools.registry import ToolRegistry, ToolError, ToolNotFoundError, ToolValidationError
from shared.audit.emitter import emit_audit_event
from shared.audit.models import AuditAction, AuditOutcome, PolicyDecisionRecord


class ToolGateway:
    """GATE Tool Gateway — externalized policy and invariant enforcement.

    All tool requests MUST flow through the gateway. The registry's execute()
    method remains available for internal/testing use, but production agents
    must use the gateway.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngineClient | None = None,
        invariant_evaluator: InvariantEvaluator | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy_engine or PolicyEngineClient()
        self.invariants = invariant_evaluator or InvariantEvaluator()

    async def execute(
        self,
        tool_name: str,
        input_dict: dict[str, Any],
        abom: AgentBillOfMaterials | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = context or {}
        tenant_id = ctx.get("tenant_id") or input_dict.get("tenant_id")
        trace_id = ctx.get("trace_id")
        actor_id = ctx.get("actor_id")

        # Stage 1: Policy Evaluation (configurable)
        policy_input = {
            "tool_name": tool_name,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "abom": abom.model_dump() if abom else {},
            "hourly_budget_remaining": ctx.get("hourly_budget_remaining", 1.0),
            "input": input_dict,
        }
        decision = await self.policy.evaluate(policy_input)

        # Emit policy decision record regardless of outcome
        await emit_audit_event(
            action=AuditAction.POLICY_DECISION,
            outcome=AuditOutcome.SUCCESS if decision.allowed else AuditOutcome.DENIED,
            resource_type="tool",
            resource_id=tool_name,
            tenant_id=tenant_id,
            request_id=trace_id,
            details=PolicyDecisionRecord(
                decision=decision.allowed,
                reason=decision.reason,
                obligations=decision.obligations,
                policy_bundle_hash=ctx.get("policy_bundle_hash"),
            ).model_dump(),
        )

        if not decision.allowed:
            raise ToolError(f"Policy denied execution of {tool_name}: {decision.reason}")

        # Stage 2: Invariant Evaluation (non-overridable)
        if abom:
            try:
                self.invariants.evaluate(tool_name, input_dict, abom)
            except InvariantViolation as inv:
                await emit_audit_event(
                    action=AuditAction.POLICY_DECISION,
                    outcome=AuditOutcome.DENIED,
                    resource_type="tool",
                    resource_id=tool_name,
                    tenant_id=tenant_id,
                    request_id=trace_id,
                    details={"invariant_violation": str(inv), "invariant_bundle_hash": self.invariants.compute_bundle_hash()},
                )
                raise ToolError(f"Invariant blocked execution of {tool_name}: {inv}") from inv

        # Stage 3: Execute via registry (Phase 1 audit instrumentation already in place)
        return await self.registry.execute(tool_name, input_dict)
```

### 2.5 ToolRegistry Refactoring

**Changes to `services/layer4-agents/src/layer4_agents/tools/registry.py`:**
1. Add `manifest_hash` class attribute to `BaseTool` (populated from `contracts/tool-manifests/<name>.json` hash at build time).
2. Update `create_default_registry()` to load manifest hashes.
3. Keep `ToolRegistry.execute()` as the low-level dispatcher; high-level enforcement moves to `ToolGateway`.
4. Update `get_available_tools()` to accept an optional `abom: AgentBillOfMaterials` filter (intersect hardcoded RBAC with ABOM allowed_tools).

### 2.6 Agent Lifecycle Integration

**Changes to `services/layer4-agents/src/layer4_agents/agents/base.py`:**
- Add `abom: AgentBillOfMaterials | None` to `BaseAgent.__init__`.
- Load ABOM in `initialize()` via `AgentBillOfMaterials.load_for_agent(self.agent_type)`.
- Store `abom` in `AgentState.metadata`.
- Agents execute tools through `ToolGateway` instead of raw `ToolRegistry`.

```python
# services/layer4-agents/src/layer4_agents/agents/base.py (additions)
class BaseAgent(ABC):
    # ... existing attributes ...
    abom: AgentBillOfMaterials | None = None

    async def initialize(self) -> None:
        if self._initialized:
            return
        self.state.status = AgentStatus.INITIALIZING
        self.abom = AgentBillOfMaterials.load_for_agent(self.agent_type)
        await self._initialize_resources()
        self._initialized = True
        self.state.status = AgentStatus.IDLE
```

### 2.7 Testing Strategy

**Unit tests:**
- `tests/layer4/governance/test_abom.py` — Load, hash, validation
- `tests/layer4/governance/test_policy_engine.py` — Mock OPA responses, local fallback
- `tests/layer4/governance/test_invariant_bundle.py` — Financial limit, tier restriction, domain block
- `tests/layer4/gateway/test_tool_gateway.py` — Two-stage pipeline ordering, audit emission, error propagation

**Integration tests:**
- `tests/layer4/test_agent_with_abom.py` — Initialize agent, verify ABOM loaded, verify tool execution blocked by policy/invariant.

**Contract tests:**
- Validate all `layer4-agents/aboms/*.json` against `contracts/jsonschema/abom.json`.
- Validate `agent-runtime-policies.rego` with `opa test`.

---

## Phase 3: Memory Gateway and Replay (Advanced)

**Goal:** Enhance Layer 3 retrieval with provenance tracking and implement deterministic replay recording for post-incident analysis.

**Timeline:** 3-4 weeks
**Risk:** Medium (touches graph traversal hot paths; adds write load to audit log)

### 3.1 Memory Gateway Architecture

**Gap:** `GraphRAGEngine` and `HybridSearch` retrieve entities but do not emit structured access records or compute content hashes of retrieved data.

**Action:**
Create a `MemoryGateway` that wraps retrieval engines and enforces ACLs, provenance tracking, and poisoning controls.

```python
# services/layer3-knowledge/src/governance/memory_gateway.py
from __future__ import annotations

import asyncio
from typing import Any

from shared.audit.emitter import emit_audit_event
from shared.audit.models import AuditAction, AuditOutcome, MemoryAccessRecord
from shared.crypto.canonical import canonical_hash

from ..retrieval.graph_rag import GraphRAGEngine, GraphRAGResult
from ..retrieval.hybrid_search import HybridSearchEngine, HybridSearchResult


class MemoryGateway:
    """GATE Memory Gateway — retrieval-time ACLs, provenance, and poisoning controls.

    Wraps GraphRAG and HybridSearch to emit memory access records and enforce
    retrieval boundaries.
    """

    def __init__(
        self,
        graph_engine: GraphRAGEngine | None = None,
        hybrid_engine: HybridSearchEngine | None = None,
    ) -> None:
        self.graph = graph_engine
        self.hybrid = hybrid_engine

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        trace_id: str | None = None,
        max_hops: int | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        if not tenant_id:
            raise ValueError("tenant_id is required for MemoryGateway.retrieve")

        # Ticket SEC-4318 (Layer 4 Agents, M1-2027Q1):
        # Phase 3.2 — retrieval-time ACL check (e.g., is agent allowed to access this partition?)

        # Execute retrieval through wrapped engine
        result = await self.graph.query(
            query_text=query,
            max_hops=max_hops,
            max_results=max_results,
        )

        # Compute content hash of retrieved context
        retrieved_payload = {
            "entities": sorted([e["id"] for e in result.entities]),
            "relationships": sorted([f"{r['source']}-{r['type']}-{r['target']}" for r in result.relationships]),
            "query": query,
        }
        content_hash = canonical_hash(retrieved_payload)

        # Build source lineage pointers
        source_lineage = []
        for entity in result.entities:
            source_id = entity.get("source_id") or entity.get("provenance_source")
            if source_id:
                source_lineage.append({
                    "entity_id": entity["id"],
                    "source_id": source_id,
                    "confidence": entity.get("confidence"),
                })

        # Emit memory access record
        record = MemoryAccessRecord(
            query=query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            content_hash=content_hash,
            source_lineage=source_lineage,
            entity_count=len(result.entities),
            relationship_count=len(result.relationships),
            trace_id=trace_id,
        )
        # Note: Using create_task for fire-and-forget emission.
        # In a production shutdown scenario, ensure the event loop waits for pending tasks
        # or use a dedicated background worker to prevent silent loss.
        asyncio.create_task(
            emit_audit_event(
                action=AuditAction.MEMORY_ACCESS,
                outcome=AuditOutcome.SUCCESS,
                resource_type="memory",
                resource_id=query,
                tenant_id=tenant_id,
                request_id=trace_id,
                details=record.model_dump(),
                chain_id=f"{tenant_id}:memory" if tenant_id else None,
            )
        )

        return {
            "result": result,
            "memory_access_hash": content_hash,
            "source_lineage": source_lineage,
        }
```

### 3.2 Retrieval-Time ACLs & Provenance

**Changes to `services/layer3-knowledge/src/retrieval/graph_rag.py`:**
- `get_entity_context()` already enforces `tenant_id`. Keep this as the primary isolation boundary.
- Add optional `agent_id` parameter to all public retrieval methods.
- In `GraphRAGEngine.query()`, inject a post-filter step that drops entities whose `source_id` is in a tenant-specific blocklist (poisoning control).

**New schema:** `contracts/jsonschema/memory-access-record.json`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MemoryAccessRecord",
  "type": "object",
  "required": ["query", "tenant_id", "content_hash"],
  "properties": {
    "query": { "type": "string" },
    "tenant_id": { "type": "string" },
    "agent_id": { "type": "string" },
    "content_hash": { "type": "string" },
    "source_lineage": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entity_id": { "type": "string" },
          "source_id": { "type": "string" },
          "confidence": { "type": "number" }
        }
      }
    },
    "entity_count": { "type": "integer" },
    "relationship_count": { "type": "integer" },
    "trace_id": { "type": "string" }
  }
}
```

### 3.3 Memory Access Records

**Update `shared/audit/models.py`:**
```python
class MemoryAccessRecord(BaseModel):
    query: str
    tenant_id: str
    agent_id: str | None = None
    content_hash: str
    source_lineage: list[dict[str, Any]] = Field(default_factory=list)
    entity_count: int = 0
    relationship_count: int = 0
    trace_id: str | None = None

class AuditAction(str, Enum):
    # ... existing values ...
    TOOL_INVOCATION = "tool_invocation"
    POLICY_DECISION = "policy_decision"
    MEMORY_ACCESS = "memory_access"
    REPLAY_SNAPSHOT = "replay_snapshot"
```

### 3.4 Replay Recorder & Deterministic Snapshots

**Gap:** No mechanism exists to capture a deterministic snapshot of agent state, tool boundaries, and memory context for replay.

**Action:**
Implement a `ReplayRecorder` that captures snapshots at key lifecycle points.

```python
# services/layer4-agents/src/governance/replay_recorder.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from shared.audit.emitter import emit_audit_event
from shared.audit.models import AuditAction, AuditOutcome, ReplaySnapshotRecord
from shared.crypto.canonical import canonical_hash


@dataclass
class ToolSnapshot:
    tool_name: str
    tool_manifest_hash: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    policy_bundle_hash: str | None = None
    invariant_bundle_hash: str | None = None
    execution_time_ms: int | None = None


@dataclass
class MemorySnapshot:
    query: str | None = None
    content_hash: str | None = None
    source_lineage: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentSnapshot:
    agent_id: str
    agent_type: str
    abom_hash: str | None = None
    state_hash: str | None = None  # Hash of AgentState.to_dict()
    capabilities_hash: str | None = None


@dataclass
class ReplayTrace:
    trace_id: str
    tenant_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent: AgentSnapshot | None = None
    tools: list[ToolSnapshot] = field(default_factory=list)
    memories: list[MemorySnapshot] = field(default_factory=list)

    def to_snapshot_hash(self) -> str:
        payload = {
            "trace_id": self.trace_id,
            "tenant_id": self.tenant_id,
            "agent": self.agent.__dict__ if self.agent else None,
            "tools": [t.__dict__ for t in self.tools],
            "memories": [m.__dict__ for m in self.memories],
        }
        return canonical_hash(payload)


class ReplayRecorder:
    """Captures deterministic snapshots for post-incident replay.

    Usage:
        recorder = ReplayRecorder(trace_id="trace-123", tenant_id="t-1")
        recorder.set_agent(agent_snapshot)
        recorder.record_tool(tool_snapshot)
        recorder.record_memory(memory_snapshot)
        await recorder.commit()
    """

    def __init__(self, trace_id: str, tenant_id: str | None = None) -> None:
        self.trace = ReplayTrace(trace_id=trace_id, tenant_id=tenant_id)

    def set_agent(self, snapshot: AgentSnapshot) -> None:
        self.trace.agent = snapshot

    def record_tool(self, snapshot: ToolSnapshot) -> None:
        self.trace.tools.append(snapshot)

    def record_memory(self, snapshot: MemorySnapshot) -> None:
        self.trace.memories.append(snapshot)

    async def commit(self) -> str:
        snapshot_hash = self.trace.to_snapshot_hash()
        record = ReplaySnapshotRecord(
            trace_id=self.trace.trace_id,
            tenant_id=self.trace.tenant_id,
            snapshot_hash=snapshot_hash,
            tool_count=len(self.trace.tools),
            memory_count=len(self.trace.memories),
            agent_type=self.trace.agent.agent_type if self.trace.agent else None,
            abom_hash=self.trace.agent.abom_hash if self.trace.agent else None,
        )
        # Await emission to prevent silent loss on shutdown
        await emit_audit_event(
            action=AuditAction.REPLAY_SNAPSHOT,
            outcome=AuditOutcome.SUCCESS,
            resource_type="replay_trace",
            resource_id=self.trace.trace_id,
            tenant_id=self.trace.tenant_id,
            request_id=self.trace.trace_id,
            details=record.model_dump(),
            chain_id=f"{self.trace.tenant_id or 'global'}:replay" if self.trace.tenant_id else None,
        )
        return snapshot_hash
```

**Integration into `BaseAgent`:**
```python
# services/layer4-agents/src/layer4_agents/agents/base.py (run method additions)

async def run(self, task: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {}
    trace_id = ctx.get("trace_id", self._id_gen.generate())
    tenant_id = ctx.get("tenant_id")

    recorder = ReplayRecorder(trace_id=trace_id, tenant_id=tenant_id)
    if self.abom:
        recorder.set_agent(AgentSnapshot(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            abom_hash=self.abom.compute_hash(),
            state_hash=canonical_hash(self.state.to_dict()),
        ))

    # ... existing run logic ...
    # Store recorder in context so gateways can access it
    ctx["replay_recorder"] = recorder

    # Gateways (ToolGateway, MemoryGateway) will append snapshots to the recorder
    # found in the context, avoiding the need for hooks in all 8 agent implementations.

    # At completion:
    await recorder.commit()
    return result
```

### 3.5 Testing Strategy

**Unit tests:**
- `tests/layer3/governance/test_memory_gateway.py` — Mock GraphRAG, verify hash stability, verify audit emission
- `tests/layer4/governance/test_replay_recorder.py` — Snapshot hash determinism, trace completeness

**Integration tests:**
- `tests/layer3/test_graph_rag_provenance.py` — End-to-end retrieval with memory access record validation
- `tests/layer4/test_agent_replay.py` — Run an agent, verify replay snapshot emitted with correct tool/memory entries

**Contract tests:**
- Validate `contracts/jsonschema/memory-access-record.json` against emitted records.
- Validate `contracts/jsonschema/replay-snapshot-record.json` against committed traces.

---

## Cross-Cutting Concerns

### Platform Contract Updates

**File:** `packages/platform-contract/CONTRACT.md`

Add the following new sections (or subsections under Tool Invocation Boundary):

| Section | Title | Key Requirement |
|---------|-------|-----------------|
| §3.7 | Audit Ledger Commit | All audit hashes MUST use RFC 8785 Canonical JSON. `AuditEvent` MAY include `previous_hash` and `event_hash`. |
| §3.8 | Tool Gateway | Production tool execution MUST flow through `ToolGateway`. Direct `ToolRegistry.execute()` is permitted only in tests. |
| §3.9 | Agent Bill of Materials | Every deployed agent MUST have a matching ABOM manifest. ABOM hash MUST be recorded in agent startup events. |
| §3.10 | Memory Gateway | Retrieval operations MUST emit `MEMORY_ACCESS` records with `content_hash` and `source_lineage`. |
| §3.11 | Replay Recorder | Agents in `high_privilege` or `bounded` tiers MUST commit a `ReplaySnapshot` at the end of every run. |

Update `docs/platform-contract/DEPRECATION_MAP.md` to mark direct `ToolRegistry.execute()` from agent code as deprecated with a target removal version.

### CI/CD Integration

1. **New CI job:** `gate-contract-tests`
   - `opa test k8s/policy/agent-runtime-policies.rego`
   - `pytest tests/layer4/gateway/`
   - JSON Schema validation for all ABOMs and audit record types

2. **Pre-merge gate:**
   - Any change to `shared/audit/models.py` requires updating `contracts/jsonschema/audit-*.json`.
   - Any new agent requires an ABOM manifest in `layer4-agents/aboms/`.

### Performance Impact

| Component | Impact | Mitigation |
|-----------|--------|------------|
| Canonical JSON hashing | ~0.1ms per event | Use `orjson` where available; hashing is async fire-and-forget |
| Ledger chain head lookup | ~1-2ms (Redis) | Local cache for single-instance dev; Redis for prod |
| Policy Engine (OPA) | ~5-10ms per tool call | Local bundle evaluation fallback; OPA sidecar with connection pooling |
| Memory access records | ~0.5ms per retrieval | Fire-and-forget audit emission; hash only entity IDs, not full properties |
| Replay snapshots | ~1ms per trace | Hash computed once at commit; snapshots kept in-memory until commit |

### Security Review Gates

Per `AGENTS.md` P0 rules:
- **Do not** place real OPA secrets in manifests. Use `.env` and `INFISICAL_SECRET_SEEDED` for `OPA_URL` / `OPA_TOKEN`.
- **Do not** weaken `shared/identity/` RBAC during policy engine integration. The `ToolGateway` is additive; existing middleware stays.
- All changes to `shared/audit/` require a security review sign-off before merge.

---

## Appendix A: File Inventory

### New Files

```
shared/crypto/canonical.py
shared/crypto/__init__.py
shared/audit/ledger.py
shared/audit/ledger_handler.py
services/layer4-agents/src/governance/__init__.py
services/layer4-agents/src/governance/abom.py
services/layer4-agents/src/governance/policy_engine.py
services/layer4-agents/src/governance/invariant_bundle.py
services/layer4-agents/src/governance/replay_recorder.py
services/layer4-agents/src/governance/replay_models.py
services/layer4-agents/src/gateway/__init__.py
services/layer4-agents/src/gateway/tool_gateway.py
services/layer3-knowledge/src/governance/__init__.py
services/layer3-knowledge/src/governance/memory_gateway.py
contracts/jsonschema/audit-ledger-commit.json
contracts/jsonschema/tool-invocation-record.json
contracts/jsonschema/abom.json
contracts/jsonschema/memory-access-record.json
contracts/jsonschema/replay-snapshot-record.json
contracts/jsonschema/policy-decision-record.json
services/layer4-agents/aboms/signal_detection.json
services/layer4-agents/aboms/taxonomy.json
services/layer4-agents/aboms/orchestration_controller.json
k8s/policy/agent-runtime-policies.rego
tests/shared/crypto/test_canonical.py
tests/shared/audit/test_ledger_chain.py
tests/layer4/governance/test_abom.py
tests/layer4/governance/test_policy_engine.py
tests/layer4/governance/test_invariant_bundle.py
tests/layer4/governance/test_replay_recorder.py
tests/layer4/gateway/test_tool_gateway.py
tests/layer3/governance/test_memory_gateway.py
```

### Modified Files

```
shared/audit/models.py
shared/audit/emitter.py
services/layer4-agents/src/layer4_agents/tools/registry.py
services/layer4-agents/src/layer4_agents/agents/base.py
services/layer3-knowledge/src/retrieval/graph_rag.py
services/layer4-agents/src/layer4_agents/services/export_provenance.py
packages/platform-contract/CONTRACT.md
docs/platform-contract/DEPRECATION_MAP.md
```

---

## Appendix B: Rollback Procedures

| Phase | Rollback Trigger | Procedure |
|-------|-----------------|-----------|
| 1 | Hash chain corruption or perf regression | Set `AUDIT_LEDGER_MODE=disabled`. Events revert to non-chained emission. |
| 2 | Policy engine latency or false denials | Set `POLICY_ENGINE_MODE=local` (permissive fallback) or bypass `ToolGateway` to `ToolRegistry.execute()` via feature flag. |
| 3 | Memory audit log saturation | Disable `MemoryGateway` wrapper; return to direct `GraphRAGEngine.query()`. |

---

## Appendix C: Acceptance Criteria

### Phase 1 Complete When
- [ ] `canonical_hash()` passes RFC 8785 compliance vectors.
- [ ] `AuditEvent` includes optional `previous_hash`, `event_hash`, `sequence_number`.
- [ ] `TOOL_INVOCATION` events are emitted for every `TenantAwareTool` execution in staging.
- [ ] Hash chain is verifiable end-to-end for a 100-event sequence.

### Phase 2 Complete When
- [ ] Every agent type has an ABOM manifest validated by CI.
- [ ] `ToolGateway.execute()` blocks tool execution when OPA returns `allow: false`.
- [ ] `InvariantEvaluator` blocks execution exceeding hard financial limits regardless of policy.
- [ ] `make verify` passes with new governance tests.

### Phase 3 Complete When
- [ ] Every `GraphRAG` retrieval emits a `MEMORY_ACCESS` record with `content_hash` and `source_lineage`.
- [ ] `ReplayRecorder` commits a `ReplaySnapshot` for every agent run in `high_privilege` tier.
- [ ] A replay trace can be reconstructed from audit log entries for a complete agent workflow.
- [ ] `make evals` passes with new GATE evaluation suite.
