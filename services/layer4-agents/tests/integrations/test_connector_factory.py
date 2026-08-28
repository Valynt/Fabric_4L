from __future__ import annotations

import pytest

from layer4_agents.integration.connectors.factory import get_connector, get_write_connector
from layer4_agents.integration.connectors.providers.hubspot.connector import HubSpotConnector
from layer4_agents.integration.connectors.providers.salesforce.connector import SalesforceConnector
from layer4_agents.models.account import CRMProvider


class TestConnectorFactory:
    """Unit tests for the CRM connector factory."""

    def test_get_connector_salesforce(self) -> None:
        connector = get_connector(
            CRMProvider.SALESFORCE,
            {"crm_api_key": "token", "crm_instance_url": "https://test.salesforce.com"},
        )
        assert isinstance(connector, SalesforceConnector)

    def test_get_connector_hubspot(self) -> None:
        connector = get_connector(
            CRMProvider.HUBSPOT,
            {"crm_api_key": "token"},
        )
        assert isinstance(connector, HubSpotConnector)

    def test_get_connector_unsupported_provider(self) -> None:
        # Manual provider has no connector yet.
        with pytest.raises(Exception):
            get_connector(CRMProvider.MANUAL, {})

    def test_get_write_connector_returns_same_instance(self) -> None:
        connector = get_write_connector(
            CRMProvider.SALESFORCE,
            {"crm_api_key": "token", "crm_instance_url": "https://test.salesforce.com"},
        )
        assert isinstance(connector, SalesforceConnector)
