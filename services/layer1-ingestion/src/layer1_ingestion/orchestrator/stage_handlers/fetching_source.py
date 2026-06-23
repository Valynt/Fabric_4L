"""FETCHING_SOURCE stage handler for the source ingestion pipeline."""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Protocol, runtime_checkable

import httpx

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.connector_resolution import (
    ConnectorResolution,
    CustodyMode,
    FetchStrategy,
    normalize_custody_mode,
)
from layer1_ingestion.orchestrator.stage_handlers.base import StageHandler
from layer1_ingestion.orchestrator.stage_handlers.context import (
    StageContext,
    _flatten_artifact_ids,
)

# Default timeout for outbound HTTP(S) fetches. Web pages and external metadata
# endpoints are expected to respond within this window.
_DEFAULT_FETCH_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


@runtime_checkable
class ObjectStorageClient(Protocol):
    """Protocol for downloading raw bytes from object storage."""

    async def download_bytes(self, storage_uri: str) -> bytes:
        ...


@runtime_checkable
class SecretManager(Protocol):
    """Protocol for retrieving connector credentials without exposing secrets."""

    async def get_connector_credentials(
        self, tenant_id: str, connector_id: str
    ) -> dict[str, str]:
        ...


def _classify_storage_error(exc: Exception) -> tuple[str, bool]:
    """Return (error_code, is_permanent) for a storage-layer exception."""
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        return ("STORAGE_RESOURCE_NOT_ACCESSIBLE", True)
    if isinstance(exc, ValueError):
        return ("STORAGE_INVALID_URI", True)
    return ("STORAGE_READ_ERROR", False)


def _classify_http_error(exc: httpx.HTTPStatusError) -> tuple[str, bool]:
    """Return (error_code, is_permanent) for an HTTP response error."""
    status = exc.response.status_code
    if status == 429:
        return ("HTTP_RATE_LIMITED", False)
    if status >= 500:
        return ("HTTP_SERVER_ERROR", False)
    return ("HTTP_CLIENT_ERROR", True)


def _build_web_headers(resolution: ConnectorResolution) -> dict[str, str]:
    """Merge resolution headers with the mandatory service User-Agent."""
    headers = {"User-Agent": "Fabric4L-Ingest-Agent/2.6"}
    if resolution.headers:
        # Resolution headers take precedence except for User-Agent, which we keep
        # as an observability signal.
        headers.update(resolution.headers)
        headers.setdefault("User-Agent", "Fabric4L-Ingest-Agent/2.6")
    return headers


class FetchingSourceHandler(StageHandler):
    """Fetch the raw source payload according to the connector resolution strategy."""

    stage = IngestionStage.FETCHING_SOURCE

    def __init__(
        self,
        storage_client: ObjectStorageClient | None = None,
        secret_manager: SecretManager | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.storage_client = storage_client
        self.secret_manager = secret_manager
        self.http_client = http_client

    async def handle(self, ctx: StageContext) -> str:
        # 1. Retrieve prior stage artifact
        resolution_dict = ctx.get_step_artifact("connector_resolution")
        if not resolution_dict:
            return ctx.fail_permanent(
                error_code="MISSING_RESOLUTION_ARTIFACT",
                error_detail_safe="The connector_resolution step artifact was not found.",
            )

        try:
            resolution = ConnectorResolution(**resolution_dict)
        except Exception as exc:
            return ctx.fail_permanent(
                error_code="INVALID_RESOLUTION_DATA",
                error_detail_safe=f"Failed to parse resolution artifact: {str(exc)}",
            )

        strategy = resolution.fetch_strategy
        raw_payload: bytes = b""
        metadata_attestation: dict[str, Any] | None = None

        custody_mode = normalize_custody_mode(
            getattr(ctx.source, "custody_mode", CustodyMode.REFERENCE_EXTRACT.value)
        )

        # 2. Branching fetch logic
        if strategy == FetchStrategy.LOCAL_PAYLOAD:
            storage_uri = getattr(ctx.source_version, "raw_storage_uri", None)
            if not storage_uri:
                return ctx.fail_permanent(
                    error_code="MISSING_LOCAL_STORAGE_URI",
                    error_detail_safe="Fetch strategy is LOCAL_PAYLOAD but source_version.raw_storage_uri is empty.",
                )
            if not self.storage_client:
                return ctx.fail_permanent(
                    error_code="STORAGE_CLIENT_NOT_INITIALIZED",
                    error_detail_safe="Object storage client was not configured for LOCAL_PAYLOAD.",
                )
            try:
                raw_payload = await self.storage_client.download_bytes(storage_uri)
            except Exception as exc:
                code, permanent = _classify_storage_error(exc)
                if permanent:
                    return ctx.fail_permanent(
                        error_code=code,
                        error_detail_safe=f"Permanent failure reading local payload: {str(exc)}",
                    )
                return ctx.fail_transient(
                    error_code=code,
                    error_detail_safe=f"Transient failure reading local payload: {str(exc)}",
                )

        elif strategy == FetchStrategy.OBJECT_STORAGE:
            if not self.storage_client:
                return ctx.fail_permanent(
                    error_code="STORAGE_CLIENT_NOT_INITIALIZED",
                    error_detail_safe="Object storage client was not configured.",
                )
            storage_uri = resolution.metadata.get("storage_ref")
            if not storage_uri:
                return ctx.fail_permanent(
                    error_code="MISSING_STORAGE_URI",
                    error_detail_safe="Storage reference path was not found in resolution metadata.",
                )
            try:
                raw_payload = await self.storage_client.download_bytes(storage_uri)
            except Exception as exc:
                code, permanent = _classify_storage_error(exc)
                if permanent:
                    return ctx.fail_permanent(
                        error_code=code,
                        error_detail_safe=f"Permanent failure downloading object: {str(exc)}",
                    )
                return ctx.fail_transient(
                    error_code=code,
                    error_detail_safe=f"Transient failure downloading object: {str(exc)}",
                )

        elif strategy == FetchStrategy.EXTERNAL_CONNECTOR:
            # External connector fetch is not yet production-ready. Fail closed
            # rather than fabricating a payload or silently returning placeholder
            # data.
            return ctx.fail_permanent(
                error_code="UNSUPPORTED_FETCH_STRATEGY",
                error_detail_safe=(
                    f"The fetch strategy {strategy.value} is not implemented for production use."
                ),
            )

        elif strategy == FetchStrategy.CUSTOMER_HOSTED_CONNECTOR:
            # Customer-hosted connectors fetch only metadata/attestation; the raw
            # payload is never persisted by Fabric.
            metadata_url = resolution.metadata.get("metadata_url")
            if not metadata_url:
                return ctx.fail_permanent(
                    error_code="UNSUPPORTED_FETCH_STRATEGY",
                    error_detail_safe=(
                        "CUSTOMER_HOSTED_CONNECTOR requires a metadata_url in the connector resolution."
                    ),
                )
            if not (
                metadata_url.startswith("https://") or metadata_url.startswith("http://")
            ):
                return ctx.fail_permanent(
                    error_code="INSECURE_OR_INVALID_PROTOCOL",
                    error_detail_safe="Customer-hosted metadata URL must use HTTP or HTTPS.",
                )

            try:
                metadata_attestation = await self._http_get(metadata_url, resolution)
            except httpx.TimeoutException as exc:
                return ctx.fail_transient(
                    error_code="HTTP_FETCH_TIMEOUT",
                    error_detail_safe=f"Timeout fetching customer-hosted metadata: {str(exc)}",
                )
            except httpx.NetworkError as exc:
                return ctx.fail_transient(
                    error_code="HTTP_FETCH_NETWORK_ERROR",
                    error_detail_safe=f"Network error fetching customer-hosted metadata: {str(exc)}",
                )
            except httpx.HTTPStatusError as exc:
                code, permanent = _classify_http_error(exc)
                if permanent:
                    return ctx.fail_permanent(
                        error_code=code,
                        error_detail_safe=f"Permanent failure fetching customer-hosted metadata: {str(exc)}",
                    )
                return ctx.fail_transient(
                    error_code=code,
                    error_detail_safe=f"Transient failure fetching customer-hosted metadata: {str(exc)}",
                )
            except Exception as exc:
                return ctx.fail_permanent(
                    error_code="CUSTOMER_HOSTED_METADATA_ERROR",
                    error_detail_safe=f"Permanent failure fetching customer-hosted metadata: {str(exc)}",
                )

            # Never store the raw payload; record an attestation artifact only.
            ctx.persist_step_artifact(
                "raw_source_bytes",
                {
                    "bytes_size": 0,
                    "custody_mode": CustodyMode.CUSTOMER_HOSTED.value,
                    "stored": False,
                    "metadata_attestation": metadata_attestation,
                },
            )
            ctx.set_scratchpad("fetched_raw_data", metadata_attestation)
            return ctx.advance(IngestionStage.APPLYING_POLICY)

        elif strategy == FetchStrategy.WEB_FETCH:
            url = resolution.metadata.get("url")
            if not url:
                return ctx.fail_permanent(
                    error_code="MISSING_URL",
                    error_detail_safe="Web fetch strategy selected but no URL was provided.",
                )
            if not (url.startswith("https://") or url.startswith("http://")):
                return ctx.fail_permanent(
                    error_code="INSECURE_OR_INVALID_PROTOCOL",
                    error_detail_safe="Web URL must use HTTP or HTTPS.",
                )

            try:
                raw_payload = await self._http_get_bytes(url, resolution)
            except httpx.TimeoutException as exc:
                return ctx.fail_transient(
                    error_code="HTTP_FETCH_TIMEOUT",
                    error_detail_safe=f"Timeout fetching target URL: {str(exc)}",
                )
            except httpx.NetworkError as exc:
                return ctx.fail_transient(
                    error_code="HTTP_FETCH_NETWORK_ERROR",
                    error_detail_safe=f"Network error fetching target URL: {str(exc)}",
                )
            except httpx.HTTPStatusError as exc:
                code, permanent = _classify_http_error(exc)
                if permanent:
                    return ctx.fail_permanent(
                        error_code=code,
                        error_detail_safe=f"Permanent failure fetching target URL: {str(exc)}",
                    )
                return ctx.fail_transient(
                    error_code=code,
                    error_detail_safe=f"Transient failure fetching target URL: {str(exc)}",
                )
            except Exception as exc:
                return ctx.fail_permanent(
                    error_code="WEB_FETCH_CRITICAL_FAILURE",
                    error_detail_safe=f"Permanent failure fetching target URL: {str(exc)}",
                )

        else:
            return ctx.fail_permanent(
                error_code="UNSUPPORTED_FETCH_STRATEGY",
                error_detail_safe=f"The fetch strategy {strategy.value} is not implemented.",
            )

        # 3. Persist raw payload according to custody rules
        if custody_mode == CustodyMode.CUSTOMER_HOSTED.value:
            ctx.persist_step_artifact(
                "raw_source_bytes",
                {
                    "bytes_size": len(raw_payload),
                    "custody_mode": CustodyMode.CUSTOMER_HOSTED.value,
                    "stored": False,
                },
            )
        else:
            ctx.persist_step_artifact(
                "raw_source_bytes",
                {
                    "bytes_b64": base64.b64encode(raw_payload).decode(),
                    "bytes_size": len(raw_payload),
                    "custody_mode": custody_mode,
                    "stored": True,
                },
            )

        ctx.set_scratchpad("fetched_raw_data", raw_payload)
        return ctx.advance(IngestionStage.APPLYING_POLICY)

    async def _http_get_bytes(
        self, url: str, resolution: ConnectorResolution
    ) -> bytes:
        """Perform an async HTTP GET and return raw response bytes."""
        client = self.http_client or httpx.AsyncClient(timeout=_DEFAULT_FETCH_TIMEOUT)
        try:
            response = await client.get(url, headers=_build_web_headers(resolution))
            response.raise_for_status()
            return response.content
        finally:
            if self.http_client is None:
                await client.aclose()

    async def _http_get(
        self, url: str, resolution: ConnectorResolution
    ) -> dict[str, Any]:
        """Perform an async HTTP GET and return a JSON metadata object."""
        client = self.http_client or httpx.AsyncClient(timeout=_DEFAULT_FETCH_TIMEOUT)
        try:
            response = await client.get(url, headers=_build_web_headers(resolution))
            response.raise_for_status()
            return response.json()
        finally:
            if self.http_client is None:
                await client.aclose()

    def execute(
        self,
        db: Any,
        coordinator: Any,
        run: Any,
        step: Any,
    ) -> None:
        """Pipeline entry point: run the async handler in a dedicated event loop."""
        coordinator.mark_step_running(step)
        ctx = StageContext(
            tenant_id=run.tenant_id,
            account_id=getattr(run.source, "account_id", None),
            source=run.source,
            source_version=run.version,
            step=step,
            run=run,
            coordinator=coordinator,
            db=db,
            artifacts=_flatten_artifact_ids(step.input_artifact_ids or {}),
        )
        asyncio.run(self.handle(ctx))
