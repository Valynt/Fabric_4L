from __future__ import annotations

"""Harness claim-validation adapter backed by the Layer 5 client."""

from layer4_agents.harness.live_l5_validator import LiveL5Validator
from layer4_agents.harness.validation_hooks import ClaimValidator
from layer4_agents.integration.layer5_client import Layer5GroundTruthClient


def create_live_l5_claim_validator(
    *,
    base_url: str,
    service_token: str | None,
    stale_threshold_hours: int = 24,
) -> ClaimValidator:
    """Create a Layer 5-backed harness claim validator.

    Tenant scoping remains per request via ``LiveL5Validator``. The underlying
    Layer 5 client is deliberately constructed in an adapter module so the
    harness factory does not import cross-layer integration clients directly.
    """
    client = Layer5GroundTruthClient(
        base_url=base_url,
        service_token=service_token,
    )
    return LiveL5Validator(
        client=client,
        stale_threshold_hours=stale_threshold_hours,
    )
