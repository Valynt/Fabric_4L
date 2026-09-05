"""Dialect-aware converging upsert for the durable runtime adapters.

``save`` on the Postgres-backed memory/checkpoint adapters must be a single
atomic statement: the legacy SELECT-then-INSERT pattern raced under concurrent
saves (two sessions could both miss, both insert, and one would abort on the
composite UNIQUE constraint). On PostgreSQL and SQLite an
``INSERT ... ON CONFLICT DO UPDATE`` removes the race entirely. Dialects
without a native upsert fall back to a converging INSERT-then-UPDATE retry
loop; the composite UNIQUE constraint still guarantees exactly one row
survives, and a conflict loser re-reads the winner's row and updates it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence

from sqlalchemy import Table, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import Executable

__all__ = ["NATIVE_UPSERT_DIALECTS", "upsert_row"]

NATIVE_UPSERT_DIALECTS = frozenset({"postgresql", "sqlite"})

TenantContextSetter = Callable[[AsyncSession], Awaitable[None]]

RowValues = Mapping[str, object]


def _dialect_name(session: AsyncSession) -> str:
    bind = getattr(session.sync_session, "bind", None)
    dialect = getattr(bind, "dialect", None)
    return str(getattr(dialect, "name", "") or "")


def _native_upsert_stmt(
    *,
    dialect_name: str,
    table: Table,
    values: RowValues,
    conflict_columns: Sequence[str],
    update_values: RowValues,
) -> Executable:
    # The sqlite and postgresql insert builders return sibling Insert
    # subclasses (no shared on_conflict_do_update base), so each dialect
    # branch returns its own fully built statement.
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        return sqlite_insert(table).values(**values).on_conflict_do_update(
            index_elements=list(conflict_columns), set_=dict(update_values)
        )
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    return pg_insert(table).values(**values).on_conflict_do_update(
        index_elements=list(conflict_columns), set_=dict(update_values)
    )


async def upsert_row(
    session: AsyncSession,
    *,
    table: Table,
    values: RowValues,
    conflict_columns: Sequence[str],
    update_values: RowValues,
    enter_tenant_context: TenantContextSetter,
    max_attempts: int = 3,
) -> None:
    """Persist ``values`` as one row, converging on composite-key conflicts.

    Native dialects (PostgreSQL, SQLite) issue a single atomic
    ``INSERT ... ON CONFLICT DO UPDATE``. Other dialects converge via
    INSERT-then-UPDATE retry bounded by ``max_attempts``; the composite
    UNIQUE constraint makes duplicate rows unrepresentable, so a failed
    insert always means a concurrent writer won and the update path
    re-reads and overwrites that row.
    """
    dialect_name = _dialect_name(session)
    if dialect_name in NATIVE_UPSERT_DIALECTS:
        async with session.begin():
            await enter_tenant_context(session)
            await session.execute(
                _native_upsert_stmt(
                    dialect_name=dialect_name,
                    table=table,
                    values=values,
                    conflict_columns=conflict_columns,
                    update_values=update_values,
                )
            )
        return

    last_error: IntegrityError | None = None
    for _ in range(max_attempts):
        try:
            async with session.begin():
                await enter_tenant_context(session)
                await session.execute(insert(table).values(**values))
            return
        except IntegrityError as exc:
            # A concurrent writer inserted the row first; the transaction has
            # been rolled back and the session is reusable for the update.
            last_error = exc
        async with session.begin():
            await enter_tenant_context(session)
            conditions = [table.c[column] == values[column] for column in conflict_columns]
            result = await session.execute(
                update(table).where(*conditions).values(**update_values)
            )
            if getattr(result, "rowcount", 0):
                return
    if last_error is not None:
        raise last_error
    raise RuntimeError("upsert_row failed to converge within its retry budget")
