"""Custody policy service for canonical source ingestion (v3.0).

Determines the custody mode and storage policy for a source based on its type,
connector, and account-level configuration. v3.0 defines three custody modes:

A: Fabric full custody — raw content stored in Fabric.
B: Reference + extract — metadata and extracted values stored; raw fetched on demand.
C: Customer hosted — no raw content persisted; only hashes, pointers, and attestations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import CustodyMode, SourceType


@dataclass(frozen=True)
class CustodyDecision:
    """Result of applying the custody policy to a source."""

    mode: CustodyMode
    store_raw: bool
    store_extracted: bool
    store_reference_only: bool
    allowed_backends: tuple[str, ...]
    retention_class: str
    policy_version: str


# Default custody policy per source type.
# Mode A: store raw + extracted.
# Mode B: store extracted + reference metadata, do not persist raw.
# Mode C: store hashes/pointers only, no raw or extracted values.
DEFAULT_CUSTODY_POLICY: dict[SourceType, CustodyDecision] = {
    SourceType.NOTES: CustodyDecision(
        mode=CustodyMode.FULL_CUSTODY,
        store_raw=True,
        store_extracted=True,
        store_reference_only=False,
        allowed_backends=("postgres", "s3"),
        retention_class="standard",
        policy_version="v3.0",
    ),
    SourceType.URL: CustodyDecision(
        mode=CustodyMode.FULL_CUSTODY,
        store_raw=True,
        store_extracted=True,
        store_reference_only=False,
        allowed_backends=("postgres", "s3"),
        retention_class="standard",
        policy_version="v3.0",
    ),
    SourceType.AUDIO: CustodyDecision(
        mode=CustodyMode.REFERENCE_EXTRACT,
        store_raw=False,
        store_extracted=True,
        store_reference_only=True,
        allowed_backends=("s3_reference", "external_custodian"),
        retention_class="sensitive",
        policy_version="v3.0",
    ),
    SourceType.CRM: CustodyDecision(
        mode=CustodyMode.REFERENCE_EXTRACT,
        store_raw=False,
        store_extracted=True,
        store_reference_only=True,
        allowed_backends=("crm_connector", "external_custodian"),
        retention_class="sensitive",
        policy_version="v3.0",
    ),
    SourceType.PDF: CustodyDecision(
        mode=CustodyMode.FULL_CUSTODY,
        store_raw=True,
        store_extracted=True,
        store_reference_only=False,
        allowed_backends=("postgres", "s3"),
        retention_class="standard",
        policy_version="v3.0",
    ),
    SourceType.MEETING: CustodyDecision(
        mode=CustodyMode.REFERENCE_EXTRACT,
        store_raw=False,
        store_extracted=True,
        store_reference_only=True,
        allowed_backends=("s3_reference", "external_custodian"),
        retention_class="sensitive",
        policy_version="v3.0",
    ),
}


class CustodyPolicyService:
    """Resolve custody policy for a source ingestion request."""

    def __init__(self, account_config: dict[str, Any] | None = None) -> None:
        self._account_config = account_config or {}

    def decide(
        self,
        source_type: SourceType,
        *,
        connector_name: str | None = None,
        customer_hosted: bool = False,
    ) -> CustodyDecision:
        """Return the custody decision for a source.

        Account-level overrides take precedence, then customer-hosted flag,
        then default policy by source type.
        """
        if customer_hosted or self._account_config.get("force_customer_hosted"):
            return CustodyDecision(
                mode=CustodyMode.CUSTOMER_HOSTED,
                store_raw=False,
                store_extracted=False,
                store_reference_only=True,
                allowed_backends=("customer_hosted",),
                retention_class="customer_hosted",
                policy_version="v3.0",
            )

        source_type_value = getattr(source_type, "value", str(source_type))
        account_overrides = self._account_config.get("custody_overrides", {})
        override = account_overrides.get(source_type_value)
        if override:
            return CustodyDecision(
                mode=CustodyMode(override["mode"]),
                store_raw=override.get("store_raw", False),
                store_extracted=override.get("store_extracted", False),
                store_reference_only=override.get("store_reference_only", True),
                allowed_backends=tuple(override.get("allowed_backends", [])),
                retention_class=override.get("retention_class", "standard"),
                policy_version=override.get("policy_version", "v3.0"),
            )

        default = DEFAULT_CUSTODY_POLICY.get(source_type) if isinstance(source_type, SourceType) else None
        if default is None:
            # Try to look up by value if source_type is an enum instance.
            if not isinstance(source_type, SourceType):
                default = next(
                    (v for k, v in DEFAULT_CUSTODY_POLICY.items() if k.value == source_type_value),
                    None,
                )
        if default is None:
            # Fallback to customer-hosted for unknown source types.
            return CustodyDecision(
                mode=CustodyMode.CUSTOMER_HOSTED,
                store_raw=False,
                store_extracted=False,
                store_reference_only=True,
                allowed_backends=("customer_hosted",),
                retention_class="unknown",
                policy_version="v3.0",
            )

        return default

    def validate_connector_against_policy(
        self,
        decision: CustodyDecision,
        connector_name: str,
    ) -> None:
        """Raise if the connector is not allowed for the custody decision."""
        if connector_name not in decision.allowed_backends:
            raise ValueError(
                f"Connector '{connector_name}' is not allowed for custody mode {decision.mode.value}"
            )
