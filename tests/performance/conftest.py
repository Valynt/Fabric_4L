"""Shared fixtures for performance tests."""

import os

import pytest


def infrastructure_available() -> bool:
    """Check if required infrastructure is available for performance tests.
    
    Returns True if RUN_INFRA_TESTS=1 is set, indicating the user has
    explicitly started the required services (Postgres, Redis, Neo4j).
    """
    return os.environ.get("RUN_INFRA_TESTS") == "1"


def pytest_configure(config):
    """Add custom markers for performance tests."""
    config.addinivalue_line(
        "markers",
        "requires_infra: Tests that require live infrastructure (Postgres, Redis, Neo4j)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skip requires_infra tests when infrastructure is unavailable."""
    if not infrastructure_available():
        for item in items:
            if item.get_closest_marker("requires_infra"):
                item.add_marker(
                    pytest.mark.skipif(
                        True,
                        reason="Postgres/Redis/Neo4j unavailable; set RUN_INFRA_TESTS=1 and start services to run this test"
                    )
                )
