"""Tests for the connector resolution contract and helpers."""

from __future__ import annotations

from enum import Enum as PyEnum

import pytest

from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorResolution,
    CustodyMode,
    FetchStrategy,
    normalize_custody_mode,
)


class _DbCustodyMode(str, PyEnum):
    """Mimics the SQLAlchemy DB enum that uses single-letter custody codes."""

    FULL_CUSTODY = "A"
    REFERENCE_EXTRACT = "B"
    CUSTOMER_HOSTED = "C"


@pytest.mark.parametrize(
    "value, expected",
    [
        (CustodyMode.FABRIC_FULL_CUSTODY, "fabric_full_custody"),
        (CustodyMode.REFERENCE_EXTRACT, "reference_extract"),
        (CustodyMode.CUSTOMER_HOSTED, "customer_hosted"),
        ("A", "fabric_full_custody"),
        ("B", "reference_extract"),
        ("C", "customer_hosted"),
        ("fabric_full_custody", "fabric_full_custody"),
        ("reference_extract", "reference_extract"),
        ("customer_hosted", "customer_hosted"),
        (_DbCustodyMode.FULL_CUSTODY, "fabric_full_custody"),
        (_DbCustodyMode.REFERENCE_EXTRACT, "reference_extract"),
        (_DbCustodyMode.CUSTOMER_HOSTED, "customer_hosted"),
    ],
)
def test_normalize_custody_mode(value, expected: str) -> None:
    assert normalize_custody_mode(value) == expected


def test_normalize_custody_mode_returns_unknown_unchanged() -> None:
    assert normalize_custody_mode("unknown_mode") == "unknown_mode"
    assert normalize_custody_mode(None) is None


def test_connector_resolution_headers_round_trip() -> None:
    resolution = ConnectorResolution(
        connector_kind="local",
        connector_name="local",
        custody_mode="reference_extract",
        fetch_strategy=FetchStrategy.WEB_FETCH,
        requires_fetch=True,
        headers={"X-Custom": "value"},
    )
    artifact = resolution.to_artifact()
    restored = ConnectorResolution.from_artifact(artifact)
    assert restored.headers == {"X-Custom": "value"}
