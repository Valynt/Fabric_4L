"""Unit tests for L3 graph population verification."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from layer1_ingestion.shared.tasks import _verify_l3_graph_population


class TestVerifyL3GraphPopulation:
    """Test _verify_l3_graph_population helper."""

    @pytest.mark.asyncio
    async def test_returns_entity_count_on_success(self):
        """Should return total entity count when L3 responds 200."""
        tenant_id = "tenant-123"
        source_version_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 42}

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("layer1_ingestion.shared.tasks.settings") as mock_settings:
                mock_settings.layer3_api_url = "http://layer3:8000"
                with patch.dict("os.environ", {"SERVICE_AUTH_SECRET": "secret"}):
                    result = await _verify_l3_graph_population(tenant_id, source_version_id)

        assert result == 42
        mock_client.__aenter__.return_value.get.assert_called_once()
        call_args = mock_client.__aenter__.return_value.get.call_args
        assert call_args[1]["params"]["source_version_id"] == source_version_id
        assert call_args[1]["params"]["limit"] == 1
        assert call_args[1]["headers"]["X-Tenant-ID"] == tenant_id

    @pytest.mark.asyncio
    async def test_returns_zero_on_404(self):
        """Should return 0 when L3 responds 404."""
        tenant_id = "tenant-123"
        source_version_id = str(uuid4())

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("layer1_ingestion.shared.tasks.settings") as mock_settings:
                mock_settings.layer3_api_url = "http://layer3:8000"
                with patch.dict("os.environ", {"SERVICE_AUTH_SECRET": "secret"}):
                    result = await _verify_l3_graph_population(tenant_id, source_version_id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_on_exception(self):
        """Should return 0 and log warning when httpx raises."""
        tenant_id = "tenant-123"
        source_version_id = str(uuid4())

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get = AsyncMock(side_effect=Exception("connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("layer1_ingestion.shared.tasks.settings") as mock_settings:
                mock_settings.layer3_api_url = "http://layer3:8000"
                with patch.dict("os.environ", {"SERVICE_AUTH_SECRET": "secret"}):
                    with patch("layer1_ingestion.shared.tasks.logger") as mock_logger:
                        result = await _verify_l3_graph_population(tenant_id, source_version_id)

        assert result == 0
        mock_logger.warning.assert_called_once()
