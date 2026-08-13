"""Regression protection: CheckpointConfig.create_saver must provision the
LangGraph checkpoint tables.

Failure mode covered: create_saver() constructed an AsyncPostgresSaver but
never awaited setup(), so live workflow execution crashed with
``relation "checkpoints" does not exist`` (observed via the Meridian
certification journey, 2026-08-12). setup() is idempotent and is the
canonical LangGraph provisioning step.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from layer4_agents.config.checkpoint import CheckpointConfig


@pytest.mark.asyncio
async def test_create_saver_provisions_checkpoint_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_saver must call saver.setup() so checkpoint tables exist."""
    fake_conn = AsyncMock()
    fake_saver = Mock()
    fake_saver.setup = AsyncMock()

    monkeypatch.setenv("CHECKPOINT_DATABASE_URL", "postgresql://localhost:5432/checkpoints")

    import psycopg  # noqa: PLC0415

    monkeypatch.setattr(
        psycopg.AsyncConnection,
        "connect",
        AsyncMock(return_value=fake_conn),
    )
    # create_saver lazily imports AsyncPostgresSaver from this module at call
    # time, so patching the attribute here intercepts the construction.
    import langgraph.checkpoint.postgres.aio as aio_mod  # noqa: PLC0415

    monkeypatch.setattr(aio_mod, "AsyncPostgresSaver", Mock(return_value=fake_saver))

    saver = await CheckpointConfig.create_saver()

    fake_saver.setup.assert_awaited_once()
    assert saver is fake_saver
