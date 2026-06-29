"""Unit tests for the FETCHING_SOURCE and APPLYING_POLICY stage handlers."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any

import httpx
import respx

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorKind,
    ConnectorResolution,
    CustodyMode,
    FetchStrategy,
)
from layer1_ingestion.orchestrator.stage_handlers.applying_policy import ApplyingPolicyHandler
from layer1_ingestion.orchestrator.stage_handlers.fetching_source import FetchingSourceHandler
from layer1_ingestion.orchestrator.stage_handlers.resolving_connector import (
    ResolvingConnectorHandler,
)


class MockStageContext:
    """Lightweight in-memory context for testing handler logic."""

    def __init__(
        self,
        source: Any,
        source_version: Any,
        step_artifacts: dict[str, Any],
        run: Any | None = None,
    ) -> None:
        self.source = source
        self.source_version = source_version
        self.artifacts = step_artifacts
        self.run = (
            run
            if run is not None
            else SimpleNamespace(
                connector_name=None,
                connector_config_hash=None,
                policy_version=None,
                source_snapshot_hash=None,
            )
        )
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
    async def download_bytes(self, storage_uri: str) -> bytes:
        if storage_uri == "s3://prod-bucket/file.txt":
            return b"Verified File Download Content."
        if storage_uri == "local://source-version-payload":
            return b"Local File Content."
        if storage_uri == "local://not-found":
            raise FileNotFoundError("object not found")
        if storage_uri == "local://forbidden":
            raise PermissionError("access denied")
        if storage_uri == "local://invalid-uri":
            raise ValueError("invalid storage URI")
        raise Exception("Access Denied")


class MockSecretManager:
    async def get_connector_credentials(self, tenant_id: str, connector_id: str) -> dict[str, str]:
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
    headers: dict[str, str] | None = None,
) -> ConnectorResolution:
    return ConnectorResolution(
        connector_kind=connector_kind,
        connector_name=connector_name,
        custody_mode=custody_mode,
        fetch_strategy=fetch_strategy,
        requires_fetch=requires_fetch,
        requires_snapshot_verification=False,
        headers=headers,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# FETCHING_SOURCE
# ---------------------------------------------------------------------------


async def test_fetching_source_local_payload_success() -> None:
    source = SimpleNamespace(custody_mode="reference_extract")
    source_version = SimpleNamespace(raw_storage_uri="local://source-version-payload")
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
        requires_fetch=False,
        metadata={"source_version_id": "sv-1", "source_type": "note"},
    )

    ctx = MockStageContext(
        source, source_version, {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert ctx.scratchpad["fetched_raw_data"] == b"Local File Content."
    assert ctx.artifacts["raw_source_bytes"]["stored"] is True


async def test_fetching_source_object_storage_success() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={
            "storage_ref": "s3://prod-bucket/file.txt",
            "source_version_id": "sv-2",
            "source_type": "pdf",
        },
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert ctx.scratchpad["fetched_raw_data"] == b"Verified File Download Content."


async def test_fetching_source_transient_failure_on_generic_storage_error() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={
            "storage_ref": "s3://invalid-bucket/file.txt",
            "source_version_id": "sv-2",
            "source_type": "pdf",
        },
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "FAILED_TRANSIENT"
    assert ctx.error_code == "STORAGE_READ_ERROR"


async def test_fetching_source_permanent_failure_on_file_not_found() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={
            "storage_ref": "local://not-found",
            "source_version_id": "sv-2",
            "source_type": "pdf",
        },
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "STORAGE_RESOURCE_NOT_ACCESSIBLE"


async def test_fetching_source_permanent_failure_on_permission_error() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={
            "storage_ref": "local://forbidden",
            "source_version_id": "sv-2",
            "source_type": "pdf",
        },
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "STORAGE_RESOURCE_NOT_ACCESSIBLE"


async def test_fetching_source_permanent_failure_on_invalid_storage_uri() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.OBJECT_STORAGE,
        connector_kind=ConnectorKind.FILE,
        connector_name="file",
        metadata={
            "storage_ref": "local://invalid-uri",
            "source_version_id": "sv-2",
            "source_type": "pdf",
        },
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "STORAGE_INVALID_URI"


async def test_fetching_source_external_connector_fails_permanent() -> None:
    """External connector fetch must not fabricate placeholder data."""
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

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler(secret_manager=MockSecretManager())

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "UNSUPPORTED_FETCH_STRATEGY"


async def test_fetching_source_customer_hosted_metadata_only_success() -> None:
    """Customer-hosted connectors fetch only metadata; raw payload is never stored."""
    resolution = ConnectorResolution(
        connector_kind=ConnectorKind.CRM,
        connector_name="customer-hosted-crm",
        custody_mode=CustodyMode.CUSTOMER_HOSTED,
        fetch_strategy=FetchStrategy.CUSTOMER_HOSTED_CONNECTOR,
        requires_fetch=True,
        requires_snapshot_verification=False,
        external_system="salesforce",
        external_object_id="opp-123",
        metadata={"metadata_url": "https://customer.example/metadata"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        route = respx.get("https://customer.example/metadata").mock(
            return_value=httpx.Response(200, json={"attestation": "hash-abc", "record_count": 42})
        )
        result = await handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert route.called
    assert ctx.scratchpad["fetched_raw_data"] == {"attestation": "hash-abc", "record_count": 42}
    assert ctx.artifacts["raw_source_bytes"]["stored"] is False
    assert ctx.artifacts["raw_source_bytes"]["custody_mode"] == CustodyMode.CUSTOMER_HOSTED.value
    assert "metadata_attestation" in ctx.artifacts["raw_source_bytes"]
    await client.aclose()


async def test_fetching_source_customer_hosted_missing_metadata_url_fails_permanent() -> None:
    resolution = ConnectorResolution(
        connector_kind=ConnectorKind.CRM,
        connector_name="customer-hosted-crm",
        custody_mode=CustodyMode.CUSTOMER_HOSTED,
        fetch_strategy=FetchStrategy.CUSTOMER_HOSTED_CONNECTOR,
        requires_fetch=True,
        requires_snapshot_verification=False,
        metadata={},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler()

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "UNSUPPORTED_FETCH_STRATEGY"


async def test_fetching_source_customer_hosted_never_stores_raw_payload() -> None:
    """Even a metadata URL returning a large response only stores the attestation summary."""
    resolution = ConnectorResolution(
        connector_kind=ConnectorKind.CRM,
        connector_name="customer-hosted-crm",
        custody_mode=CustodyMode.CUSTOMER_HOSTED,
        fetch_strategy=FetchStrategy.CUSTOMER_HOSTED_CONNECTOR,
        requires_fetch=True,
        requires_snapshot_verification=False,
        metadata={"metadata_url": "https://customer.example/metadata"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        respx.get("https://customer.example/metadata").mock(
            return_value=httpx.Response(200, json={"raw": "should-not-be-persisted"})
        )
        await handler.handle(ctx)

    assert ctx.artifacts["raw_source_bytes"]["stored"] is False
    assert "bytes_b64" not in ctx.artifacts["raw_source_bytes"]
    await client.aclose()


async def test_fetching_source_missing_resolution_fails_permanent() -> None:
    ctx = MockStageContext(SimpleNamespace(), SimpleNamespace(), {})
    handler = FetchingSourceHandler()

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "MISSING_RESOLUTION_ARTIFACT"


async def test_fetching_source_local_payload_empty_fails_permanent() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.LOCAL_PAYLOAD,
        requires_fetch=False,
        metadata={"source_version_id": "sv-1", "source_type": "note"},
    )
    ctx = MockStageContext(
        SimpleNamespace(),
        SimpleNamespace(raw_storage_uri=None),
        {"connector_resolution": resolution.to_artifact()},
    )
    handler = FetchingSourceHandler(storage_client=MockStorageClient())

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "MISSING_LOCAL_STORAGE_URI"


async def test_fetching_source_web_fetch_success() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        route = respx.get("https://example.com/page").mock(
            return_value=httpx.Response(200, text="<html>hello</html>")
        )
        result = await handler.handle(ctx)

    assert result == "ADVANCED"
    assert ctx.advanced_to == IngestionStage.APPLYING_POLICY
    assert route.called
    assert ctx.scratchpad["fetched_raw_data"] == b"<html>hello</html>"
    await client.aclose()


async def test_fetching_source_web_fetch_uses_resolution_headers() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
        headers={"X-Custom-Header": "custom-value"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        route = respx.get("https://example.com/page").mock(
            return_value=httpx.Response(200, text="ok")
        )
        await handler.handle(ctx)

    assert route.called
    request = route.calls.last.request
    assert request.headers["X-Custom-Header"] == "custom-value"
    assert "Fabric4L-Ingest-Agent" in request.headers["User-Agent"]
    await client.aclose()


async def test_fetching_source_web_fetch_timeout_is_retryable() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        respx.get("https://example.com/page").mock(side_effect=httpx.TimeoutException("timeout"))
        result = await handler.handle(ctx)

    assert result == "FAILED_TRANSIENT"
    assert ctx.error_code == "HTTP_FETCH_TIMEOUT"
    await client.aclose()


async def test_fetching_source_web_fetch_503_is_retryable() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        respx.get("https://example.com/page").mock(return_value=httpx.Response(503))
        result = await handler.handle(ctx)

    assert result == "FAILED_TRANSIENT"
    assert ctx.error_code == "HTTP_SERVER_ERROR"
    await client.aclose()


async def test_fetching_source_web_fetch_429_is_retryable() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        respx.get("https://example.com/page").mock(return_value=httpx.Response(429))
        result = await handler.handle(ctx)

    assert result == "FAILED_TRANSIENT"
    assert ctx.error_code == "HTTP_RATE_LIMITED"
    await client.aclose()


async def test_fetching_source_web_fetch_404_is_permanent() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "https://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    client = httpx.AsyncClient()
    handler = FetchingSourceHandler(http_client=client)

    with respx.mock:
        respx.get("https://example.com/page").mock(return_value=httpx.Response(404))
        result = await handler.handle(ctx)

    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "HTTP_CLIENT_ERROR"
    await client.aclose()


async def test_fetching_source_web_fetch_invalid_protocol_is_permanent() -> None:
    resolution = _connector_resolution(
        fetch_strategy=FetchStrategy.WEB_FETCH,
        metadata={"url": "ftp://example.com/page"},
    )

    ctx = MockStageContext(
        SimpleNamespace(), SimpleNamespace(), {"connector_resolution": resolution.to_artifact()}
    )
    handler = FetchingSourceHandler()

    result = await handler.handle(ctx)
    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "INSECURE_OR_INVALID_PROTOCOL"


# ---------------------------------------------------------------------------
# RESOLVING_CONNECTOR
# ---------------------------------------------------------------------------


def test_resolving_connector_builds_strategy_for_supported_source() -> None:
    source = SimpleNamespace(
        source_type="audio",
        custody_mode="B",
        meta={"storage_ref": "s3://audio/record.txt"},
    )
    source_version = SimpleNamespace()
    handler = ResolvingConnectorHandler()
    ctx = MockStageContext(source=source, source_version=source_version, step_artifacts={})

    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert handler is not None
    assert ctx.advanced_to == IngestionStage.FETCHING_SOURCE
    assert (
        ctx.artifacts["connector_resolution"]["fetch_strategy"]
        == FetchStrategy.OBJECT_STORAGE.value
    )


def test_resolving_connector_persists_run_connector_metadata() -> None:
    source = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000101",
        source_type="audio",
        custody_mode="B",
        meta={"storage_ref": "s3://audio/record.txt"},
        field_scope_id="scope-1",
    )
    source_version = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000202",
        content_hash="abc123",
        raw_storage_uri="s3://audio/record.txt",
        meta={"storage_ref": "s3://audio/record.txt"},
    )
    run = SimpleNamespace(
        connector_name=None,
        connector_config_hash=None,
        policy_version=None,
        source_snapshot_hash=None,
    )
    handler = ResolvingConnectorHandler()

    ctx = MockStageContext(
        source=source,
        source_version=source_version,
        step_artifacts={},
        run=run,
    )
    result = handler.handle(ctx)

    assert result == "ADVANCED"
    assert run.connector_name == "s3_reference"
    assert run.policy_version == "v3.0"
    assert isinstance(run.connector_config_hash, str)
    assert len(run.connector_config_hash) == 64
    assert isinstance(run.source_snapshot_hash, str)
    assert len(run.source_snapshot_hash) == 64


def test_resolving_connector_url_without_source_url_fails() -> None:
    source = SimpleNamespace(
        source_type="url",
        custody_mode="A",
        meta={},
    )
    source_version = SimpleNamespace(raw_storage_uri="raw://url")
    handler = ResolvingConnectorHandler()

    ctx = MockStageContext(source=source, source_version=source_version, step_artifacts={})
    result = handler.handle(ctx)

    assert result == "FAILED_PERMANENT"
    assert ctx.error_code == "UNSUPPORTED_CONNECTOR_CONFIG"


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
    assert (
        ctx.get_scratchpad("transient_clean_text")
        == "Contact John Doe at [REDACTED_EMAIL] or [REDACTED_PHONE]."
    )
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
    assert (
        ctx.artifacts["policy_scrubbed_payload"]["custody_status"]
        == "customer_hosted_zero_retention"
    )


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
