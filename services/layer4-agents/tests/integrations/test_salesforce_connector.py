from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from layer4_agents.integration.connectors.core.errors import AuthError, TransientError
from layer4_agents.integration.connectors.providers.salesforce.connector import SalesforceConnector


def _make_response(
    status_code: int, json_data: dict | None = None, text: str = ""
) -> httpx.Response:
    request = httpx.Request("GET", "https://test.salesforce.com")
    kwargs: dict[str, Any] = {"request": request}
    if json_data is not None:
        kwargs["json"] = json_data
    else:
        kwargs["text"] = text
    return httpx.Response(status_code, **kwargs)


class TestSalesforceConnectorTestConnection:
    @pytest.mark.asyncio
    async def test_test_connection_success(self) -> None:
        connector = SalesforceConnector(
            config={
                "crm_api_key": "token",
                "crm_instance_url": "https://test.salesforce.com",
            }
        )
        mock_response = _make_response(200, {"records": [{"Name": "TestOrg"}]})
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        result = await connector.test_connection()

        assert result["success"] is True
        assert "TestOrg" in result["message"]

    @pytest.mark.asyncio
    async def test_test_connection_missing_credentials(self) -> None:
        connector = SalesforceConnector(config={})
        result = await connector.test_connection()
        assert result["success"] is False
        assert result["error_code"] == "MISSING_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_test_connection_401(self) -> None:
        connector = SalesforceConnector(
            config={
                "crm_api_key": "token",
                "crm_instance_url": "https://test.salesforce.com",
            }
        )
        mock_response = _make_response(401, {}, "Unauthorized")
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        result = await connector.test_connection()
        assert result["success"] is False
        assert result["error_code"] == "AUTH_FAILED"

    @pytest.mark.asyncio
    async def test_transport_error_does_not_expose_provider_details(self) -> None:
        connector = SalesforceConnector(
            config={
                "crm_api_key": "token",
                "crm_instance_url": "https://test.salesforce.com",
            }
        )
        connector._request = AsyncMock(
            side_effect=TransientError("connection failed with secret-token")
        )

        result = await connector.test_connection()

        assert result == {
            "success": False,
            "message": "Salesforce connection failed",
            "error_code": "TRANSIENTERROR",
        }


class TestSalesforceConnectorRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_token_success(self) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(
                200,
                {
                    "access_token": "new-token",
                    "instance_url": "https://new.salesforce.com",
                    "refresh_token": "new-refresh",
                },
            )
            result = await SalesforceConnector.refresh_token(
                refresh_token="old-refresh",
                instance_url="https://test.salesforce.com",
                client_id="client-id",
                client_secret="client-secret",
            )
        assert result["api_key"] == "new-token"
        assert result["instance_url"] == "https://new.salesforce.com"
        assert result["refresh_token"] == "new-refresh"

    @pytest.mark.asyncio
    async def test_refresh_token_401_raises_auth_error(self) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _make_response(401, {}, "Unauthorized")
            with pytest.raises(AuthError):
                await SalesforceConnector.refresh_token(
                    refresh_token="old-refresh",
                    instance_url="https://test.salesforce.com",
                    client_id="client-id",
                    client_secret="client-secret",
                )


class TestSalesforceConnectorValidation:
    def test_validate_sfdc_id_rejects_injection(self) -> None:
        from layer4_agents.integration.connectors.providers.salesforce.connector import _validate_sfdc_id

        with pytest.raises(ValueError):
            _validate_sfdc_id("001' OR Name != '")

    def test_validate_sfdc_id_accepts_valid(self) -> None:
        from layer4_agents.integration.connectors.providers.salesforce.connector import _validate_sfdc_id

        assert _validate_sfdc_id("001XXXXXXXXXXXXXXX") == "001XXXXXXXXXXXXXXX"


class TestSalesforceConnectorTimeoutPropagation:
    @pytest.mark.asyncio
    async def test_timeout_reaches_httpx(self) -> None:
        """provider_timeout_s arrives as the timeout kwarg in the httpx call."""
        connector = SalesforceConnector(
            config={
                "crm_api_key": "token",
                "crm_instance_url": "https://test.salesforce.com",
            }
        )
        mock_response = _make_response(200, {"records": [{"Name": "TestOrg"}]})
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        connector._client = mock_client

        await connector.test_connection(timeout=42.0)

        _, kwargs = mock_client.request.call_args
        assert kwargs.get("timeout") == 42.0


class TestSalesforceConnectorTokenRefreshPersistence:
    @pytest.mark.asyncio
    async def test_401_refresh_invokes_persistence_callback_with_rotated_tokens(self) -> None:
        refreshed_payloads: list[dict[str, str]] = []

        async def persist_refreshed_tokens(payload: dict[str, str]) -> None:
            refreshed_payloads.append(payload)

        connector = SalesforceConnector(
            config={
                "crm_api_key": "old-token",
                "crm_instance_url": "https://test.salesforce.com",
                "refresh_token": "old-refresh",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "on_token_refresh": persist_refreshed_tokens,
            }
        )
        first_response = _make_response(401, {}, "Unauthorized")
        retry_response = _make_response(200, {"records": []})
        stale_client = AsyncMock()
        stale_client.request = AsyncMock(return_value=first_response)
        refreshed_client = AsyncMock()
        refreshed_client.request = AsyncMock(return_value=retry_response)
        connector._client = stale_client

        with (
            patch.object(
                SalesforceConnector,
                "refresh_token",
                new=AsyncMock(
                    return_value={
                        "api_key": "new-token",
                        "instance_url": "https://new.salesforce.com",
                        "refresh_token": "new-refresh",
                    }
                ),
            ),
            patch.object(connector, "_get_client", side_effect=[stale_client, refreshed_client]),
        ):
            response = await connector._request("GET", "/services/data/v58.0/query/")

        assert response.status_code == 200
        assert refreshed_payloads == [
            {
                "api_key": "new-token",
                "instance_url": "https://new.salesforce.com",
                "refresh_token": "new-refresh",
            }
        ]


class TestSalesforceConnectorOpportunityTruncation:
    @pytest.mark.asyncio
    async def test_list_opportunities_raises_when_soql_query_is_truncated(self) -> None:
        connector = SalesforceConnector(
            config={
                "crm_api_key": "token",
                "crm_instance_url": "https://test.salesforce.com",
            }
        )

        with patch.object(
            connector,
            "_execute_soql_query",
            new=AsyncMock(return_value=([{"Id": "006XXXXXXXXXXXX", "Name": "Partial"}], True)),
        ):
            with pytest.raises(TransientError, match="truncated"):
                await connector.list_opportunities("001XXXXXXXXXXXX")
