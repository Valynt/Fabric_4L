from __future__ import annotations

"""Canonical endpoint surface regression tests for Layer 3 route normalization.

Validates that the double-prefix bugs are fixed and legacy aliases remain governed.
"""


import pytest

from src.api.routes.entities import router as entities_router
from src.api.routes.calculators import router as calculators_router
from src.api.routes.graph_viz import router as graph_viz_router


@pytest.mark.unit
def test_entities_router_uses_entities_prefix() -> None:
    """entities.py must define prefix='/entities' so main.py mount with '/v1' yields '/v1/entities'."""
    assert entities_router.prefix == "/entities", f"Unexpected prefix: {entities_router.prefix!r}"


@pytest.mark.unit
def test_calculators_router_uses_calculators_prefix() -> None:
    """calculators.py must define prefix='/calculators' so main.py mount with '/v1' yields '/v1/calculators'."""
    assert calculators_router.prefix == "/calculators", f"Unexpected prefix: {calculators_router.prefix!r}"


@pytest.mark.unit
def test_graph_viz_router_uses_v1_prefix() -> None:
    """graph_viz.py must define prefix='/v1' and be mounted without extra prefix in main.py."""
    assert graph_viz_router.prefix == "/v1", f"Unexpected prefix: {graph_viz_router.prefix!r}"


@pytest.mark.unit
def test_entities_routes_are_canonical() -> None:
    paths = {route.path for route in entities_router.routes}
    assert "/entities/" in paths
    assert "/entities/{entity_id}" in paths
    assert "/entities/query" in paths
    assert "/entities/traverse" in paths
    # No double-prefix artifacts inside the router
    assert "/v1/entities" not in paths
    assert "/v1/v1" not in paths


@pytest.mark.unit
def test_calculators_routes_are_canonical() -> None:
    paths = {route.path for route in calculators_router.routes}
    assert "/calculators/levers" in paths
    assert "/calculators/value-cases" in paths
    assert "/calculators/value-cases/{case_id}" in paths
    # No double-prefix artifacts inside the router
    assert "/v1/calculators" not in paths
    assert "/v1/v1" not in paths


@pytest.mark.unit
def test_graph_viz_routes_are_canonical() -> None:
    paths = {route.path for route in graph_viz_router.routes}
    assert "/v1/graph" in paths
    assert "/v1/entities/{entity_id}/subgraph" in paths
    assert "/v1/graph/subgraph" in paths
    # Mixed prefixing fixed
    assert "/v1/v1/graph/subgraph" not in paths
