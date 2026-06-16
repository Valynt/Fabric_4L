"""ReplayRecorder — deterministic agent run replay snapshots.

Captures a complete snapshot of an agent run including:
- Agent identity and ABOM manifest hash
- Tool invocation log (from ToolGateway)
- Memory access log (from MemoryGateway)
- Run timing and outcome
- Canonical snapshot hash for integrity verification

Committed as a REPLAY_SNAPSHOT audit event at the end of each run.

GATE Framework §3.2 — ReplayRecorder
"""

from __future__ import annotations

import logging
from typing import Any

from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome, ReplaySnapshotRecord
from value_fabric.shared.crypto.canonical import canonical_hash
from value_fabric.shared.testability import Clock, SystemClock

logger = logging.getLogger(__name__)


class ReplayRecorder:
    """Records agent run snapshots for deterministic replay.

    Collects tool invocations and memory accesses during an agent run,
    then commits a single REPLAY_SNAPSHOT audit event with a canonical
    hash of the entire run.

    Args:
        agent_id: Agent instance identifier.
        agent_type: Agent class name.
        abom: Agent's ABOM manifest (for manifest hash).
        tenant_id: Tenant context.
        trace_id: Trace ID for audit correlation.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        abom: Any | None = None,
        tenant_id: str | None = None,
        trace_id: str | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._agent_type = agent_type
        self._abom = abom
        self._tenant_id = tenant_id
        self._trace_id = trace_id
        self._tool_invocations: list[dict[str, Any]] = []
        self._memory_accesses: list[dict[str, Any]] = []
        self._clock = clock or SystemClock()
        self._started_at: str = self._clock.now().isoformat()
        self._committed = False

    def record_tool_invocations(self, invocations: list[dict[str, Any]]) -> None:
        """Record tool invocations from ToolGateway.invocation_log.

        Args:
            invocations: List of invocation records from ToolGateway.
        """
        self._tool_invocations.extend(invocations)

    def record_memory_accesses(self, accesses: list[dict[str, Any]]) -> None:
        """Record memory accesses from MemoryGateway.access_log.

        Args:
            accesses: List of access records from MemoryGateway.
        """
        self._memory_accesses.extend(accesses)

    def build_snapshot(self) -> dict[str, Any]:
        """Build the complete replay snapshot.

        Returns:
            Snapshot dictionary with all run data and canonical hash.
        """
        manifest_hash = None
        if self._abom is not None and hasattr(self._abom, "manifest_hash"):
            manifest_hash = self._abom.manifest_hash()

        snapshot = {
            "agent_id": self._agent_id,
            "agent_type": self._agent_type,
            "manifest_hash": manifest_hash,
            "tenant_id": self._tenant_id,
            "trace_id": self._trace_id,
            "started_at": self._started_at,
            "completed_at": self._clock.now().isoformat(),
            "tool_invocations": self._tool_invocations,
            "memory_accesses": self._memory_accesses,
            "tool_invocation_count": len(self._tool_invocations),
            "memory_access_count": len(self._memory_accesses),
        }

        stable_payload = {
            "agent_id": snapshot["agent_id"],
            "agent_type": snapshot["agent_type"],
            "manifest_hash": snapshot["manifest_hash"],
            "tenant_id": snapshot["tenant_id"],
            "trace_id": snapshot["trace_id"],
            "started_at": snapshot["started_at"],
            "tool_invocations": snapshot["tool_invocations"],
            "memory_accesses": snapshot["memory_accesses"],
        }
        snapshot["snapshot_hash"] = canonical_hash(stable_payload)
        return snapshot

    async def commit(self) -> dict[str, Any]:
        """Commit the replay snapshot as an audit event.

        Builds the snapshot, computes its canonical hash, and emits
        a REPLAY_SNAPSHOT audit event.  Uses ``await`` instead of
        ``asyncio.create_task()`` to prevent silent loss on shutdown.

        Returns:
            The committed snapshot dictionary.

        Raises:
            RuntimeError: If commit() is called more than once.
        """
        if self._committed:
            raise RuntimeError("ReplayRecorder.commit() already called for this run")

        snapshot = self.build_snapshot()

        record = ReplaySnapshotRecord(
            agent_id=self._agent_id,
            agent_type=self._agent_type,
            manifest_hash=snapshot["manifest_hash"],
            snapshot_hash=snapshot["snapshot_hash"],
            tool_invocation_count=snapshot["tool_invocation_count"],
            memory_access_count=snapshot["memory_access_count"],
            tenant_id=self._tenant_id,
            trace_id=self._trace_id,
        )

        # CRITICAL: Use await, not asyncio.create_task(), to prevent
        # silent loss of replay snapshots on shutdown.
        await emit_audit_event(
            action=AuditAction.REPLAY_SNAPSHOT,
            outcome=AuditOutcome.SUCCESS,
            resource_type="agent_run",
            resource_id=self._agent_id,
            request_id=self._trace_id,
            details=record.model_dump(),
            chain_id=f"{self._tenant_id or 'global'}:replay:{self._agent_type}",
        )

        self._committed = True

        logger.info(
            "Replay snapshot committed: agent=%s hash=%s tools=%d memory=%d",
            self._agent_id,
            snapshot["snapshot_hash"][:12],
            snapshot["tool_invocation_count"],
            snapshot["memory_access_count"],
        )

        return snapshot
