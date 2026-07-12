"""No-infra adapter contract tests for dependency probes and gate messaging.

These tests run without Postgres/Redis/Neo4j and validate the behavioral contract
for infrastructure probes and gate reasons using mocks/fakes.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def root_conftest() -> Any:
    """Load and return the root conftest module for testing.
    
    This fixture encapsulates the complex module loading logic to improve
    test maintainability and prevent brittleness from conftest refactors.
    """
    _ROOT_CONFTEST_PATH = Path(__file__).resolve().parents[1] / "conftest.py"
    _SPEC = spec_from_file_location("root_tests_conftest", _ROOT_CONFTEST_PATH)
    assert _SPEC and _SPEC.loader
    module = module_from_spec(_SPEC)
    sys.modules[_SPEC.name] = module
    _SPEC.loader.exec_module(module)
    return module


@pytest.mark.parametrize("dependency_key", ["postgres", "redis", "neo4j"])
def test_skip_reason_contains_command_and_categories(root_conftest: Any, dependency_key: str) -> None:
    reason = root_conftest.make_infra_skip_reason(dependency_key)
    metadata = root_conftest.INFRA_DEPENDENCIES[dependency_key]

    assert f"[INFRA_GATE:{metadata.display_name.upper()}]" in reason
    assert metadata.startup_command in reason
    for category in metadata.categories:
        assert category in reason


def test_check_postgres_contract_with_fake_psycopg2(root_conftest: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connect = Mock()
    fake_connect.return_value.close = Mock()
    fake_psycopg2 = Mock(connect=fake_connect)

    monkeypatch.setitem(__import__("sys").modules, "psycopg2", fake_psycopg2)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://example:5432/test_db")

    assert root_conftest._check_postgres() is True
    fake_connect.assert_called_once_with("postgresql://example:5432/test_db")


def test_check_redis_contract_with_fake_client(root_conftest: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = Mock()
    fake_redis_module = Mock()
    fake_redis_module.Redis.return_value = fake_client

    monkeypatch.setitem(__import__("sys").modules, "redis", fake_redis_module)
    monkeypatch.setenv("REDIS_HOST", "redis-host")
    monkeypatch.setenv("REDIS_PORT", "6390")

    assert root_conftest._check_redis() is True
    fake_redis_module.Redis.assert_called_once_with(host="redis-host", port=6390, db=0)
    fake_client.ping.assert_called_once_with()
    fake_client.close.assert_called_once_with()


def test_check_neo4j_contract_with_fake_driver(root_conftest: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_driver = Mock()
    fake_graph_database = Mock()
    fake_graph_database.driver.return_value = fake_driver

    monkeypatch.setitem(__import__("sys").modules, "neo4j", Mock(GraphDatabase=fake_graph_database))
    monkeypatch.setenv("NEO4J_URI", "bolt://neo4j-host:9999")
    monkeypatch.setenv("NEO4J_USER", "neo-user")
    monkeypatch.setenv("NEO4J_PASSWORD", "neo-pass")

    assert root_conftest._check_neo4j() is True
    fake_graph_database.driver.assert_called_once_with(
        "bolt://neo4j-host:9999", auth=("neo-user", "neo-pass")
    )
    fake_driver.verify_connectivity.assert_called_once_with()
    fake_driver.close.assert_called_once_with()
