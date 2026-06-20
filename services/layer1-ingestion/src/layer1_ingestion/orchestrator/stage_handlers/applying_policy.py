"""APPLYING_POLICY stage handler for the source ingestion pipeline."""

from __future__ import annotations

import base64
import re
from typing import Any

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.connector_resolution import (
    CustodyMode,
    normalize_custody_mode,
)
from layer1_ingestion.orchestrator.stage_handlers.base import StageHandler
from layer1_ingestion.orchestrator.stage_handlers.context import (
    StageContext,
    _flatten_artifact_ids,
)


class ApplyingPolicyHandler(StageHandler):
    """Apply custody, PII, retention, and redaction policies to the raw payload."""

    stage = IngestionStage.APPLYING_POLICY

    def __init__(self, scrub_pii: bool = True) -> None:
        self.scrub_pii = scrub_pii

    def _apply_scrub_rules(self, raw_text: str) -> str:
        """Standard regex-based redaction engine for PII."""
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        phone_pattern = r"\+?\b\d{1,3}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b"

        scrubbed = re.sub(email_pattern, "[REDACTED_EMAIL]", raw_text)
        scrubbed = re.sub(phone_pattern, "[REDACTED_PHONE]", scrubbed)
        return scrubbed

    def _load_raw_bytes(self, ctx: StageContext) -> bytes | None:
        """Load raw bytes from in-memory scratchpad or the prior step artifact."""
        scratch = ctx.get_scratchpad("fetched_raw_data")
        if scratch is not None:
            return scratch

        artifact = ctx.get_step_artifact("raw_source_bytes")
        if not isinstance(artifact, dict):
            return None
        encoded = artifact.get("bytes_b64")
        if encoded:
            return base64.b64decode(encoded)
        return None

    def handle(self, ctx: StageContext) -> str:
        # 1. Fetch parameters
        custody_mode = normalize_custody_mode(
            getattr(ctx.source, "custody_mode", CustodyMode.REFERENCE_EXTRACT.value)
        )

        # 2. Customer-hosted zero retention: no raw content is persisted or processed.
        if custody_mode == CustodyMode.CUSTOMER_HOSTED.value:
            ctx.persist_step_artifact(
                "policy_scrubbed_payload",
                {"length": 0, "custody_status": "customer_hosted_zero_retention"},
            )
            ctx.clear_scratchpad()
            return ctx.advance(IngestionStage.NORMALIZING_DOCUMENT)

        raw_data = self._load_raw_bytes(ctx)
        if raw_data is None:
            return ctx.fail_permanent(
                error_code="MISSING_RAW_SOURCE_BYTES",
                error_detail_safe="No raw source bytes were found in scratchpad or prior step artifact.",
            )

        # 3. Decode payload
        try:
            text_content = raw_data.decode("utf-8", errors="replace")
        except Exception as exc:
            return ctx.fail_permanent(
                error_code="CHARACTER_DECODING_FAILURE",
                error_detail_safe=f"Payload processing failed: {str(exc)}",
            )

        # 4. PII scrubbing policy application
        processed_text = text_content
        if self.scrub_pii:
            processed_text = self._apply_scrub_rules(text_content)

        # 5. Storage decisions based on custody level
        if custody_mode == CustodyMode.FABRIC_FULL_CUSTODY.value:
            ctx.persist_step_artifact(
                "policy_scrubbed_payload",
                {"length": len(processed_text), "custody_status": "stored_fully_redacted"},
            )
            ctx.save_permanent_document(processed_text)

        elif custody_mode == CustodyMode.REFERENCE_EXTRACT.value:
            ctx.persist_step_artifact(
                "policy_scrubbed_payload",
                {"length": len(processed_text), "custody_status": "transient_memory_only"},
            )
            ctx.set_scratchpad("transient_clean_text", processed_text)

        else:
            return ctx.fail_permanent(
                error_code="UNSUPPORTED_CUSTODY_MODE",
                error_detail_safe=f"The custody level {custody_mode} is not recognized by governance.",
            )

        # Trigger cleanup of raw fetched memory
        ctx.clear_scratchpad("fetched_raw_data")
        return ctx.advance(IngestionStage.NORMALIZING_DOCUMENT)

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
