"""Tests for the connector resolution contract and helpers."""

from __future__ import annotations

from enum import Enum as PyEnum
from types import SimpleNamespace

import pytest

from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorKind,
    ConnectorResolution,
    CustodyMode,
    FetchStrategy,
    normalize_custody_mode,
    resolve_connector_for_source,
)
from layer1_ingestion.shared.models import SourceType


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


@pytest.mark.parametrize(
    "source_type, expected_strategy, expected_kind, metadata",
    [
        (
            SourceType.NOTES,
            FetchStrategy.LOCAL_PAYLOAD,
            ConnectorKind.LOCAL,
            {},
        ),
        (
            SourceType.PDF,
            FetchStrategy.LOCAL_PAYLOAD,
            ConnectorKind.LOCAL,
            {},
        ),
        (
            SourceType.URL,
            FetchStrategy.WEB_FETCH,
            ConnectorKind.WEB,
            {"url": "https://example.com/page"},
        ),
        (
            SourceType.AUDIO,
            FetchStrategy.OBJECT_STORAGE,
            ConnectorKind.FILE,
            {"storage_ref": "s3://layer1/audio/record.json"},
        ),
        (
            SourceType.MEETING,
            FetchStrategy.OBJECT_STORAGE,
            ConnectorKind.FILE,
            {"storage_ref": "s3://layer1/meeting/transcript.txt"},
        ),
        (
            SourceType.CRM,
            FetchStrategy.OBJECT_STORAGE,
            ConnectorKind.CRM,
            {
                "storage_ref": "s3://layer1/crm/object.json",
                "external_system": "salesforce",
                "external_object_type": "opportunity",
                "external_object_id": "opp-123",
            },
        ),
    ],
)
def test_resolve_connector_for_all_source_types(
    source_type: SourceType,
    expected_strategy: FetchStrategy,
    expected_kind: ConnectorKind,
    metadata: dict[str, str],
) -> None:
    source = SimpleNamespace(source_type=source_type, custody_mode="A", meta={})
    source_version = SimpleNamespace(raw_storage_uri="raw://source-version", meta=metadata)

    resolution = resolve_connector_for_source(source, source_version)

    assert resolution.connector_kind == expected_kind
    assert resolution.fetch_strategy == expected_strategy
    assert resolution.connector_name in {"postgres", "s3_reference", "crm_connector"}


def test_resolve_connector_for_url_requires_source_url() -> None:
    source = SimpleNamespace(source_type=SourceType.URL, custody_mode="A", meta={})
    source_version = SimpleNamespace(raw_storage_uri="raw://source-version", meta={})

    with pytest.raises(Exception):
        resolve_connector_for_source(source, source_version)


def test_resolve_connector_for_url_uses_source_external_reference() -> None:
    source = SimpleNamespace(
        source_type=SourceType.URL,
        custody_mode="A",
        external_reference="https://example.com/page",
        meta={},
    )
    source_version = SimpleNamespace(raw_storage_uri="raw://source-version", meta={})

    resolution = resolve_connector_for_source(source, source_version)

    assert resolution.connector_kind == ConnectorKind.WEB
    assert resolution.fetch_strategy == FetchStrategy.WEB_FETCH
    assert resolution.metadata["url"] == "https://example.com/page"


def test_resolve_connector_for_audio_fails_without_storage_ref() -> None:
    source = SimpleNamespace(source_type=SourceType.AUDIO, custody_mode="B", meta={})
    source_version = SimpleNamespace(raw_storage_uri=None, meta={})

    with pytest.raises(Exception):
        resolve_connector_for_source(source, source_version)


def test_resolve_connector_for_audio_fails_with_only_raw_storage_uri() -> None:
    """AUDIO sources must not fall back to raw_storage_uri — sensitive recordings."""
    source = SimpleNamespace(source_type=SourceType.AUDIO, custody_mode="B", meta={})
    source_version = SimpleNamespace(raw_storage_uri="raw://s3/audio/recording.mp3", meta={})

    with pytest.raises(Exception):
        resolve_connector_for_source(source, source_version)


def test_resolve_connector_for_meeting_fails_without_storage_ref() -> None:
    source = SimpleNamespace(source_type=SourceType.MEETING, custody_mode="B", meta={})
    source_version = SimpleNamespace(raw_storage_uri=None, meta={})

    with pytest.raises(Exception):
        resolve_connector_for_source(source, source_version)


def test_resolve_connector_for_meeting_fails_with_only_raw_storage_uri() -> None:
    """MEETING sources must not fall back to raw_storage_uri — sensitive recordings."""
    source = SimpleNamespace(source_type=SourceType.MEETING, custody_mode="B", meta={})
    source_version = SimpleNamespace(raw_storage_uri="raw://s3/meetings/recording.mp4", meta={})

    with pytest.raises(Exception):
        resolve_connector_for_source(source, source_version)


def test_resolve_connector_for_crm_uses_source_external_reference() -> None:
    source = SimpleNamespace(
        source_type=SourceType.CRM,
        custody_mode="A",
        external_reference="https://tenant.example/api/crm/attestation",
        meta={},
    )
    source_version = SimpleNamespace(
        raw_storage_uri="raw://source-version",
        meta={"storage_ref": None},
    )

    resolution = resolve_connector_for_source(source, source_version)

    assert resolution.connector_kind == ConnectorKind.CRM
    assert resolution.fetch_strategy == FetchStrategy.CUSTOMER_HOSTED_CONNECTOR
    assert resolution.metadata["metadata_url"] == "https://tenant.example/api/crm/attestation"


def test_resolve_connector_for_crm_customer_hosted_metadata_uses_metadata_connector() -> None:
    source = SimpleNamespace(source_type=SourceType.CRM, custody_mode="C", meta={})
    source_version = SimpleNamespace(
        raw_storage_uri="raw://source-version",
        meta={"metadata_url": "https://tenant.example/attestation"},
    )

    resolution = resolve_connector_for_source(source, source_version)

    assert resolution.fetch_strategy == FetchStrategy.CUSTOMER_HOSTED_CONNECTOR
    assert resolution.connector_name == "customer_hosted"
    assert resolution.metadata["metadata_url"] == "https://tenant.example/attestation"
