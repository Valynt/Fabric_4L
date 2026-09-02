"""In-memory CheckpointPort adapter for hermetic tests and ephemeral stores.

Stores checkpoints keyed by ``(tenant_id, run_id, thread_id, checkpoint_id)``.
All lookups are tenant-scoped and fail closed: a run that was saved under a
different tenant is simply invisible to ``load``/``list``.
"""

from __future__ import annotations

import copy
from typing import Any

from ..errors import TenantRequiredError
from ..models import Checkpoint
from ..ports import CheckpointPort


class InMemoryCheckpointAdapter(CheckpointPort):
    """Tenant-scoped CheckpointPort backed by an in-process dict."""

    def __init__(self) -> None:
        self._rows: list[
            tuple[tuple[str, str, str, str], Checkpoint, dict[str, Any]]
        ] = []
        self._index: dict[tuple[str, str, str, str], int] = {}

    async def save(self, checkpoint: Checkpoint, state: dict[str, Any]) -> None:
        """Persist a checkpoint (insert or replace by composite key)."""
        if not checkpoint.tenant_id:
            raise TenantRequiredError(
                details={"checkpoint_id": checkpoint.checkpoint_id}
            )
        key = (
            checkpoint.tenant_id,
            checkpoint.run_id,
            checkpoint.thread_id,
            checkpoint.checkpoint_id,
        )
        row = (key, checkpoint.model_copy(deep=True), copy.deepcopy(state))
        if key in self._index:
            self._rows[self._index[key]] = row
        else:
            self._index[key] = len(self._rows)
            self._rows.append(row)

    async def load(
        self,
        run_id: str,
        thread_id: str,
        tenant_id: str,
        *,
        checkpoint_id: str | None = None,
    ) -> tuple[Checkpoint, dict[str, Any]] | None:
        """Load the named checkpoint, or the latest one for the run/thread.

        Returns ``None`` when nothing is visible to the requesting tenant.
        """
        matching = [
            row
            for row in self._rows
            if row[0][0] == tenant_id and row[0][1] == run_id and row[0][2] == thread_id
        ]
        if checkpoint_id is not None:
            matching = [row for row in matching if row[0][3] == checkpoint_id]
        if not matching:
            return None
        _key, checkpoint, state = matching[-1]
        return checkpoint.model_copy(deep=True), copy.deepcopy(state)

    async def list(self, run_id: str, tenant_id: str) -> list[Checkpoint]:
        """List checkpoints for a run in save order, scoped to the tenant."""
        return [
            row[1].model_copy(deep=True)
            for row in self._rows
            if row[0][0] == tenant_id and row[0][1] == run_id
        ]
