"""Root pytest entrypoint for the Fabric_4L monorepo.

Volatile bootstrap and policy logic lives in ``tests.support`` so this file
stays stable despite repository-wide test and layer changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.layer3_api_helpers import (
    TestUtils,
    create_mock_graphrag_response,
    create_mock_search_response,
)
from tests.support.root_pytest_bootstrap import bootstrap_root_pytest
from tests.support.root_pytest_policy import (
    add_root_pytest_options,
    apply_collection_markers,
    enforce_mandatory_dependencies,
)

if TYPE_CHECKING:
    from _pytest.config import Config, Parser
    from _pytest.nodes import Item

bootstrap_root_pytest()


def pytest_addoption(parser: "Parser") -> None:
    """Add repository-level pytest options."""
    add_root_pytest_options(parser)


def pytest_configure(config: "Config") -> None:
    """Fail fast when mandatory test dependencies are missing."""
    enforce_mandatory_dependencies(config)


def pytest_collection_modifyitems(config: "Config", items: list["Item"]) -> None:
    """Apply repository-level marker policy after collection."""
    apply_collection_markers(items)


__all__ = [
    "TestUtils",
    "create_mock_graphrag_response",
    "create_mock_search_response",
]
