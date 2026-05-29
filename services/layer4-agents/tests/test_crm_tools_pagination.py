from __future__ import annotations

"""
Tests for CRM tools pagination and rate limit handling.

Covers:
- SOQL query pagination via nextRecordsUrl
- Rate limit detection and graceful handling
- Max page safety limit
"""


import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from layer4_agents.models.tool_schemas import GetProspectDataInput
from layer4_agents.tools.crm_tools import GetProspectDataTool


class MockResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, status_code: int, json_data: dict, headers: dict | None = None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
        return self._json


@pytest.mark.asyncio
async def test_salesforce_opportunity_pagination():
    """Test that opportunities are fetched across multiple pages."""
    tool = GetProspectDataTool(
        config={
            "crm_type": "salesforce",
            "crm_api_key": "test-token",
            "crm_instance_url": "https://test.salesforce.com",
        }
    )

    page1_data = {
        "records": [
            {"Id": "0061", "Name": "Opp 1", "StageName": "Prospecting", "Amount": 1000, "Probability": 50, "CloseDate": "2026-06-01"},
            {"Id": "0062", "Name": "Opp 2", "StageName": "Negotiation", "Amount": 2000, "Probability": 75, "CloseDate": "2026-07-01"},
        ],
        "nextRecordsUrl": "/services/data/v58.0/query/01g5000000abcdef",
    }

    page2_data = {
        "records": [
            {"Id": "0063", "Name": "Opp 3", "StageName": "Closed Won", "Amount": 3000, "Probability": 100, "CloseDate": "2026-08-01"},
        ],
        "nextRecordsUrl": None,
    }

    call_count = 0
    async def mock_get(url: str, **kwargs):
        nonlocal call_count
        call_count += 1
        if "query?q=" in url:
            return MockResponse(200, page1_data)
        elif "query/01g5000000abcdef" in url:
            return MockResponse(200, page2_data)
        return MockResponse(404, {})

    with patch.object(tool, "_get_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client_factory.return_value = mock_client

        result = await tool._get_salesforce_data(
            mock_client,
            GetProspectDataInput(prospect_id="001TEST123456789", data_types=["opportunities"]),
        )

    assert len(result.opportunities) == 3
    assert result.opportunities[0]["name"] == "Opp 1"
    assert result.opportunities[2]["name"] == "Opp 3"
    assert call_count == 2  # Initial query + 1 next page


@pytest.mark.asyncio
async def test_salesforce_rate_limit_graceful():
    """Test that rate limit (429) is handled gracefully without crashing."""
    tool = GetProspectDataTool(
        config={
            "crm_type": "salesforce",
            "crm_api_key": "test-token",
            "crm_instance_url": "https://test.salesforce.com",
        }
    )

    async def mock_get(url: str, **kwargs):
        if "sobjects/Account" in url:
            return MockResponse(200, {"Name": "Test Co"})
        elif "query?q=" in url:
            return MockResponse(429, {}, headers={"Sforce-Limit-Info": "api-usage=50000/50000"})
        return MockResponse(404, {})

    with patch.object(tool, "_get_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client_factory.return_value = mock_client

        result = await tool._get_salesforce_data(
            mock_client,
            GetProspectDataInput(prospect_id="001TEST123456789", data_types=["profile", "opportunities"]),
        )

    # Profile should still be fetched
    assert result.profile is not None
    assert result.profile.get("name") == "Test Co"
    # Opportunities should be empty due to 429, not crash
    assert result.opportunities == []


@pytest.mark.asyncio
async def test_salesforce_max_pages_safety():
    """Test that pagination stops at max_pages to prevent unbounded fetching."""
    tool = GetProspectDataTool(
        config={
            "crm_type": "salesforce",
            "crm_api_key": "test-token",
            "crm_instance_url": "https://test.salesforce.com",
        }
    )

    # Create a chain longer than max_pages (10)
    call_count = 0
    async def mock_get(url: str, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockResponse(
            200,
            {
                "records": [{"Id": f"006{call_count}", "Name": f"Opp {call_count}", "StageName": "Open", "Amount": 100, "Probability": 10, "CloseDate": "2026-06-01"}],
                "nextRecordsUrl": "/services/data/v58.0/query/next",
            },
        )

    with patch.object(tool, "_get_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client_factory.return_value = mock_client

        result = await tool._get_salesforce_data(
            mock_client,
            GetProspectDataInput(prospect_id="001TEST123456789", data_types=["opportunities"]),
        )

    # Should stop at max_pages (10) even though more pages exist
    assert len(result.opportunities) == 10
    assert call_count == 10
