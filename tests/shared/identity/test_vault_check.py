"""Tests for vault_check module - regression tests for code review fixes."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from value_fabric.shared.identity.vault_check import (
    VaultConfigurationError,
    get_vault_health,
    get_vault_healthResult,
    resolve_vault_secret,
)


class TestGetVaultHealth:
    @pytest.mark.asyncio
    async def test_success_response_includes_all_required_fields(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "initialized": True,
            "sealed": False,
            "standby": False,
            "version": "1.15.0",
            "error": None,
        }

        with patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=False):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=AsyncMock(get=AsyncMock(return_value=mock_response))
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

                result = await get_vault_health()

        assert "reachable" in result
        assert result["reachable"] is True
        assert "status" in result
        assert result["status"] == "healthy"
        assert "initialized" in result
        assert "sealed" in result
        assert "standby" in result
        assert "version" in result

    @pytest.mark.asyncio
    async def test_error_response_has_reachable_false(self):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await get_vault_health()

        assert result["reachable"] is False
        assert result["status"] == "unreachable"
        assert "error" in result


class TestGetVaultHealthResultModel:
    def test_model_requires_reachable_field(self):
        data = {
            "status": "healthy",
            "reachable": True,
            "initialized": True,
            "sealed": False,
            "standby": False,
            "version": "1.15.0",
            "error": None,
        }
        result = get_vault_healthResult.model_validate(data)
        assert result["reachable"] is True

    def test_model_allows_optional_fields(self):
        data = {
            "status": "unreachable",
            "reachable": False,
            "error": "Connection failed",
        }
        result = get_vault_healthResult.model_validate(data)
        assert result["status"] == "unreachable"


class TestVaultTransportHardening:
    @pytest.mark.asyncio
    async def test_rejects_http_vault_addr_in_production(self):
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "production", "VAULT_ADDR": "http://vault.internal:8200", "VAULT_TOKEN": "token"},
            clear=False,
        ):
            with pytest.raises(VaultConfigurationError):
                await resolve_vault_secret("vault:secret/data/my-secret#api_key")

    @pytest.mark.asyncio
    async def test_allows_http_vault_addr_in_development(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"data": {"api_key": "x"}}}

        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "development", "VAULT_ADDR": "http://vault.internal:8200", "VAULT_TOKEN": "token"},
            clear=False,
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=AsyncMock(get=AsyncMock(return_value=mock_response))
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
                value = await resolve_vault_secret("vault:secret/data/my-secret#api_key")

        assert value == "x"
