"""Postgres-backed :class:`MemoryPort` adapter (SQLite-compatible for tests).

Durable drop-in replacement for :class:`InMemoryMemoryAdapter`. Thread state is
stored one row per ``(tenant_id, thread_id)`` (latest write wins via upsert);
long-term records live in an append-only pool and are matched by a
case-insensitive substring search over a precomputed, case-folded JSON
representation — mirroring the in-memory adapter's semantics.

The adapter is session-agnostic: it receives an ``async_sessionmaker`` and
opens a session per operation, so it is safe to reuse across requests and
threads.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import TenantRequiredError
from ..orm import RuntimeLongTermMemoryRow, RuntimeThreadStateRow
from ..ports import MemoryPort


def _fold_record(record: dict[str, Any]) -> str:
    """Return the case-folded JSON haystack for a long-term record."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False, default=str).casefold()


class PostgresMemoryAdapter(MemoryPort):
    """Durable memory backed by ``runtime_thread_states`` / ``runtime_long_term_memory``."""

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

    async def get_thread_state(self, thread_id: str, tenant_id: str) -> dict[str, Any] | None:
        if not tenant_id:
            raise TenantRequiredError(details={"thread_id": thread_id})
        stmt = (
            select(RuntimeThreadStateRow)
            .where(
                RuntimeThreadStateRow.tenant_id == tenant_id,
                RuntimeThreadStateRow.thread_id == thread_id,
            )
            .order_by(RuntimeThreadStateRow.updated_at.desc())
            .limit(1)
        )
        async with self._session_factory() as session:
            await self._enter_tenant_context(session, tenant_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
        return None if row is None else copy.deepcopy(row.state)

    async def save_thread_state(self, thread_id: str, tenant_id: str, state: dict[str, Any]) -> None:
        if not tenant_id:
            raise TenantRequiredError(details={"thread_id": thread_id})
        async with self._session_factory() as session:
            async with session.begin():
                await self._enter_tenant_context(session, tenant_id)
                existing = await session.scalar(
                    select(RuntimeThreadStateRow).where(
                        RuntimeThreadStateRow.tenant_id == tenant_id,
                        RuntimeThreadStateRow.thread_id == thread_id,
                    )
                )
                if existing is None:
                    session.add(
                        RuntimeThreadStateRow(
                            tenant_id=tenant_id,
                            thread_id=thread_id,
                            state=copy.deepcopy(state),
                        )
                    )
                else:
                    existing.state = copy.deepcopy(state)  # updated_at refreshed via onupdate

    async def search_long_term(
        self, query: str, tenant_id: str, *, limit: int = 10
    ) -> list[dict[str, Any]]:
        if not tenant_id:
            raise TenantRequiredError()
        if limit <= 0:
            return []
        needle = query.casefold()
        stmt = (
            select(RuntimeLongTermMemoryRow)
            .where(
                RuntimeLongTermMemoryRow.tenant_id == tenant_id,
                RuntimeLongTermMemoryRow.content.contains(needle),
            )
            .order_by(RuntimeLongTermMemoryRow.seq.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            await self._enter_tenant_context(session, tenant_id)
            rows = (await session.execute(stmt)).scalars().all()
        return [copy.deepcopy(row.record) for row in rows]

    async def add_long_term(self, tenant_id: str, record: dict[str, Any]) -> None:
        """Index a long-term memory record (adapter extension seam, mirrors in-memory)."""
        if not tenant_id:
            raise TenantRequiredError()
        async with self._session_factory() as session:
            async with session.begin():
                await self._enter_tenant_context(session, tenant_id)
                session.add(
                    RuntimeLongTermMemoryRow(
                        tenant_id=tenant_id,
                        content=_fold_record(record),
                        record=copy.deepcopy(record),
                    )
                )
