from __future__ import annotations

"""Signal Detection Agent for operational pain signal discovery.

Orchestrates the complete signal detection pipeline:
1. Receives prospect setup data
2. Calls Layer 2 for structured extraction
3. Queries Layer 3 for evidence and quantification
4. Persists enriched signals
5. Emits streaming events to frontend
"""
import asyncio
import json
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..harness.prompt_registry import get_prompt_registry
from ..interfaces.signal_clients import SignalExtractionPort, SignalKnowledgePort
from ..messaging.signal_events import (
    ErrorCategory,
    SignalCompletedEvent,
    SignalDiscoveredEvent,
    SignalFailedEvent,
    SignalStreamCompleteEvent,
)
from ..models.pain_signal import EvidenceMatch, PainSignal, SignalCategory, TrendDirection
from ..services.governed_llm_client import GovernedLLMClient
from ..services.llm_output_parser import parse_llm_json
from ..services.llm_provider import get_llm_provider
from .base import AgentCapability, AgentResult, BaseAgent


class SignalDetectionAgent__detect_signalsResult(TypedDictModel):
    message: str
    processing_metadata: Any
    signals: list[Any]
    llm_output: Any | None = None

class SignalDetectionAgent__extract_signals_from_layer2Result(TypedDictModel):
    duration_ms: int
    error: Any
    signals: list[Any]

logger = logging.getLogger(__name__)


class SignalDetectionAgent(BaseAgent):
    """Agent for detecting operational pain signals from prospect data.

    This agent orchestrates a multi-layer pipeline:
    - Layer 2: LLM-based structured extraction of operational signals
    - Layer 3: Evidence matching and impact quantification
    - Layer 4: Event streaming and persistence coordination

    Capabilities:
    - detect_operational_signals: Extract and enrich operational signals
    - stream_signal_detection: Real-time streaming version with progress events
    """

    agent_type = "SignalDetectionAgent"

    # Supported signal categories (operational only for Phase 3 vertical slice)
    SUPPORTED_CATEGORIES: set[str] = {"Operational"}

    def __init__(
        self,
        *,
        layer2_client: SignalExtractionPort | None = None,
        layer3_client: SignalKnowledgePort | None = None,
        layer2_client_factory: Callable[[Mapping[str, Any]], SignalExtractionPort] | None = None,
        layer3_client_factory: Callable[[Mapping[str, Any]], SignalKnowledgePort] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.layer2_client = layer2_client
        self.layer3_client = layer3_client
        self._layer2_client_factory = layer2_client_factory
        self._layer3_client_factory = layer3_client_factory
        self.stream_callback = None
        self.max_signals = self.config.get("max_signals_per_request", 3)
        self.evidence_match_limit = self.config.get("evidence_match_limit", 5)

    async def _initialize_resources(self) -> None:
        """Initialize Layer 2 and Layer 3 API clients."""
        # Cross-layer clients are initialized lazily through injectable factories.

    def _get_layer2_client(self) -> SignalExtractionPort:
        """Get or create Layer 2 extraction client."""
        if self.layer2_client is None:
            if self._layer2_client_factory is None:
                raise RuntimeError("SignalDetectionAgent requires a Layer 2 signal extraction client factory")
            self.layer2_client = self._layer2_client_factory(self.config)
        return self.layer2_client

    def _get_layer3_client(self) -> SignalKnowledgePort:
        """Get or create Layer 3 knowledge client."""
        if self.layer3_client is None:
            if self._layer3_client_factory is None:
                raise RuntimeError("SignalDetectionAgent requires a Layer 3 signal knowledge client factory")
            self.layer3_client = self._layer3_client_factory(self.config)
        return self.layer3_client

    def get_capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="detect_operational_signals",
                description="Detect operational pain signals from prospect setup data",
                input_schema={
                    "prospect_data": {
                        "account_id": "string",
                        "company_name": "string",
                        "industry": "string",
                        "business_pains": ["string"],
                        "friction_points": ["string"],
                        "desired_outcomes": ["string"],
                        "prompt_text": "string",
                        "attachments": ["object"],
                    },
                    "options": {
                        "include_evidence": "boolean",
                        "quantify_impact": "boolean",
                        "stream_results": "boolean",
                    },
                },
                output_schema={
                    "signals": ["PainSignal"],
                    "processing_metadata": {
                        "extraction_duration_ms": "number",
                        "signals_found": "number",
                        "signals_with_evidence": "number",
                    },
                },
                timeout_seconds=120,
            ),
            AgentCapability(
                name="stream_signal_detection",
                description="Stream signal detection progress in real-time",
                input_schema={
                    "prospect_data": "object",
                    "stream_callback": "callable",
                },
                output_schema={
                    "stream_id": "string",
                    "signals_count": "number",
                },
                timeout_seconds=180,
            ),
        ]

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute signal detection task.

        Args:
            task: Task with 'capability' and 'parameters'
            context: Execution context with tenant_id, user_id, trace_id

        Returns:
            Task execution result
        """
        capability = task.get("capability", "detect_operational_signals")
        parameters = task.get("parameters", {})
        ctx = RequestContext(**context)

        if capability == "detect_operational_signals":
            return await self._detect_signals(parameters, ctx)
        elif capability == "stream_signal_detection":
            self.stream_callback = parameters.get("stream_callback")
            return await self._stream_detection(parameters, ctx)
        else:
            raise ValueError(f"Unknown capability: {capability}")

    async def _detect_signals(
        self,
        parameters: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Core signal detection pipeline.

        Pipeline stages:
        1. Layer 2: Extract operational signals via LLM
        2. Layer 3: Match evidence, quantify impact
        3. Layer 3: Persist enriched signals
        """
        start_time = datetime.now(UTC)
        prospect_data = parameters.get("prospect_data", {})
        options = parameters.get("options", {})
        include_evidence = options.get("include_evidence", True)
        quantify_impact = options.get("quantify_impact", True)

        signals: list[PainSignal] = []
        processing_metadata = {
            "extraction_duration_ms": 0,
            "enrichment_duration_ms": 0,
            "persistence_duration_ms": 0,
            "signals_found": 0,
            "signals_with_evidence": 0,
            "signals_quantified": 0,
            "trace_id": ctx.trace_id or "",
        }

        try:
            # Stage 1: Layer 2 Extraction
            logger.info(
                "Starting signal extraction",
                extra={
                    "tenant_id": ctx.tenant_id,
                    "account_id": prospect_data.get("account_id"),
                    "trace_id": ctx.trace_id,
                },
            )

            extraction_result = await self._extract_signals_from_layer2(
                prospect_data, ctx
            )
            processing_metadata["extraction_duration_ms"] = extraction_result.get(
                "duration_ms", 0
            )

            raw_signals = extraction_result.get("signals", [])
            processing_metadata["signals_found"] = len(raw_signals)

            if not raw_signals:
                return SignalDetectionAgent__detect_signalsResult.model_validate({
                    "signals": [],
                    "processing_metadata": processing_metadata,
                    "message": "No operational signals detected",
                })


            # Stage 2: Layer 3 Enrichment
            enrichment_start = datetime.now(UTC)
            for idx, raw_signal in enumerate(raw_signals):
                signal = self._create_pain_signal(raw_signal, prospect_data, ctx)
                if signal is None:
                    continue

                if include_evidence:
                    signal = await self._enrich_with_evidence(signal, ctx)

                if quantify_impact and signal.confidence_score >= 0.7:
                    signal = await self._quantify_impact(signal, prospect_data, ctx)

                signals.append(signal)

                # Emit discovery event if streaming
                if self.stream_callback:
                    event = SignalDiscoveredEvent(
                        prospect_id=prospect_data.get("account_id", ""),
                        signal=signal,
                        partial=idx < len(raw_signals) - 1 or include_evidence,
                        stage="enriching",
                        progress_percent=int((idx + 1) / len(raw_signals) * 50),
                    )
                    await self._emit_event(event)

            processing_metadata["enrichment_duration_ms"] = int(
                (datetime.now(UTC) - enrichment_start).total_seconds() * 1000
            )

            # Stage 3: Layer 3 Persistence
            persistence_start = datetime.now(UTC)
            persisted_count = 0
            for signal in signals:
                try:
                    await self._persist_signal(signal, ctx)
                    persisted_count += 1

                    # Emit completion event if streaming
                    if self.stream_callback:
                        event = SignalCompletedEvent(
                            prospect_id=prospect_data.get("account_id", ""),
                            signal_id=signal.id,
                            final_signal=signal,
                            processing_duration_ms=int(
                                (datetime.now(UTC) - start_time).total_seconds() * 1000
                            ),
                        )
                        await self._emit_event(event)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(
                        f"Failed to persist signal {signal.id}: {e}",
                        extra={
                            "tenant_id": ctx.tenant_id,
                            "signal_id": signal.id,
                            "trace_id": ctx.trace_id,
                        },
                    )

            processing_metadata["persistence_duration_ms"] = int(
                (datetime.now(UTC) - persistence_start).total_seconds() * 1000
            )
            processing_metadata["signals_with_evidence"] = len(
                [s for s in signals if s.evidence_matches]
            )
            processing_metadata["signals_quantified"] = len(
                [s for s in signals if s.impact_value is not None]
            )

            # Emit stream complete if streaming
            if self.stream_callback:
                stream_duration_ms = int(
                    (datetime.now(UTC) - start_time).total_seconds() * 1000
                )
                event = SignalStreamCompleteEvent(
                    prospect_id=prospect_data.get("account_id", ""),
                    total_signals=len(signals),
                    completed_signals=persisted_count,
                    failed_signals=len(signals) - persisted_count,
                    stream_duration_ms=stream_duration_ms,
                )
                await self._emit_event(event)

            # Stage 4: LLM classification, hypothesis generation, narrative
            llm_output = await self._execute_llm_layer(signals, prospect_data, ctx)

            return SignalDetectionAgent__detect_signalsResult.model_validate({
                "signals": [s.model_dump() for s in signals],
                "processing_metadata": processing_metadata,
                "message": f"Detected {len(signals)} operational signals",
                "llm_output": llm_output,
            })


        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"Signal detection failed: {e}",
                extra={
                    "tenant_id": ctx.tenant_id,
                    "trace_id": ctx.trace_id,
                },
            )

            # Always emit the stream failure event before deciding how to handle.
            if self.stream_callback:
                event = SignalFailedEvent(
                    prospect_id=prospect_data.get("account_id", ""),
                    error_category=ErrorCategory.UNKNOWN,
                    error_message="Signal detection failed",
                    retryable=False,
                )
                await self._emit_event(event)

            # Governance and programming errors (ValueError subclasses: missing
            # tenant context, invalid state, policy violations) must propagate so
            # the caller can handle them explicitly. Safe LLM runtime failures
            # (network, timeout, rate-limit, parse) degrade gracefully.
            if isinstance(e, ValueError):
                raise

            agent_result = AgentResult(
                payload={},
                workflow_type="signal_detection",
                tenant_id=ctx.tenant_id or "",
                trace_id=ctx.trace_id or "",
            )
            agent_result.payload = {
                "classified_signals": [],
                "hypotheses": [],
                "narrative": "",
                "top_signals": [],
                "evidence_refs": [],
            }
            agent_result.degraded_reason = "llm_failed"
            agent_result.human_review_required = True
            agent_result.customer_facing_allowed = False

            return SignalDetectionAgent__detect_signalsResult.model_validate({
                "signals": [],
                "processing_metadata": processing_metadata,
                "message": f"Signal detection degraded: {type(e).__name__}",
                "llm_output": agent_result.to_dict(),
            })

    async def _stream_detection(
        self,
        parameters: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Streaming version of signal detection.

        Same pipeline as _detect_signals but with real-time event emission.
        """
        self.stream_callback = parameters.get("stream_callback")
        return await self._detect_signals(parameters, ctx)

    async def _extract_signals_from_layer2(
        self,
        prospect_data: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Call Layer 2 for signal extraction.

        Args:
            prospect_data: Prospect setup data
            ctx: Request context

        Returns:
            Extraction result with signals list
        """
        client = self._get_layer2_client()

        try:
            result = await client.extract_operational_signals(
                prospect_data=prospect_data,
                trace_id=ctx.trace_id,
            )
            return result
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Layer 2 extraction failed: {e}")
            # Return empty result on failure
            return SignalDetectionAgent__extract_signals_from_layer2Result.model_validate({
                "signals": [],
                "duration_ms": 0,
                "error": "Signal extraction failed",
                "error_code": "SIGNAL_EXTRACTION_ERROR",
            })


    def _create_pain_signal(
        self,
        raw_signal: dict[str, Any],
        prospect_data: dict[str, Any],
        ctx: RequestContext,
    ) -> PainSignal | None:
        """Create PainSignal from raw extraction result.

        Returns ``None`` (and logs a warning) when ``account_id`` is absent from
        *prospect_data*, so the caller can skip the record rather than persisting
        a signal with an empty account identifier.
        """
        account_id = prospect_data.get("account_id")
        if not account_id:
            logger.warning(
                "Skipping pain signal creation: account_id missing from prospect_data"
            )
            return None

        raw_explanation = raw_signal.get("confidence_explanation", "")
        # PainSignal requires confidence_explanation min_length=10; pad if needed
        confidence_explanation = (
            raw_explanation if len(raw_explanation) >= 10
            else (raw_explanation.strip() + " (extracted)").ljust(10)
        )
        description = raw_signal.get("description", "")
        # PainSignal requires description min_length=10
        if len(description) < 10:
            description = (description.strip() + " (extracted)").ljust(10)
        return PainSignal(
            id=f"sig_{self._id_gen.generate()[:12]}",
            name=raw_signal.get("name", "Unknown Signal"),
            category=SignalCategory.OPERATIONAL,
            description=description,
            confidence_score=raw_signal.get("confidence_score", 0.0),
            confidence_explanation=confidence_explanation,
            trend_direction=TrendDirection(raw_signal.get("trend_direction", "new")),
            trend_explanation=raw_signal.get("trend_explanation", ""),
            account_id=account_id,
            tenant_id=ctx.tenant_id,
            extraction_trace_id=ctx.trace_id,
            source_prompt_id=prospect_data.get("prompt_id", ""),
        )

    async def _enrich_with_evidence(
        self,
        signal: PainSignal,
        ctx: RequestContext,
    ) -> PainSignal:
        """Enrich signal with evidence matches from Layer 3.

        Args:
            signal: Signal to enrich
            ctx: Request context

        Returns:
            Enriched signal with evidence matches
        """
        client = self._get_layer3_client()

        try:
            evidence_matches = await client.find_matching_evidence(
                signal_description=signal.description,
                industry=None,  # Could extract from context
                limit=self.evidence_match_limit,
                tenant_id=ctx.tenant_id,
            )

            signal.evidence_matches = [
                EvidenceMatch(
                    evidence_id=match.get("evidence_id", ""),
                    evidence_type=match.get("evidence_type", "case_study"),
                    title=match.get("title", ""),
                    match_score=match.get("match_score", 0),
                    match_reasoning=match.get("match_reasoning", ""),
                    relevance_quote=match.get("relevance_quote"),
                )
                for match in evidence_matches
            ]

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Evidence matching failed for signal {signal.id}: {e}")

        return signal

    async def _quantify_impact(
        self,
        signal: PainSignal,
        prospect_data: dict[str, Any],
        ctx: RequestContext,
    ) -> PainSignal:
        """Quantify signal impact using Layer 3 formulas.

        Args:
            signal: Signal to quantify
            prospect_data: Prospect data for variable extraction
            ctx: Request context

        Returns:
            Signal with impact_value and formula reference
        """
        client = self._get_layer3_client()

        try:
            quantification = await client.quantify_signal(
                signal_name=signal.name,
                signal_description=signal.description,
                impact_indicators=signal.impact_indicators,
                industry=prospect_data.get("industry"),
                prospect_data=prospect_data,
                tenant_id=ctx.tenant_id,
            )

            if quantification.get("success"):
                signal.impact_value = quantification.get("impact_value")
                signal.impact_unit = quantification.get("impact_unit")
                signal.impact_formula_id = quantification.get("formula_id")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Impact quantification failed for signal {signal.id}: {e}")

        return signal

    async def _execute_llm_layer(
        self,
        signals: list[PainSignal],
        prospect_data: dict[str, Any],
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Run LLM classification, hypothesis generation, and narrative over detected signals.

        Three sequential prompts:
        1. ``classification`` — classify each signal by type and confidence
        2. ``hypothesis_generation`` — generate value hypotheses from high-confidence clusters
        3. ``narrative`` — produce a 1-paragraph signal summary

        Returns an ``AgentResult`` serialised to dict.  Degrades gracefully on failure.
        """
        account_name = (
            prospect_data.get("account_name")
            or prospect_data.get("name")
            or prospect_data.get("account_id", "Unknown Account")
        )
        tenant_id = ctx.tenant_id or ""
        trace_id = ctx.trace_id or ""

        agent_result = AgentResult(
            payload={},
            workflow_type="signal_detection",
            tenant_id=tenant_id,
            trace_id=trace_id,
        )

        if not signals:
            agent_result.payload = {"signals": [], "hypotheses": [], "narrative": ""}
            agent_result.degraded_reason = "no_signals"
            return agent_result.to_dict()

        try:
            registry = get_prompt_registry()
            system_tmpl = registry.get("signal_detection", "system")
            class_tmpl = registry.get("signal_detection", "classification")
            hyp_tmpl = registry.get("signal_detection", "hypothesis_generation")
            narr_tmpl = registry.get("signal_detection", "narrative")

            provider = get_llm_provider(self.config)
            client = GovernedLLMClient(
                provider=provider,
                provider_name=self._resolve_provider_name(),
            )
            system_msg = {"role": "system", "content": system_tmpl.body}

            # Compact signal representation for prompts
            signals_json = json.dumps(
                [
                    {
                        "id": s.id,
                        "category": s.category.value if hasattr(s.category, "value") else str(s.category),
                        "description": s.description,
                        "confidence": s.confidence_score,
                        "source": getattr(s, "source_ref", ""),
                    }
                    for s in signals[:15]  # cap at 15 signals
                ],
                indent=2,
            )
            entities_json = json.dumps(
                list({s.category.value if hasattr(s.category, "value") else str(s.category) for s in signals}),
                indent=2,
            )

            # ── Step 1: classification ──────────────────────────────────
            class_content = class_tmpl.render(
                account_name=account_name,
                signals_json=signals_json,
                entities_json=entities_json,
            )
            class_result = await client.call(
                model_task=class_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": class_content}],
                temperature=class_tmpl.temperature,
                max_tokens=class_tmpl.max_tokens,
                call_id=f"sd_class_{trace_id}",
            )
            classified = parse_llm_json(class_result.content)

            # ── Step 2: hypothesis generation (high-confidence only) ────
            high_conf = [
                s for s in signals if s.confidence_score >= 0.6
            ]
            high_conf_json = json.dumps(
                [
                    {
                        "id": s.id,
                        "category": s.category.value if hasattr(s.category, "value") else str(s.category),
                        "description": s.description,
                        "confidence": s.confidence_score,
                    }
                    for s in high_conf[:10]
                ],
                indent=2,
            )
            hyp_content = hyp_tmpl.render(
                account_name=account_name,
                high_confidence_signals_json=high_conf_json,
            )
            hyp_result = await client.call(
                model_task=hyp_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": hyp_content}],
                temperature=hyp_tmpl.temperature,
                max_tokens=hyp_tmpl.max_tokens,
                call_id=f"sd_hyp_{trace_id}",
            )
            hypotheses = parse_llm_json(hyp_result.content)

            # ── Step 3: narrative ───────────────────────────────────────
            signal_summary = {
                "total": len(signals),
                "high_confidence": len(high_conf),
                "classified_types": classified.get("signal_types", []),
            }
            narr_content = narr_tmpl.render(
                account_name=account_name,
                hypotheses_json=json.dumps(hypotheses.get("hypotheses", []), indent=2),
                signal_summary_json=json.dumps(signal_summary, indent=2),
            )
            narr_result = await client.call(
                model_task=narr_tmpl.model_task,
                messages=[system_msg, {"role": "user", "content": narr_content}],
                temperature=narr_tmpl.temperature,
                max_tokens=narr_tmpl.max_tokens,
                call_id=f"sd_narr_{trace_id}",
            )
            narrative_data = parse_llm_json(narr_result.content)

            total_prompt = class_result.prompt_tokens + hyp_result.prompt_tokens + narr_result.prompt_tokens
            total_completion = class_result.completion_tokens + hyp_result.completion_tokens + narr_result.completion_tokens
            confidence = float(narrative_data.get("confidence", 0.7))

            agent_result.payload = {
                "classified_signals": classified.get("classified_signals", []),
                "hypotheses": hypotheses.get("hypotheses", []),
                "narrative": narrative_data.get("narrative", ""),
                "top_signals": narrative_data.get("top_signals", []),
                "evidence_refs": narrative_data.get("evidence_refs", []),
            }
            agent_result.mark_llm_enriched(
                model=narr_result.model,
                prompt_tokens=total_prompt,
                completion_tokens=total_completion,
                confidence=confidence,
            )
            logger.info(
                "Signal detection LLM layer complete: model=%s tokens=%d",
                narr_result.model,
                total_prompt + total_completion,
            )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Signal detection LLM layer failed", extra={"code": "llm_failed"})
            agent_result.payload = {
                "classified_signals": [],
                "hypotheses": [],
                "narrative": "",
                "top_signals": [],
                "evidence_refs": [],
            }
            agent_result.degraded_reason = "llm_failed"

        return agent_result.to_dict()

    def _resolve_provider_name(self) -> str:
        import os
        return (
            os.getenv("LAYER4_LLM_PROVIDER")
            or (self.config.get("llm_provider") if isinstance(self.config, dict) else None)
            or getattr(self.config, "llm_provider", None)
            or "together"
        )

    async def _persist_signal(
        self,
        signal: PainSignal,
        ctx: RequestContext,
    ) -> None:
        """Persist signal to Layer 3 knowledge graph.

        Args:
            signal: Signal to persist
            ctx: Request context
        """
        client = self._get_layer3_client()

        try:
            await client.persist_signal(
                signal_data=signal.model_dump(),
                tenant_id=ctx.tenant_id,
            )

            # Link evidence if available
            if signal.evidence_matches:
                await client.link_evidence(
                    signal_id=signal.id,
                    evidence_matches=[match.model_dump() for match in signal.evidence_matches],
                    tenant_id=ctx.tenant_id,
                )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Signal persistence failed: {e}")
            raise

    async def _emit_event(self, event: Any) -> None:
        """Emit streaming event via callback.

        Args:
            event: Event to emit
        """
        if self.stream_callback:
            try:
                await self.stream_callback(event.to_json())
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Failed to emit event: {e}")

    async def get_account_signals(
        self,
        account_id: str,
        tenant_id: str,
        category: str | None = None,
    ) -> list[PainSignal]:
        """Retrieve signals for an account.

        Args:
            account_id: Account identifier
            tenant_id: Tenant identifier
            category: Optional category filter

        Returns:
            List of signals
        """
        client = self._get_layer3_client()

        try:
            signals_data = await client.get_signals_for_account(
                account_id=account_id,
                tenant_id=tenant_id,
                category=category,
            )

            return [PainSignal.model_validate(data) for data in signals_data]

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve account signals: {e}")
            return []
