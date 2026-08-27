"""Comprehensive unit tests for graph_viz.py refactored methods.

This test file provides direct coverage for the graph visualization routes,
addressing the untested hotspot issue identified in health analysis.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.models import (
    GraphEdge,
    GraphNode,
    GraphNodeWithLayout,
    GraphResponse,
    SubgraphResponse,
)
from src.api.routes.graph_viz import (
    _build_graph_node,
    _calculate_density,
    _fetch_graph_edges,
    _fetch_graph_nodes,
    _fetch_graph_stats,
    _get_center_entity_subgraph,
    _get_query_search_subgraph,
    _get_root_entity,
    _record_full_graph_metrics,
    _record_subgraph_metrics,
    get_entity_subgraph,
    get_full_graph,
    get_query_subgraph,
)
from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)


@pytest.fixture
def mock_neo4j():
    """Create a mock Neo4j driver."""
    neo4j = AsyncMock()
    neo4j.execute_query = AsyncMock()
    return neo4j


@pytest.fixture
def mock_app_state():
    """Create a mock app state."""
    state = MagicMock()
    state.neo4j_driver = AsyncMock()
    return state


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for testing."""
    return "12345678-1234-5678-1234-567812345678"


class TestBuildGraphNode:
    """Tests for _build_graph_node helper function."""

    def test_build_basic_graph_node(self):
        """Test building a basic graph node without layout."""
        node = _build_graph_node(
            node_id="node-1",
            label="Test Node",
            node_type="Entity",
            confidence=0.9,
        )
        assert isinstance(node, GraphNode)
        assert node.id == "node-1"
        assert node.label == "Test Node"
        assert node.type == "Entity"
        assert node.confidence == 0.9

    def test_build_graph_node_with_layout(self):
        """Test building a graph node with layout coordinates."""
        node = _build_graph_node(
            node_id="node-1",
            label="Test Node",
            node_type="Entity",
            confidence=0.9,
            x=100.0,
            y=200.0,
            r=10.0,
        )
        assert isinstance(node, GraphNodeWithLayout)
        assert node.id == "node-1"
        assert node.x == 100.0
        assert node.y == 200.0
        assert node.r == 10.0

    def test_build_graph_node_with_properties(self):
        """Test building a graph node with custom properties."""
        node = _build_graph_node(
            node_id="node-1",
            label="Test Node",
            node_type="Entity",
            properties={"custom_field": "value"},
        )
        assert node.properties == {"custom_field": "value"}


class TestCalculateDensity:
    """Tests for _calculate_density helper function."""

    def test_density_zero_nodes(self):
        """Test density calculation with zero nodes."""
        assert _calculate_density(0, 0) == 0.0

    def test_density_one_node(self):
        """Test density calculation with one node."""
        assert _calculate_density(1, 0) == 0.0

    def test_density_two_nodes_one_edge(self):
        """Test density calculation with two nodes and one edge."""
        density = _calculate_density(2, 1)
        assert density == 1.0

    def test_density_complete_graph(self):
        """Test density calculation for a complete graph."""
        # Complete graph with 4 nodes has 6 edges
        density = _calculate_density(4, 6)
        assert density == 1.0

    def test_density_sparse_graph(self):
        """Test density calculation for a sparse graph."""
        density = _calculate_density(5, 2)
        assert density == 0.2


class TestFetchGraphNodes:
    """Tests for _fetch_graph_nodes helper function."""

    @pytest.mark.asyncio
    async def test_fetch_graph_nodes_success(self, mock_neo4j, sample_tenant_id):
        """Test successful graph nodes fetch."""
        mock_neo4j.execute_query.return_value = [
            {"id": "node-1", "label": "Node 1", "type": "Entity", "confidence": 0.9, "x": 100.0, "y": 200.0},
            {"id": "node-2", "label": "Node 2", "type": "Entity", "confidence": 0.8, "x": None, "y": None},
        ]

        nodes, node_ids, node_types = await _fetch_graph_nodes(mock_neo4j, sample_tenant_id, 1000)

        assert len(nodes) == 2
        assert len(node_ids) == 2
        assert node_types == {"Entity": 2}
        assert "node-1" in node_ids
        assert "node-2" in node_ids

    @pytest.mark.asyncio
    async def test_fetch_graph_nodes_skips_missing_id(self, mock_neo4j, sample_tenant_id):
        """Test that nodes without ID are skipped."""
        mock_neo4j.execute_query.return_value = [
            {"id": "node-1", "label": "Node 1", "type": "Entity", "confidence": 0.9},
            {"label": "Node 2", "type": "Entity", "confidence": 0.8},  # Missing ID
        ]

        nodes, node_ids, node_types = await _fetch_graph_nodes(mock_neo4j, sample_tenant_id, 1000)

        assert len(nodes) == 1
        assert len(node_ids) == 1

    @pytest.mark.asyncio
    async def test_fetch_graph_nodes_aggregates_types(self, mock_neo4j, sample_tenant_id):
        """Test that node types are correctly aggregated."""
        mock_neo4j.execute_query.return_value = [
            {"id": "node-1", "label": "Node 1", "type": "Entity", "confidence": 0.9},
            {"id": "node-2", "label": "Node 2", "type": "Entity", "confidence": 0.8},
            {"id": "node-3", "label": "Node 3", "type": "Relationship", "confidence": 0.7},
        ]

        nodes, node_ids, node_types = await _fetch_graph_nodes(mock_neo4j, sample_tenant_id, 1000)

        assert node_types == {"Entity": 2, "Relationship": 1}

    @pytest.mark.asyncio
    async def test_fetch_graph_nodes_name_fallback_agrees(self, mock_neo4j, sample_tenant_id):
        """Node fallback name must agree across top-level label and properties.name.

        Regression for the divergence where top-level ``label`` fell back to
        ``node_id`` on a missing/None label but ``properties["name"]`` did not.
        """
        mock_neo4j.execute_query.return_value = [
            {"id": "node-1", "label": None, "type": "Entity", "confidence": 0.9},
        ]

        nodes, node_ids, node_types = await _fetch_graph_nodes(mock_neo4j, sample_tenant_id, 1000)

        assert len(nodes) == 1
        assert nodes[0].label == "node-1"
        assert nodes[0].properties.get("name") == "node-1"


class TestFetchGraphEdges:
    """Tests for _fetch_graph_edges helper function."""

    @pytest.mark.asyncio
    async def test_fetch_graph_edges_success(self, mock_neo4j, sample_tenant_id):
        """Test successful graph edges fetch."""
        node_ids = {"node-1", "node-2"}
        mock_neo4j.execute_query.return_value = [
            {"source": "node-1", "target": "node-2", "rel_type": "RELATED_TO", "weight": 1.0},
        ]

        edges = await _fetch_graph_edges(mock_neo4j, sample_tenant_id, node_ids)

        assert len(edges) == 1
        assert edges[0].source == "node-1"
        assert edges[0].target == "node-2"
        assert edges[0].type == "RELATED_TO"

    @pytest.mark.asyncio
    async def test_fetch_graph_edges_skips_invalid(self, mock_neo4j, sample_tenant_id):
        """Test that edges without source/target are skipped."""
        node_ids = {"node-1", "node-2"}
        mock_neo4j.execute_query.return_value = [
            {"source": "node-1", "target": "node-2", "rel_type": "RELATED TO", "weight": 1.0},
            {"source": None, "target": "node-2", "rel_type": "RELATED_TO", "weight": 1.0},  # Invalid
        ]

        edges = await _fetch_graph_edges(mock_neo4j, sample_tenant_id, node_ids)

        assert len(edges) == 1

    @pytest.mark.asyncio
    async def test_fetch_graph_edges_defaults_weight(self, mock_neo4j, sample_tenant_id):
        """Test that missing weight defaults to 1.0."""
        node_ids = {"node-1", "node-2"}
        mock_neo4j.execute_query.return_value = [
            {"source": "node-1", "target": "node-2", "rel_type": "RELATED_TO", "weight": None},
        ]

        edges = await _fetch_graph_edges(mock_neo4j, sample_tenant_id, node_ids)

        assert edges[0].weight == 1.0


class TestFetchGraphStats:
    """Tests for _fetch_graph_stats helper function."""

    @pytest.mark.asyncio
    async def test_fetch_graph_stats_success(self, mock_neo4j, sample_tenant_id):
        """Test successful graph stats fetch."""
        mock_neo4j.execute_query.side_effect = [
            [{"total": 100}],
            [{"total": 200}],
        ]

        total_nodes, total_edges = await _fetch_graph_stats(mock_neo4j, sample_tenant_id)

        assert total_nodes == 100
        assert total_edges == 200

    @pytest.mark.asyncio
    async def test_fetch_graph_stats_empty_results(self, mock_neo4j, sample_tenant_id):
        """Test handling of empty stats results."""
        mock_neo4j.execute_query.side_effect = [
            [],
            [],
        ]

        total_nodes, total_edges = await _fetch_graph_stats(mock_neo4j, sample_tenant_id)

        assert total_nodes == 0
        assert total_edges == 0


class TestGetRootEntity:
    """Tests for _get_root_entity helper function."""

    @pytest.mark.asyncio
    async def test_get_root_entity_success(self, mock_neo4j, sample_tenant_id):
        """Test successful root entity fetch."""
        mock_neo4j.execute_query.return_value = [
            {"id": "entity-1", "label": "Entity 1", "type": "Entity", "confidence": 0.9}
        ]

        root_record = await _get_root_entity(mock_neo4j, "entity-1", sample_tenant_id)

        assert root_record["id"] == "entity-1"
        assert root_record["label"] == "Entity 1"

    @pytest.mark.asyncio
    async def test_get_root_entity_not_found(self, mock_neo4j, sample_tenant_id):
        """Test NotFoundError when entity doesn't exist."""
        mock_neo4j.execute_query.return_value = []

        with pytest.raises(NotFoundError) as exc_info:
            await _get_root_entity(mock_neo4j, "entity-1", sample_tenant_id)

        assert "not found" in str(exc_info.value.message)


class TestGetCenterEntitySubgraph:
    """Tests for _get_center_entity_subgraph helper function."""

    @pytest.mark.asyncio
    async def test_get_center_entity_subgraph_success(self, mock_neo4j, sample_tenant_id):
        """Test successful center entity subgraph fetch."""
        mock_neo4j.execute_query.side_effect = [
            [{"id": "entity-1"}],  # Root check
            [
                {
                    "root": {"id": "entity-1", "name": "Entity 1", "entity_type": "Entity"},
                    "neighbors": [{"id": "entity-2", "name": "Entity 2", "entity_type": "Entity"}],
                    "paths": [],
                }
            ],  # Subgraph query
        ]

        nodes, edges = await _get_center_entity_subgraph(
            mock_neo4j, "entity-1", sample_tenant_id, 2, 100, None
        )

        assert len(nodes) == 2
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_get_center_entity_subgraph_not_found(self, mock_neo4j, sample_tenant_id):
        """Test NotFoundError when center entity doesn't exist."""
        mock_neo4j.execute_query.return_value = []

        with pytest.raises(NotFoundError):
            await _get_center_entity_subgraph(
                mock_neo4j, "entity-1", sample_tenant_id, 2, 100, None
            )

    @pytest.mark.asyncio
    async def test_get_center_entity_subgraph_invalid_rel_types(self, mock_neo4j, sample_tenant_id):
        """Test ValidationError when no valid relationship types provided."""
        mock_neo4j.execute_query.return_value = [{"id": "entity-1"}]

        with pytest.raises(ValidationError) as exc_info:
            await _get_center_entity_subgraph(
                mock_neo4j, "entity-1", sample_tenant_id, 2, 100, ["invalid!type"]
            )

        assert "No valid relationship types" in str(exc_info.value.message)


class TestGetQuerySearchSubgraph:
    """Tests for _get_query_search_subgraph helper function."""

    @pytest.mark.asyncio
    async def test_get_query_search_subgraph_success(self, mock_neo4j, sample_tenant_id):
        """Test successful query search subgraph fetch."""
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.return_value = [
            MagicMock(entity_id="entity-1"),
            MagicMock(entity_id="entity-2"),
        ]
        mock_neo4j.execute_query.return_value = [
            {
                "seed": {"id": "entity-1", "name": "Entity 1", "entity_type": "Entity"},
                "neighbors": [],
                "rels": [],
            }
        ]

        nodes, edges = await _get_query_search_subgraph(
            mock_neo4j, mock_hybrid_search, "test query", 100, None, sample_tenant_id
        )

        assert len(nodes) == 1
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_get_query_search_subgraph_no_results(self, mock_neo4j, sample_tenant_id):
        """Test empty result when search returns no matches."""
        mock_hybrid_search = AsyncMock()
        mock_hybrid_search.search.return_value = []

        nodes, edges = await _get_query_search_subgraph(
            mock_neo4j, mock_hybrid_search, "test query", 100, None, sample_tenant_id
        )

        assert nodes == []
        assert edges == []


class TestRecordMetrics:
    """Tests for metrics recording functions."""

    def test_record_full_graph_metrics_with_metrics(self):
        """Test metrics recording when metrics module is available."""
        with patch("src.api.routes.graph_viz.get_metrics") as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics

            _record_full_graph_metrics(100)

            mock_metrics.observe_graph_result_size.assert_called_once_with(
                size=100, endpoint="/graph", operation="get_full_graph"
            )

    def test_record_full_graph_metrics_without_metrics(self):
        """Test graceful handling when metrics module is not available."""
        with patch("src.api.routes.graph_viz.get_metrics", return_value=None):
            _record_full_graph_metrics(100)  # Should not raise

    def test_record_subgraph_metrics_with_metrics(self):
        """Test subgraph metrics recording when metrics module is available."""
        with patch("src.api.routes.graph_viz.get_metrics") as mock_get_metrics:
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics

            _record_subgraph_metrics(2, 50, "/test/endpoint", "test_operation")

            mock_metrics.observe_graph_traversal_depth.assert_called_once_with(
                depth=2, endpoint="/test/endpoint", operation="test_operation"
            )
            mock_metrics.observe_graph_result_size.assert_called_once_with(
                size=50, endpoint="/test/endpoint", operation="test_operation"
            )


class TestGetFullGraph:
    """Tests for get_full_graph endpoint."""

    @pytest.mark.asyncio
    async def test_get_full_graph_success(self, mock_app_state, sample_tenant_id):
        """Test successful full graph retrieval."""
        mock_app_state.neo4j_driver.execute_query.side_effect = [
            # Nodes — include x/y/r so _build_graph_node returns GraphNodeWithLayout
            [{"id": "node-1", "label": "Node 1", "type": "Entity", "confidence": 0.9, "x": 0.0, "y": 0.0, "r": 5.0}],
            [{"source": "node-1", "target": "node-1", "rel_type": "SELF", "weight": 1.0}],  # Edges
            [{"total": 1}],  # Total nodes
            [{"total": 1}],  # Total edges
        ]

        with patch("src.api.routes.graph_viz.get_metrics", return_value=None):
            response = await get_full_graph(sample_tenant_id, 1000, mock_app_state)

        assert isinstance(response, GraphResponse)
        assert len(response.nodes) == 1
        assert len(response.edges) == 1
        assert response.stats.total_nodes == 1

    @pytest.mark.asyncio
    async def test_get_full_graph_no_neo4j(self, mock_app_state, sample_tenant_id):
        """Test ServiceUnavailableError when Neo4j is not available."""
        mock_app_state.neo4j_driver = None

        with pytest.raises(ServiceUnavailableError):
            await get_full_graph(sample_tenant_id, 1000, mock_app_state)


class TestGetEntitySubgraph:
    """Tests for get_entity_subgraph endpoint."""

    @pytest.mark.asyncio
    async def test_get_entity_subgraph_success(self, mock_app_state, sample_tenant_id):
        """Test successful entity subgraph retrieval."""
        mock_app_state.neo4j_driver.execute_query.side_effect = [
            [{"id": "entity-1", "label": "Entity 1", "type": "Entity", "confidence": 0.9}],  # Root
            [
                {
                    "root": {"id": "entity-1"},
                    "connected": {"id": "entity-2", "type": "Entity"},
                    "rels": [],
                    "path_length": 1,
                }
            ],  # Subgraph
        ]

        with patch("src.api.routes.graph_viz.get_metrics", return_value=None):
            response = await get_entity_subgraph("entity-1", sample_tenant_id, 2, mock_app_state)

        assert isinstance(response, SubgraphResponse)
        assert response.root_entity_id == "entity-1"
        assert len(response.nodes) >= 1


class TestGetQuerySubgraph:
    """Tests for get_query_subgraph endpoint."""

    @pytest.mark.asyncio
    async def test_get_query_subgraph_center_mode_success(self, mock_app_state, sample_tenant_id):
        """Test successful query subgraph in center mode."""
        mock_app_state.neo4j_driver.execute_query.side_effect = [
            [{"id": "entity-1"}],  # Root check
            [
                {
                    "root": {"id": "entity-1", "name": "Entity 1", "entity_type": "Entity"},
                    "neighbors": [],
                    "paths": [],
                }
            ],  # Subgraph
        ]

        mock_hybrid_search = AsyncMock()

        with patch("src.api.routes.graph_viz.get_metrics", return_value=None):
            response = await get_query_subgraph(
                tenant_id=sample_tenant_id,
                query=None,
                center_entity_id="entity-1",
                depth=2,
                limit=100,
                entity_types=None,
                relationship_types=None,
                hybrid_search=mock_hybrid_search,
                graph_rag=AsyncMock(),
                app_state=mock_app_state,
            )

        assert isinstance(response, SubgraphResponse)
        assert response.root_entity_id == "entity-1"

    @pytest.mark.asyncio
    async def test_get_query_subgraph_requires_query_or_center(self, mock_app_state, sample_tenant_id):
        """Test ValidationError when neither query nor center_entity_id provided."""
        mock_app_state.neo4j_driver = AsyncMock()

        with pytest.raises(ValidationError) as exc_info:
            await get_query_subgraph(
                tenant_id=sample_tenant_id,
                query=None,
                center_entity_id=None,
                depth=2,
                limit=100,
                entity_types=None,
                relationship_types=None,
                hybrid_search=AsyncMock(),
                graph_rag=AsyncMock(),
                app_state=mock_app_state,
            )

        assert "Either 'query' or 'center_entity_id'" in str(exc_info.value.message)
