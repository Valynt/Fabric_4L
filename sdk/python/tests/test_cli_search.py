"""Tests for the ``vf search`` CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from valuefabric.cli.main import app
from valuefabric.generated.l3 import EntityType, SearchResponse, SearchResult, SearchType

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_config(tmp_path):
    """Provide a temporary CLI config so commands can load credentials."""
    config = {
        "active_profile": "default",
        "profiles": {
            "default": {
                "base_url": "https://api.example.com",
                "api_key": "test-key",
            }
        },
    }
    with patch("valuefabric.cli.config.CONFIG_FILE", tmp_path / "config.toml"):
        from valuefabric.cli.config import _save_config

        _save_config(config)
        yield


class TestSearchCommands:
    """Tests for vf search command."""

    def test_search_missing_query(self, mock_config):
        """Test that search without query shows error."""
        result = runner.invoke(app, ["search"])
        # Typer/Click returns exit code 2 for missing required arguments
        assert result.exit_code == 2
        assert "Usage:" in result.output or "Missing" in result.output or "required" in result.output.lower() or "Argument" in result.output

    def test_search_success(self, mock_config):
        """Test successful search returns results."""
        mock_response = SearchResponse(
            query="AI platform",
            total_results=2,
            search_type=SearchType.hybrid,
            processing_time_ms=150,
            results=[
                SearchResult(
                    entity_id="entity-1",
                    entity_type=EntityType.Capability,
                    name="Machine Learning Platform",
                    bm25_score=0.85,
                    vector_score=0.92,
                    graph_score=0.78,
                    combined_score=0.88,
                    confidence=0.95,
                ),
                SearchResult(
                    entity_id="entity-2",
                    entity_type=EntityType.UseCase,
                    name="Predictive Analytics",
                    bm25_score=0.72,
                    vector_score=0.88,
                    graph_score=0.81,
                    combined_score=0.82,
                    confidence=0.91,
                ),
            ],
        )

        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = mock_response

            result = runner.invoke(app, ["search", "AI platform"])

            assert result.exit_code == 0
            assert "Machine Learning Platform" in result.output
            assert "Predictive Analytics" in result.output
            assert "2 total" in result.output

    def test_search_json_output(self, mock_config):
        """Test search with --json flag returns valid JSON."""
        mock_response = SearchResponse(
            query="test",
            total_results=1,
            search_type=SearchType.hybrid,
            processing_time_ms=100,
            results=[
                SearchResult(
                    entity_id="entity-1",
                    entity_type=EntityType.Capability,
                    name="Test Capability",
                    bm25_score=0.9,
                    vector_score=0.85,
                    graph_score=0.8,
                    combined_score=0.87,
                    confidence=0.92,
                ),
            ],
        )

        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = mock_response

            result = runner.invoke(app, ["search", "test", "--json"])

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["query"] == "test"
            assert data["total_results"] == 1
            assert len(data["results"]) == 1

    def test_search_with_entity_type_filter(self, mock_config):
        """Test search with --type filter."""
        mock_response = SearchResponse(
            query="AI",
            total_results=1,
            search_type=SearchType.hybrid,
            processing_time_ms=120,
            results=[
                SearchResult(
                    entity_id="entity-1",
                    entity_type=EntityType.Capability,
                    name="AI Capability",
                    bm25_score=0.9,
                    vector_score=0.9,
                    graph_score=0.9,
                    combined_score=0.9,
                    confidence=0.95,
                ),
            ],
        )

        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = mock_response

            result = runner.invoke(app, ["search", "AI", "--type", "Capability"])

            assert result.exit_code == 0
            # Verify the client was called with entity_type filter
            call_args = mock_client.search.call_args[0][0]
            assert call_args.entity_type == EntityType.Capability

    def test_search_invalid_entity_type(self, mock_config):
        """Test search with invalid entity type shows error."""
        result = runner.invoke(app, ["search", "query", "--type", "InvalidType"])
        assert result.exit_code == 1
        assert "Invalid entity type" in result.output

    def test_search_no_results(self, mock_config):
        """Test search with no results shows appropriate message."""
        mock_response = SearchResponse(
            query="nonexistent",
            total_results=0,
            search_type=SearchType.hybrid,
            processing_time_ms=50,
            results=[],
        )

        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = mock_response

            result = runner.invoke(app, ["search", "nonexistent"])

            assert result.exit_code == 0
            assert "No results found" in result.output

    def test_search_api_error(self, mock_config):
        """Test search handles API errors gracefully."""
        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.side_effect = Exception("Connection refused")

            result = runner.invoke(app, ["search", "test"])

            assert result.exit_code == 1
            assert "Search failed" in result.output

    def test_search_with_limit(self, mock_config):
        """Test search with --limit option."""
        mock_response = SearchResponse(
            query="test",
            total_results=5,
            search_type=SearchType.hybrid,
            processing_time_ms=100,
            results=[],
        )

        with patch("valuefabric.cli.search.L3Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.search.return_value = mock_response

            result = runner.invoke(app, ["search", "test", "--limit", "5"])

            assert result.exit_code == 0
            call_args = mock_client.search.call_args[0][0]
            assert call_args.top_k == 5

    def test_search_help(self, mock_config):
        """Test search --help shows usage information."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "Hybrid entity search" in result.output or "search" in result.output
