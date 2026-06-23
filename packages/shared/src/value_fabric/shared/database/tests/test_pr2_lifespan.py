"""PR2 — async PG lifespan helpers and health probe.

These tests intentionally avoid a real Postgres connection. They exercise the
adapter contract: probe returns ProbeResult with healthy=False on failure and
healthy=True on success, without raising.
"""

from __future__ import annotations

import pytest

from value_fabric.shared.database.lifespan import (
    PgRuntime,
    PostgresHealthProbe,
)
from value_fabric.shared.fastapi_framework.health import ProbeResult


class _FakeEngine:
    def __init__(self, *, ok: bool = True, raises: bool = False) -> None:
        self._ok = ok
        self._raises = raises

    def connect(self):  # pragma: no cover - returns ctx manager below
        engine = self

        class _Ctx:
            async def __aenter__(self_inner):  # noqa: N805
                if engine._raises:
                    raise RuntimeError("connect failed")
                return self_inner

            async def __aexit__(self_inner, exc_type, exc, tb):  # noqa: N805
                return False

            async def execute(self_inner, _stmt):  # noqa: N805
                if not engine._ok:
                    from sqlalchemy.exc import SQLAlchemyError

                    raise SQLAlchemyError("select failed")
                return None

        return _Ctx()


@pytest.mark.asyncio
async def test_postgres_health_probe_healthy() -> None:
    probe = PostgresHealthProbe(_FakeEngine(ok=True))  # type: ignore[arg-type]
    result = await probe.check()
    assert isinstance(result, ProbeResult)
    assert result.healthy is True
    assert result.name == "postgres"


@pytest.mark.asyncio
async def test_postgres_health_probe_unhealthy_on_query_error() -> None:
    probe = PostgresHealthProbe(_FakeEngine(ok=False))  # type: ignore[arg-type]
    result = await probe.check()
    assert result.healthy is False
    assert result.detail == "select_1_failed"


@pytest.mark.asyncio
async def test_postgres_health_probe_catches_connect_error() -> None:
    # Connect-time failures are expected operational conditions.
    # The probe must report unhealthy rather than raise.
    probe = PostgresHealthProbe(_FakeEngine(raises=True))  # type: ignore[arg-type]
    result = await probe.check()
    assert result.healthy is False
    assert result.detail == "health_check_failed"


def test_pgruntime_dataclass_shape() -> None:
    rt = PgRuntime.__dataclass_fields__  # type: ignore[attr-defined]
    assert {"engine", "session_maker", "dsn"}.issubset(set(rt.keys()))
