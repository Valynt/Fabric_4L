"""Unit tests for the FETCHING_SOURCE and APPLYING_POLICY stage handlers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorKind,
    ConnectorResolution,
    FetchStrategy,
)
from layer1_ingestion.orchestrator.stage_handlers.applying_policy import (
    ApplyingPolicyHandler,
)
from layer1_ingestion.orchestrator.stage_handlers.fetching_source import (
    FetchingSourceHandler,
)


class MockStageContext:
    """Lightweight in-memory context for testing handler logic."""

    def __init__(self, source: Any, source_version: Any, step_artifacts: dict[str, Any]) -> None:
        self.source = source
        self.source_version = source_version
        self.artifacts = step_artifacts
        self.scratchpad: dict[str, Any] = {}
        self.failed_permanent = False
        self.failed_transient = False
        self.advanced_to: IngestionStage | None = None
        self.error_code: str | None = None
        self.error_detail_safe: str | None = None
        self.permanent_store: str | None = None

    def get_step_artifact(self, name: str) -> Any | None:
        return self.artifacts.get(name)

    def persist_step_artifact(self, name: str, payload: Any) -> None:
        self.artifacts[name] = payload

    def set_scratchpad(self, key: str, value: Any) -> None:
        self.scratchpad[key] = value

    def get_scratchpad(self, key: str) -> Any | None:
        return self.scratchpad.get(key)

    def clear_scratchpad(self, key: str | None = None) -> None:
        if key:
            self.scratchpad.pop(key, None)
        else:
            self.scratchpad.clear()

    def fail_permanent(self, error_code: str, error_detail_safe: str) -> Any:
        self.failed_permanent = True
        self.error_code = error_code
        self.error_detail_safe = error_detail_safe
        return "FAILED_PERMANENT"

    def fail_transient(self, error_code: str, error_detail_safe: str) -> Any:
        self.failed_transient = True
        self.error_code = error_code
        self.error_detail_safe = error_detail_safe
        return "FAILED_TRANSIENT"

    def advance(self, stage: IngestionStage) -> Any:
        self.advanced_to = stage
        return "ADVANCED"

    def save_permanent_document(self, text: str) -> None:
        self.permanent_store = text


class MockStorageClient:
    def download_bytes(self, storage_uri: str) -> bytes:
        if storage_uri == "s3://prod-bucket/file.txt":
            return b"Verified File Download Content."
        if storage_uri == "local://source-version-payload":
            return b"Local File Content."
        raise Exception("Access Denied")


class MockSecretManager:
    def get_connector_credentials(self, tenant_id: str, connector_id: str) -> dict[str, str]:
        if connector_id == "salesforce":
            return {"api_key": "DECRYPTED_TEST_TOKEN"}
        raise Exception("Decryption failure")


def _connector_resolution(
    *,
    fetch_strategy: FetchStrategy,
    metadata: dict[str, Any],
    requires_fetch: bool = True,
    connector_kind: ConnectorKind = ConnectorKind.LOCAL,
    connector_name: str = "local",
    custody_mode: str = "reference_extract",
) -> ConnectorResolution:
    return ConnectorResolution(
        connector_kind=connector_kind,
        connector_name=connector_name,
        custody_mode=custody_mode,
        fetch_strategy=fetch_strategy,
        requires_fetch=requires_fetch,
        requires_snapshot_verification=False,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# FETCHING_SOURCE
# ---------------------------------------------------------------------------


def test_fetching_source_local_payload_success() -> None:
    source = SimpleNamespace(custody_mode="reference_extract")
    source_version = SimpleNamespace(raw_storage_uri="local://source-version-payload")
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
        requires_fetch=False,
        metadata={"source_version_id": "sv-1", "source_type": "note"},
    )

    ctx = MockStageContext(source, source_version, {"connector_resolution": resolution.to_artifact()})
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = handler.handle(ctx)
    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert ctx.scratchpad["fetched_raw_data"] == b"Local File Content."
    assert ctx.artifacts["raw_source_bytes"]["stored"] is True


def test_fetching_source_object_storage_success() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={"storage_ref": "s3://prod-bucket/file.txt", "source_version_id": "sv-2", "source_type": "pdf"},
    )

    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()})
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = handler.handle(ctx)
    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert ctx.scratchpad["fetched_raw_data"] == b"Verified File Download Content."


def test_fetching_source_transient_failure_on_storage_error() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={"storage_ref": "s3://invalid-bucket/file.txt", "source_version_id": "sv-2", "source_type": "pdf"},
    )

    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()})
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = handler.handle(ctx)
    assert result == "FAILED_TRANSIENT"
    assert ctx.error_code == "OBJECT_STORAGE_ERROR"


def test_fetching_source_external_connector_success() -> None:
    resolution = ConnectorResolution(
        connector_kind=ConnectorKind.CRM,
        connector_name="salesforce",
        custody_mode="reference_extract",
        fetch_strategy=FetchStrategy.EXTERNAL_CONNECTOR,
        requires_fetch=True,
        requires_snapshot_verification=False,
        external_system="salesforce",
        external_object_id="opp-123",
        connector_endpoint="https://salesforce.example/api/v1",
        metadata={"source_version_id": "sv-3", "source_type": "crm_record"},
    )

    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()})
    handler = FetchingSourceHandler(secret_manager=MockSecretManager())

    result = handler.handle(ctx)
    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert b"Fetched data from https://salesforce.example/api/v1" in ctx.scratchpad["fetched_raw_data"]


def test_fetching_source_missing_resolution_fails_permanent() -> None:
    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(), {})
    handler = FetchingSourceHandler()

    result = handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "MISSING_RESOLUTION_ARTIFACT"


def test_fetching_source_local_payload_empty_fails_permanent() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
        requires_fetch=False,
        metadata={"source_version_id": "sv-1", "source_type": "note"},
    )
    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(raw_storage_uri=None), {"connector_resolution": resolution.to_artifact()})
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "MISSING_LOCAL_STORAGE_URI"


# ---------------------------------------------------------------------------
# APPLYING_POLICY
# ---------------------------------------------------------------------------


def test_applying_policy_reference_extract_scrub() -> None:
    source = SimpleNamespace(custody_mode="reference_extract")
    ctx = MockStageContext(source, SimpleNamespace(), {})
    ctx.set_scratchpad(
        "fetched_raw_data",
        b"Contact John Doe at john.doe@anonymous.com or +1-555-0199.",
    )

    handler = ApplyingPolicyHandler(scrub_pii=True)
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.NORMALIZING_DOCUMENT
    assert ctx.get_scratchpad("transient_clean_text") == "Contact John Doe at [REDACTED_EMAIL] or [REDACTED_PHONE]."
    assert ctx.permanent_store is None
    assert ctx.get_scratchpad("fetched_raw_data") is None


def test_applying_policy_fabric_full_custody_stores_permanent() -> None:
    source = SimpleNamespace(custody_mode="fabric_full_custody")
    ctx = MockStageContext(source, SimpleNamespace(), {})
    ctx.set_scratchpad("fetched_raw_data", b"Sensitive full-custody payload.")

    handler = ApplyingPolicyHandler(scrub_pii=True)
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.NORMALIZING_DOCUMENT
    assert ctx.permanent_store == "Sensitive full-custody payload."
    assert ctx.artifacts["policy_scrubbed_payload"]["custody_status"] == "stored_fully_redacted"


def test_applying_policy_customer_hosted_zero_retention() -> None:
    source = SimpleNamespace(custody_mode="customer_hosted")
    ctx = MockStageContext(source, SimpleNamespace(), {})
    ctx.set_scratchpad("fetched_raw_data", b"Customer hosted payload.")
    ctx.set_scratchpad("other_key", "should also be cleared")

    handler = ApplyingPolicyHandler(scrub_pii=True)
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.NORMALIZING_DOCUMENT
    assert ctx.scratchpad == {}
    assert ctx.permanent_store is None
    assert ctx.artifacts["policy_scrubbed_payload"]["custody_status"] == "customer_hosted_zero_retention"


def test_applying_policy_missing_raw_data_fails_permanent() -> None:
    source = SimpleNamespace(custody_mode="reference_extract")
    ctx = MockStageContext(source, SimpleNamespace(), {})

    handler = ApplyingPolicyHandler()
    result = handler.handle(ctx)

    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "MISSING_RAW_SOURCE_BYTES"


def test_applying_policy_repo_custody_codes_mapped() -> None:
    """Ensure the repository's single-letter custody codes map to spec names."""
    source = SimpleNamespace(custody_mode="B")  # reference_extract
    ctx = MockStageContext(source, SimpleNamespace(), {})
    ctx.set_scratchpad("fetched_raw_data", b"Payload with email redact@example.com")

    handler = ApplyingPolicyHandler()
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.get_scratchpad("transient_clean_text") == "Payload with email [REDACTED_EMAIL]"


def test_applying_policy_reads_raw_bytes_from_prior_artifact() -> None:
    """Resilience: policy can run in a fresh worker that only has the step artifact."""
    import base64

    source = SimpleNamespace(custody_mode="reference_extract")
    ctx = MockStageContext(source, SimpleNamespace(), {})
    ctx.artifacts["raw_source_bytes"] = {
        "bytes_b64": base64.b64encode(b"Payload with email redact@example.com").decode(),
        "bytes_size": 37,
        "custody_mode": "reference_extract",
        "stored": True,
    }

    handler = ApplyingPolicyHandler()
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.get_scratchpad("transient_clean_text") == "Payload with email [REDACTED_EMAIL]"
