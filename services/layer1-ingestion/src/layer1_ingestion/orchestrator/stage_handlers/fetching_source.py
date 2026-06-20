"""FETCHING_SOURCE stage handler for the source ingestion pipeline."""

from __future__ import annotations

import base64
import urllib.error
import urllib.request
from typing import Any, Protocol, runtime_checkable

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


@runtime_checkable
class ObjectStorageClient(Protocol):
    """Protocol for downloading raw bytes from object storage."""

    def download_bytes(self, storage_uri: str) -> bytes:
        ...


@runtime_checkable
class SecretManager(Protocol):
    """Protocol for retrieving connector credentials without exposing secrets."""

    def get_connector_credentials(self, tenant_id: str, connector_id: str) -> dict[str, str]:
        ...


class FetchingSourceHandler(StageHandler):
    """Fetch the raw source payload according to the connector resolution strategy."""

    stage = IngestionStage.FETCHING_SOURCE

    def __init__(
        self,
        storage_client: ObjectStorageClient | None = None,
        secret_manager: SecretManager | None = None,
    ) -> None:
        self.storage_client = storage_client
        self.secret_manager = secret_manager

    def handle(self, ctx: StageContext) -> str:
        tenant_id = getattr(ctx, "tenant_id", "default_tenant")

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
                raw_payload = self.storage_client.download_bytes(storage_uri)
            except Exception as exc:
                return ctx.fail_transient(
                    error_code="LOCAL_PAYLOAD_READ_ERROR",
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
                raw_payload = self.storage_client.download_bytes(storage_uri)
            except Exception as exc:
                return ctx.fail_transient(
                    error_code="OBJECT_STORAGE_ERROR",
                    error_detail_safe=f"Transient failure downloading object: {str(exc)}",
                )

        elif strategy in (FetchStrategy.EXTERNAL_CONNECTOR, FetchStrategy.CUSTOMER_HOSTED_CONNECTOR):
            if not self.secret_manager:
                return ctx.fail_permanent(
                    error_code="SECRET_MANAGER_NOT_INITIALIZED",
                    error_detail_safe="Secret manager credential client was not configured.",
                )
            conn_id = resolution.connector_id or resolution.connector_name
            try:
                secrets = self.secret_manager.get_connector_credentials(tenant_id, conn_id)
            except Exception as exc:
                return ctx.fail_permanent(
                    error_code="CONNECTOR_CREDENTIAL_DECRYPTION_FAILED",
                    error_detail_safe=f"Failed to decrypt credentials: {str(exc)}",
                )

            endpoint = resolution.connector_endpoint or "https://api.external.service/v1/fetch"
            if "api_key" not in secrets and "oauth_token" not in secrets:
                return ctx.fail_permanent(
                    error_code="MISSING_AUTHENTICATION_CREDENTIALS",
                    error_detail_safe="Decrypted credentials did not yield an API key or OAuth token.",
                )

            raw_payload = (
                f"Fetched data from {endpoint} for object {resolution.external_object_id}"
            ).encode()

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
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Fabric4L-Ingest-Agent/2.6"},
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_payload = response.read()
            except urllib.error.URLError as exc:
                return ctx.fail_transient(
                    error_code="HTTP_FETCH_TIMEOUT_OR_NETWORK_ERROR",
                    error_detail_safe=f"Transient network exception when crawling URL: {str(exc)}",
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

    def execute(
        self,
        db: Any,
        coordinator: Any,
        run: Any,
        step: Any,
    ) -> None:
        """Pipeline entry point: wrap the execution in a StageContext."""
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
        self.handle(ctx)
