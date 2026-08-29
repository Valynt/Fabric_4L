from __future__ import annotations

from typing import Any

from ...models.account import CRMProvider
from .core.connector import CRMConnector, CRMWriteConnector
from .core.errors import PermanentError


def get_connector(provider: CRMProvider, config: dict[str, Any]) -> CRMConnector:
    """Return a CRMConnector for the given provider and configuration.

    Args:
        provider: The CRM provider enum value.
        config: Decrypted/provider configuration such as api_key, instance_url,
            crm_type, etc.

    Raises:
        PermanentError: If the provider is not supported.
    """
    from .providers.hubspot.connector import HubSpotConnector
    from .providers.salesforce.connector import SalesforceConnector

    if provider == CRMProvider.SALESFORCE:
        return SalesforceConnector(config=config)
    if provider == CRMProvider.HUBSPOT:
        return HubSpotConnector(config=config)
    raise PermanentError(f"Unsupported CRM provider: {provider.value}")


def get_write_connector(provider: CRMProvider, config: dict[str, Any]) -> CRMWriteConnector:
    """Return a CRMWriteConnector for the given provider and configuration.

    Currently read and write connectors are implemented by the same class for
    Salesforce and HubSpot, but the factory keeps the door open for splitting
    them later.
    """
    connector = get_connector(provider, config)
    if not isinstance(connector, CRMWriteConnector):
        raise PermanentError(
            f"Provider {provider.value} does not support write operations"
        )
    return connector
