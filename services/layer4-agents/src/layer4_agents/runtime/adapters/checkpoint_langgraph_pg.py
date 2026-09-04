"""Postgres-backed :class:`CheckpointPort` adapter (SQLite-compatible for tests).

Durable drop-in replacement for :class:`InMemoryCheckpointAdapter`. Checkpoints
are stored keyed by composite ``(tenant_id, run_id, thread_id, checkpoint_id)``
with an integer ``seq`` surrogate carrying deterministic save-order /
latest-wins semantics. ``Checkpoint.created_at`` is persisted as its original
ISO-8601 string so ``load`` reconstructs the exact value with no timezone
reformatting.

The adapter is session-agnostic: it receives an ``async_sessionmaker`` and
opens a session per operation.
"""

from __future__ import annotations

import copy
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import TenantRequiredError
from ..models import Checkpoint
from ..orm import RuntimeCheckpointRow
from ..ports import CheckpointPort


def _row_to_checkpoint(row: RuntimeCheckpointRow) -> Checkpoint:
    return Checkpoint(
        checkpoint_id=row.checkpoint_id,
        run_id=row.run_id,
        thread_id=row.thread_id,
        tenant_id=row.tenant_id,
        state_hash=row.state_hash,
        created_at=row.created_at,
        metadata=copy.deepcopy(row.metadata_json) if row.metadata_json is not None else None,
    )


class PostgresCheckpointAdapter(CheckpointPort):
    """Durable checkpoints backed by ``runtime_checkpoints``."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        tenant_context_setter: Callable[[AsyncSession, str], Awaitable[None]] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._tenant_context_setter = tenant_context_setter

    async def _enter_tenant_context(self, session: AsyncSession, tenant_id: str) -> None:
        """Establish tenant context on the session when a production hook is configured.

        The shared service session factory yields tenant-enforced sessions that
        fail closed on any statement executed without tenant context (marks the
        session and sets the RLS ``app.tenant_id`` variable). Standalone SQLite
        tests inject no hook and keep plain sessions.
        """
        if self._tenant_context_setter is not None:
            await self._tenant_context_setter(session, tenant_id)

    async def save(self, checkpoint: Checkpoint, state: dict[str, Any]) -> None:
        if not checkpoint.tenant_id:
            raise TenantRequiredError(details={"checkpoint_id": checkpoint.checkpoint_id})
        async with self._session_factory() as session:
            async with session.begin():
                await self._enter_tenant_context(session, checkpoint.tenant_id)
                existing = await session.scalar(
                    select(RuntimeCheckpointRow).where(
                        RuntimeCheckpointRow.tenant_id == checkpoint.tenant_id,
                        RuntimeCheckpointRow.run_id == checkpoint.run_id,
                        RuntimeCheckpointRow.thread_id == checkpoint.thread_id,
                        RuntimeCheckpointRow.checkpoint_id == checkpoint.checkpoint_id,
                    )
                )
                if existing is None:
                    session.add(
                        RuntimeCheckpointRow(
                            checkpoint_id=checkpoint.checkpoint_id,
                            run_id=checkpoint.run_id,
                            thread_id=checkpoint.thread_id,
                            tenant_id=checkpoint.tenant_id,
                            state_hash=checkpoint.state_hash,
                            state=copy.deepcopy(state),
                            metadata_json=copy.deepcopy(checkpoint.metadata)
                            if checkpoint.metadata is not None
                            else None,
                            created_at=checkpoint.created_at,
                        )
                    )
                else:
                    existing.state_hash = checkpoint.state_hash
                    existing.state = copy.deepcopy(state)
                    existing.metadata_json = (
                        copy.deepcopy(checkpoint.metadata)
                        if checkpoint.metadata is not None
                        else None
                    )
                    existing.created_at = checkpoint.created_at

    async def load(
        self,
        run_id: str,
        thread_id: str,
        tenant_id: str,
        *,
        checkpoint_id: str | None = None,
    ) -> tuple[Checkpoint, dict[str, Any]] | None:
        if not tenant_id:
            raise TenantRequiredError(details={"run_id": run_id, "thread_id": thread_id})
        stmt = select(RuntimeCheckpointRow).where(
            RuntimeCheckpointRow.tenant_id == tenant_id,
            RuntimeCheckpointRow.run_id == run_id,
            RuntimeCheckpointRow.thread_id == thread_id,
        )
        if checkpoint_id is not None:
            stmt = stmt.where(RuntimeCheckpointRow.checkpoint_id == checkpoint_id)
        stmt = stmt.order_by(RuntimeCheckpointRow.seq.desc()).limit(1)
        async with self._session_factory() as session:
            await self._enter_tenant_context(session, tenant_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _row_to_checkpoint(row), copy.deepcopy(row.state)

    async def list(self, run_id: str, tenant_id: str) -> list[Checkpoint]:
        if not tenant_id:
            raise TenantRequiredError(details={"run_id": run_id})
        stmt = (
            select(RuntimeCheckpointRow)
            .where(
                RuntimeCheckpointRow.tenant_id == tenant_id,
                RuntimeCheckpointRow.run_id == run_id,
            )
            .order_by(RuntimeCheckpointRow.seq.asc())
        )
        async with self._session_factory() as session:
            await self._enter_tenant_context(session, tenant_id)
            rows = (await session.execute(stmt)).scalars().all()
        return [_row_to_checkpoint(row) for row in rows]
