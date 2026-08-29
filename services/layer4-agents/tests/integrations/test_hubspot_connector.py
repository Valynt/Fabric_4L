from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from layer4_agents.integration.connectors.providers.hubspot.connector import HubSpotConnector


def _make_response(status_code: int, json_data: dict | None = None, text: str = "") -> httpx.Response:
    request = httpx.Request("GET", "https://api.hubapi.com")
    kwargs: dict[str, Any] = {"request": request}
    if json_data is not None:
        kwargs["json"] = json_data
    else:
        kwargs["text"] = text
    return httpx.Response(status_code, **kwargs)


class TestHubSpotConnectorTestConnection:
    @pytest.mark.asyncio
    async def test_test_connection_success(self) -> None:
        connector = HubSpotConnector(config={"crm_api_key": "token"})
        mock_response = _make_response(200, {"portalName": "TestPortal"})
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        result = await connector.test_connection()

        assert result["success"] is True
        assert "TestPortal" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_missing_credentials(self) -> None:
        connector = HubSpotConnector(config={})
        result = await connector.test_connection()
        assert result["success"] is False
        assert result["error_code"] == "MISSING_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_test_connection_401(self) -> None:
        connector = HubSpotConnector(config={"crm_api_key": "token"})
        mock_response = _make_response(401, {}, "Unauthorized")
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        result = await connector.test_connection()
        assert result["success"] is False
        assert result["error_code"] == "AUTH_FAILED"


class TestHubSpotConnectorGetAccount:
    @pytest.mark.asyncio
    async def test_get_account_maps_properties(self) -> None:
        connector = HubSpotConnector(config={"crm_api_key": "token"})
        mock_response = _make_response(
            200,
            {
                "id": "123",
                "properties": {
                    "name": "Acme",
                    "industry": "Technology",
                    "domain": "acme.com",
                },
            },
        )
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        record = await connector.get_account("123")

        assert record is not None
        assert record.model == "account"
        assert record.canonical["name"] == "Acme"
        assert record.canonical["domain"] == "acme.com"

    @pytest.mark.asyncio
    async def test_get_account_not_found(self) -> None:
        connector = HubSpotConnector(config={"crm_api_key": "token"})
        mock_response = _make_response(404, {})
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        record = await connector.get_account("123")
        assert record is None


class TestHubSpotConnectorTimeoutPropagation:
    @pytest.mark.asyncio
    async def test_timeout_reaches_httpx(self) -> None:
        """provider_timeout_s arrives as the timeout kwarg in the httpx call."""
        connector = HubSpotConnector(config={"crm_api_key": "token"})
        mock_response = _make_response(200, {"portalName": "TestPortal"})
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        await connector.test_connection(timeout=42.0)

        _, kwargs = mock_client.request.call_args
        assert kwargs.get("timeout") == 42.0
