from unittest.mock import AsyncMock, MagicMock

import layer6_benchmarks.api.main as main_module
import pytest
from layer6_benchmarks.api.startup_logging import config_fingerprint, emit_startup_metadata


def test_config_fingerprint_is_stable() -> None:
    left = config_fingerprint({"a": 1, "b": "x"})
    right = config_fingerprint({"b": "x", "a": 1})
    assert left == right
    assert len(left) == 16


def test_emit_startup_metadata_logs_version_and_build(caplog) -> None:
    with caplog.at_level("INFO", logger="layer6.startup"):
        emit_startup_metadata(
            service="layer6-benchmarks",
            version="1.2.3",
            build_sha="abc123",
            config={"feature_flag": "on"},
        )

    assert any(
        rec.name == "layer6.startup"
        and getattr(rec, "service", None) == "layer6-benchmarks"
        and getattr(rec, "version", None) == "1.2.3"
        and getattr(rec, "build_sha", None) == "abc123"
        and getattr(rec, "config_fingerprint", None)
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_lifespan_emits_startup_metadata(monkeypatch) -> None:
    emit_mock = MagicMock()
    monkeypatch.setattr(main_module, "emit_startup_metadata", emit_mock)
    monkeypatch.setattr(
        main_module, "get_driver", AsyncMock(side_effect=RuntimeError("neo4j unavailable"))
    )
    monkeypatch.setattr(main_module, "close_driver", AsyncMock())
    original_startup_error = main_module._neo4j_startup_error

    async with main_module.lifespan(main_module.app):
        pass

    emit_mock.assert_called_once()
    _, kwargs = emit_mock.call_args
    assert kwargs["service"] == "layer6-benchmarks"
    assert kwargs["version"]
    assert kwargs["build_sha"]
    assert "database_scheme" in kwargs["config"]
    main_module._neo4j_startup_error = original_startup_error


@pytest.mark.asyncio
async def test_lifespan_does_not_leak_raw_exception_to_health_check(monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_driver",
        AsyncMock(side_effect=RuntimeError("connection refused: neo4j://secret-host:7687")),
    )
    monkeypatch.setattr(main_module, "close_driver", AsyncMock())
    monkeypatch.setattr(main_module, "_init_seed_data", AsyncMock())
    original_startup_error = main_module._neo4j_startup_error
    main_module._neo4j_startup_error = None

    async with main_module.lifespan(main_module.app):
        pass

    assert main_module._neo4j_startup_error is not None
    assert "secret-host" not in main_module._neo4j_startup_error
    assert "Neo4j benchmark store unavailable" in main_module._neo4j_startup_error
    main_module._neo4j_startup_error = original_startup_error
