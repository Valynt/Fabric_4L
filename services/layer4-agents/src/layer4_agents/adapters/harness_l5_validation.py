from __future__ import annotations

"""Harness claim-validation adapter backed by the Layer 5 client."""

from layer4_agents.harness.live_l5_validator import LiveL5Validator
from layer4_agents.harness.validation_hooks import ClaimValidator
from layer4_agents.integration.layer5_client import get_layer5_client


def create_live_l5_claim_validator(
    *,
    base_url: str,
    service_token: str | None,
    stale_threshold_hours: int = 24,
) -> ClaimValidator:
    """Create a Layer 5-backed harness claim validator.

    Tenant scoping remains per request via ``LiveL5Validator``. The underlying
    Layer 5 client is obtained through the canonical :func:`get_layer5_client`
    factory so there is a single construction path for the cross-layer client.
    """
    client = get_layer5_client(
        base_url=base_url,
        service_token=service_token,
    )
    return LiveL5Validator(
        client=client,
        stale_threshold_hours=stale_threshold_hours,
    )
