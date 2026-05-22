"""Pytest configuration for Value Fabric Layer 3 tests.

sys.path setup
--------------
services/layer3-knowledge/src is inserted at position 0 so that bare
``from config import Settings`` and ``from api import ...`` imports in
layer3 source files resolve to the layer3 package, not to layer4-agents/src
which also has a ``config`` module.

This resolves the config.Settings namespace collision described in the
Phase 1.2 import topology fix (spec.md §1.2).
"""

import os
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent

# Layer 3 src must be first so its `config` package shadows layer4's.
# Always remove any existing occurrence then reinsert at 0 to guarantee priority.
_L3_SRC = _HERE / "src"
_l3_str = str(_L3_SRC)
sys.path = [p for p in sys.path if p != _l3_str]
sys.path.insert(0, _l3_str)

# Repo root for value_fabric.* namespace packages.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(_REPO_ROOT))

# Set test environment variables
os.environ.setdefault("NEO4J_PASSWORD", "test_password")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "requires_neo4j: mark test as requiring Neo4j"
    )
    config.addinivalue_line(
        "markers", "requires_prometheus: mark test as requiring Prometheus"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add unit marker to tests in test_*.py files that don't require external services
        if "test_" in item.nodeid and not any(
            marker in item.nodeid for marker in ["redis", "neo4j", "prometheus"]
        ):
            item.add_marker(pytest.mark.unit)

        # Add integration marker for tests that test multiple components
        if "integration" in item.nodeid or "endpoint" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Add slow marker for tests that might take longer
        if "slow" in item.nodeid or "performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
