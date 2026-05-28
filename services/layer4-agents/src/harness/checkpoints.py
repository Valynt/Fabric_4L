from __future__ import annotations

"""
Deterministic checkpointing for HarnessRun state snapshots.

Invariants:
  - tenant_id and run_id are always present.
  - Same payload produces the same hash (deterministic).
  - Changed payload produces a different hash.
  - Cross-tenant checkpoint access is rejected.
"""


from typing import Any

from .models import HarnessCheckpoint, HarnessState, ToolCallRef


class CheckpointError(ValueError):
    """Raised when a checkpoint operation is invalid."""

    pass


class CheckpointTenantError(CheckpointError):
    """Raised when a checkpoint tenant does not match."""

    pass


class CheckpointManager:
    """
    In-memory checkpoint manager with deterministic hashing.

    Production upgrade: persist to SQL with (run_id, tenant_id) composite key.
    """

    def __init__(self) -> None:
        # Primary store: checkpoint_id -> HarnessCheckpoint
        self._checkpoints: dict[str, HarnessCheckpoint] = {}
        # Run index: run_id -> ordered list of checkpoint_ids
        self._run_checkpoints: dict[str, list[str]] = {}

    def create_checkpoint(
        self,
        run_id: str,
        tenant_id: str,
        state_name: HarnessState,
        state_payload: dict[str, Any],
        tool_calls: list[ToolCallRef] | None = None,
        output_hash: str | None = None,
    ) -> HarnessCheckpoint:
        """
        Create a deterministic checkpoint.

        The input_hash is deterministically computed from the payload.
        """
        if not run_id or not run_id.strip():
            raise CheckpointError("run_id is required and must be non-empty")
        if not tenant_id or not tenant_id.strip():
            raise CheckpointError("tenant_id is required and must be non-empty")

        tool_calls = tool_calls or []

        input_hash = HarnessCheckpoint.compute_input_hash(
            run_id=run_id,
            tenant_id=tenant_id,
            state_name=state_name,
            state_payload=state_payload,
            tool_calls=tool_calls,
        )

        checkpoint = HarnessCheckpoint(
            run_id=run_id,
            tenant_id=tenant_id,
            state_name=state_name,
            state_payload=state_payload,
            input_hash=input_hash,
            output_hash=output_hash,
            tool_calls=tool_calls,
        )

        self._checkpoints[checkpoint.id] = checkpoint
        self._run_checkpoints.setdefault(run_id, []).append(checkpoint.id)

        return checkpoint

    def get_checkpoint(self, checkpoint_id: str, run_id: str, tenant_id: str) -> HarnessCheckpoint:
        """
        Retrieve a checkpoint with run and tenant verification.

        Raises:
            CheckpointError: if checkpoint not found.
            CheckpointTenantError: if tenant or run mismatch.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            raise CheckpointError(f"Checkpoint '{checkpoint_id}' not found")

        if checkpoint.run_id != run_id:
            raise CheckpointTenantError(
                f"Checkpoint '{checkpoint_id}' run_id mismatch: "
                f"expected {run_id}, got {checkpoint.run_id}"
            )

        if checkpoint.tenant_id != tenant_id:
            raise CheckpointTenantError(
                f"Checkpoint '{checkpoint_id}' tenant_id mismatch: "
                f"expected {tenant_id}, got {checkpoint.tenant_id}"
            )

        return checkpoint

    def list_checkpoints_for_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> list[HarnessCheckpoint]:
        """List checkpoints for a run, ordered by creation."""
        checkpoint_ids = self._run_checkpoints.get(run_id, [])
        result: list[HarnessCheckpoint] = []
        for cid in checkpoint_ids:
            cp = self._checkpoints.get(cid)
            if cp is not None and cp.tenant_id == tenant_id:
                result.append(cp)
        return result

    def get_latest_checkpoint(
        self,
        run_id: str,
        tenant_id: str,
    ) -> HarnessCheckpoint | None:
        """Get the most recent checkpoint for a run."""
        checkpoints = self.list_checkpoints_for_run(run_id, tenant_id)
        return checkpoints[-1] if checkpoints else None

    def verify_payload_unchanged(
        self,
        checkpoint: HarnessCheckpoint,
        state_payload: dict[str, Any],
    ) -> bool:
        """
        Verify that the given payload matches the checkpoint's stored hash.

        Returns True if the payload matches (hashes are equal).
        """
        current_hash = HarnessCheckpoint.compute_input_hash(
            run_id=checkpoint.run_id,
            tenant_id=checkpoint.tenant_id,
            state_name=checkpoint.state_name,
            state_payload=state_payload,
            tool_calls=list(checkpoint.tool_calls),
        )
        return current_hash == checkpoint.input_hash
