from __future__ import annotations

"""
Intelligence Orchestrator — Data Intelligence Layer Phase 3, Task 3.2.

Provides cross-layer orchestration that assembles intelligence from
all DIL services into unified deliverables:

  - Account Intelligence Briefing: Full account dossier combining
    enrichment, signals, hypotheses, competitive intel, ROI, evidence
  - Deal Readiness Score: Composite score indicating how prepared
    the sales team is to engage an account
  - Pipeline Intelligence Summary: Aggregated intelligence across
    all active accounts

Architecture:
  - Orchestrates calls across L3 (Neo4j) and L4 (PostgreSQL + Neo4j)
  - Each method accepts service instances or creates them from drivers
  - Designed for use by the route layer which injects dependencies
  - All methods are tenant-scoped
"""


import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.services.tenant_cypher import fetch_tenant_validated_records


class IntelligenceOrchestrator_get_deal_readinessResult(TypedDictModel):
    account_id: Any
    generated_at: Any

class IntelligenceOrchestrator__compute_deal_readinessResult(TypedDictModel):
    components: Any
    label: Any
    recommendations: Any
    score: Any

class IntelligenceOrchestrator_get_pipeline_summaryResult(TypedDictModel):
    accounts: Any
    generated_at: Any
    summary: dict[str, Any]
    tenant_id: Any

class IntelligenceOrchestrator__get_competitive_landscapeResult(TypedDictModel):
    overall_win_rate: Any | None = None
    total_competitors: bool | int
    total_losses: int
    total_wins: int

class IntelligenceOrchestrator__get_roi_summaryResult(TypedDictModel):
    pass

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = structlog.get_logger()


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        return "default"
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        return "default"


# ---------------------------------------------------------------------------
# Deal Readiness Scoring Weights
# ---------------------------------------------------------------------------

READINESS_WEIGHTS = {
    "enrichment_complete": 0.15,
    "signals_identified": 0.15,
    "hypotheses_generated": 0.20,
    "hypotheses_validated": 0.10,
    "competitive_intel": 0.10,
    "roi_calculated": 0.15,
    "evidence_matched": 0.10,
    "narrative_generated": 0.05,
}

READINESS_THRESHOLDS = {
    "not_ready": 0.0,
    "early_stage": 0.20,
    "developing": 0.40,
    "prepared": 0.60,
    "deal_ready": 0.80,
}

# Limits and batch sizes
DEFAULT_TOP_SIGNALS = 5
DEFAULT_TOP_EVIDENCE = 5
DEFAULT_HYPOTHESES_LIMIT = 20
MAX_SIGNALS_FOR_READINESS = 5
MAX_HYPOTHESES_FOR_READINESS = 5
MAX_EVIDENCE_FOR_READINESS = 3
MAX_COMPETITORS_FOR_READINESS = 3
MAX_SIGNALS_QUERY_LIMIT = 20  # For internal data fetchers


def _readiness_label(score: float) -> str:
    """Map a readiness score to a human-readable label."""
    if score >= READINESS_THRESHOLDS["deal_ready"]:
        return "deal_ready"
    if score >= READINESS_THRESHOLDS["prepared"]:
        return "prepared"
    if score >= READINESS_THRESHOLDS["developing"]:
        return "developing"
    if score >= READINESS_THRESHOLDS["early_stage"]:
        return "early_stage"
    return "not_ready"


# ---------------------------------------------------------------------------
# Intelligence Orchestrator
# ---------------------------------------------------------------------------


class IntelligenceOrchestrator:
    """Cross-layer orchestrator for unified intelligence deliverables."""

    def __init__(self, neo4j_driver: Any, db: Any | None = None):
        self._driver = neo4j_driver
        self._db = db

    # ------------------------------------------------------------------
    # Account Intelligence Briefing
    # ------------------------------------------------------------------

    async def get_account_briefing(
        self,
        account_id: str,
        *,
        include_narrative: bool = False,
        top_n_hypotheses: int = 5,
        roi_scenario: str = "moderate",
    ) -> dict[str, Any]:
        """Assemble a complete intelligence briefing for an account.

        Args:
            account_id: Account identifier (must be non-empty)
            include_narrative: Whether to include narrative section
            top_n_hypotheses: Number of top hypotheses to include
            roi_scenario: ROI calculation scenario (conservative/moderate/aggressive)

        Returns:
            Intelligence briefing dictionary

        Raises:
            ValueError: If account_id is empty or invalid
        """
        # Validate account_id
        if not account_id or not isinstance(account_id, str):
            raise ValueError("account_id must be a non-empty string")

        now = datetime.now(UTC).isoformat()

        # Gather all intelligence components in parallel with error isolation

        async def _safe_gather() -> tuple[
            list[dict[str, Any]],
            list[dict[str, Any]],
            dict[str, Any],
            dict[str, Any],
            list[dict[str, Any]],
            dict[str, Any] | None,
        ]:
            """Gather all data with individual error handling."""
            signals_task = self._get_account_signals(account_id)
            hypotheses_task = self._get_account_hypotheses(account_id, top_n_hypotheses)
            competitive_task = self._get_competitive_landscape()
            roi_task = self._get_roi_summary(account_id)
            evidence_task = self._get_matched_evidence(account_id)
            narrative_task = (
                self._get_latest_narrative(account_id)
                if include_narrative
                else asyncio.sleep(0)
            )

            results = await asyncio.gather(
                signals_task,
                hypotheses_task,
                competitive_task,
                roi_task,
                evidence_task,
                narrative_task,
                return_exceptions=True,
            )

            signals = results[0] if not isinstance(results[0], Exception) else []
            hypotheses = results[1] if not isinstance(results[1], Exception) else []
            competitive = results[2] if not isinstance(results[2], Exception) else {}
            roi = results[3] if not isinstance(results[3], Exception) else {}
            evidence = results[4] if not isinstance(results[4], Exception) else []
            narrative = (
                results[5]
                if include_narrative and not isinstance(results[5], Exception)
                else None
            )

            return signals, hypotheses, competitive, roi, evidence, narrative

        signals, hypotheses, competitive, roi, evidence, narrative_summary = (
            await _safe_gather()
        )

        # Compute deal readiness
        readiness = self._compute_deal_readiness(
            signals=signals,
            hypotheses=hypotheses,
            competitive=competitive,
            roi=roi,
            evidence=evidence,
            narrative=narrative_summary,
        )

        briefing = {
            "briefing_id": str(uuid.uuid4()),
            "account_id": account_id,
            "generated_at": now,
            "deal_readiness": readiness,
            "sections": {
                "signals": {
                    "count": len(signals),
                    "top_signals": signals[:DEFAULT_TOP_SIGNALS],
                },
                "value_hypotheses": {
                    "count": len(hypotheses),
                    "top_hypotheses": hypotheses,
                },
                "competitive_landscape": competitive,
                "roi_projection": roi,
                "evidence": {
                    "count": len(evidence),
                    "case_studies": evidence[:DEFAULT_TOP_EVIDENCE],
                },
            },
        }

        if narrative_summary:
            briefing["sections"]["narrative"] = narrative_summary

        logger.info(
            "account_briefing_generated",
            account_id=account_id,
            readiness_score=readiness["score"],
            readiness_label=readiness["label"],
        )

        return briefing

    # ------------------------------------------------------------------
    # Deal Readiness Score
    # ------------------------------------------------------------------

    async def get_deal_readiness(
        self, account_id: str
    ) -> dict[str, Any]:
        """Calculate deal readiness score for an account.

        Args:
            account_id: Account identifier (must be non-empty)

        Returns:
            Deal readiness score dictionary

        Raises:
            ValueError: If account_id is empty or invalid
        """
        # Validate account_id
        if not account_id or not isinstance(account_id, str):
            raise ValueError("account_id must be a non-empty string")

        async def _safe_gather() -> tuple[
            list[dict[str, Any]],
            list[dict[str, Any]],
            dict[str, Any],
            dict[str, Any],
            list[dict[str, Any]],
            dict[str, Any] | None,
        ]:
            """Gather all data with individual error handling."""
            signals_task = self._get_account_signals(account_id)
            hypotheses_task = self._get_account_hypotheses(
                account_id, limit=DEFAULT_HYPOTHESES_LIMIT
            )
            competitive_task = self._get_competitive_landscape()
            roi_task = self._get_roi_summary(account_id)
            evidence_task = self._get_matched_evidence(account_id)
            narrative_task = self._get_latest_narrative(account_id)

            results = await asyncio.gather(
                signals_task,
                hypotheses_task,
                competitive_task,
                roi_task,
                evidence_task,
                narrative_task,
                return_exceptions=True,
            )

            signals = results[0] if not isinstance(results[0], Exception) else []
            hypotheses = results[1] if not isinstance(results[1], Exception) else []
            competitive = results[2] if not isinstance(results[2], Exception) else {}
            roi = results[3] if not isinstance(results[3], Exception) else {}
            evidence = results[4] if not isinstance(results[4], Exception) else []
            narrative = results[5] if not isinstance(results[5], Exception) else None

            return signals, hypotheses, competitive, roi, evidence, narrative

        signals, hypotheses, competitive, roi, evidence, narrative = (
            await _safe_gather()
        )

        readiness = self._compute_deal_readiness(
            signals=signals,
            hypotheses=hypotheses,
            competitive=competitive,
            roi=roi,
            evidence=evidence,
            narrative=narrative,
        )

        return IntelligenceOrchestrator_get_deal_readinessResult.model_validate({
            "account_id": account_id,
            "generated_at": datetime.now(UTC).isoformat(),
            **readiness,
        })


    def _compute_deal_readiness(
        self,
        *,
        signals: list[dict],
        hypotheses: list[dict],
        competitive: dict,
        roi: dict,
        evidence: list[dict],
        narrative: dict | None,
    ) -> dict[str, Any]:
        """Compute a weighted deal readiness score."""
        components: dict[str, float] = {}

        # Signals identified (0-1 based on count, capped)
        components["signals_identified"] = min(
            len(signals) / MAX_SIGNALS_FOR_READINESS, 1.0
        )

        # Hypotheses generated (0-1 based on count, capped)
        components["hypotheses_generated"] = min(
            len(hypotheses) / MAX_HYPOTHESES_FOR_READINESS, 1.0
        )

        # Hypotheses validated (ratio of validated to total)
        validated = sum(1 for h in hypotheses if h.get("status") == "validated")
        components["hypotheses_validated"] = (
            validated / len(hypotheses) if hypotheses else 0.0
        )

        # Competitive intel available
        comp_count = competitive.get("total_competitors", 0)
        components["competitive_intel"] = min(
            comp_count / MAX_COMPETITORS_FOR_READINESS, 1.0
        )

        # ROI calculated
        has_roi = bool(roi.get("calculations") or roi.get("results"))
        components["roi_calculated"] = 1.0 if has_roi else 0.0

        # Evidence matched
        components["evidence_matched"] = min(
            len(evidence) / MAX_EVIDENCE_FOR_READINESS, 1.0
        )

        # Narrative generated
        components["narrative_generated"] = 1.0 if narrative else 0.0

        # Enrichment (assume complete if we have signals — simplified)
        components["enrichment_complete"] = 1.0 if signals else 0.0

        # Weighted score
        score = sum(
            components.get(k, 0) * w
            for k, w in READINESS_WEIGHTS.items()
        )
        score = round(min(score, 1.0), 3)

        return IntelligenceOrchestrator__compute_deal_readinessResult.model_validate({
            "score": score,
            "label": _readiness_label(score),
            "components": {k: round(v, 3) for k, v in components.items()},
            "recommendations": self._generate_recommendations(components),
        })


    @staticmethod
    def _generate_recommendations(components: dict[str, float]) -> list[str]:
        """Generate actionable recommendations based on gaps."""
        recs = []
        if components.get("signals_identified", 0) < 0.5:
            recs.append("Run signal detection to identify more pain points for this account")
        if components.get("hypotheses_generated", 0) < 0.5:
            recs.append("Generate value hypotheses to map signals to product capabilities")
        if components.get("hypotheses_validated", 0) < 0.3:
            recs.append("Validate existing hypotheses with the prospect to increase confidence")
        if components.get("competitive_intel", 0) < 0.5:
            recs.append("Add competitive intelligence — identify key competitors in this deal")
        if components.get("roi_calculated", 0) < 1.0:
            recs.append("Run an ROI calculation to quantify the value proposition")
        if components.get("evidence_matched", 0) < 0.5:
            recs.append("Find relevant case studies and evidence to support the value story")
        if components.get("narrative_generated", 0) < 1.0:
            recs.append("Generate a sales narrative to package the intelligence for delivery")
        return recs

    # ------------------------------------------------------------------
    # Pipeline Intelligence
    # ------------------------------------------------------------------

    async def get_pipeline_summary(
        self,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregated intelligence across all accounts."""
        if tenant_id is None:
            tenant_id = _get_tenant_id()
        query = """
        MATCH (vh:ValueHypothesis {tenant_id: $tenant_id})
        WITH vh.account_id AS account_id,
             count(vh) AS hypothesis_count,
             avg(vh.confidence_score) AS avg_confidence,
             sum(vh.estimated_impact_usd) AS total_impact,
             collect(DISTINCT vh.status) AS statuses
        RETURN account_id,
               hypothesis_count,
               avg_confidence,
               total_impact,
               statuses
        ORDER BY total_impact DESC
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={"tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_pipeline_summary",
        )

        accounts = []
        total_pipeline_value = 0.0
        total_hypotheses = 0

        for r in records:
            acct_impact = r["total_impact"] or 0
            acct_hypotheses = r["hypothesis_count"] or 0
            statuses = r["statuses"] or []

            total_pipeline_value += acct_impact
            total_hypotheses += acct_hypotheses

            accounts.append({
                "account_id": r["account_id"],
                "hypothesis_count": acct_hypotheses,
                "avg_confidence": round(r["avg_confidence"] or 0, 3),
                "total_impact": round(acct_impact, 2),
                "has_validated": "validated" in statuses,
                "has_converted": "converted" in statuses,
            })

        return IntelligenceOrchestrator_get_pipeline_summaryResult.model_validate({
            "tenant_id": tenant_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_accounts": len(accounts),
                "total_hypotheses": total_hypotheses,
                "total_pipeline_value": round(total_pipeline_value, 2),
                "avg_hypotheses_per_account": (
                    round(total_hypotheses / len(accounts), 1) if accounts else 0
                ),
            },
            "accounts": accounts,
        })


    # ------------------------------------------------------------------
    # Internal Data Fetchers (Neo4j)
    # ------------------------------------------------------------------

    async def _get_account_signals(
        self, account_id: str
    ) -> list[dict[str, Any]]:
        """Fetch ValueSignals for an account from the L2.5 Signal Refinery.

        Prefers the canonical L2.5 API over the legacy Neo4j Signal query.
        Falls back to the legacy graph query if the L2.5 service is unavailable.
        """
        try:
            from ..tools.signal_tools import get_account_signals as _get_signals
            signals = await _get_signals(
                account_id,
                lifecycle_states=["validated", "promoted", "extracted"],
                min_confidence=0.3,
                limit=MAX_SIGNALS_QUERY_LIMIT,
            )
            if signals:
                return signals
        except Exception:
            logger.warning(
                "L2.5 signal retrieval failed for account=%s — falling back to graph query",
                account_id,
                exc_info=True,
            )

        # Legacy fallback: query :Signal nodes from Neo4j
        tenant_id = _get_tenant_id()
        query = """
        MATCH (s:Signal {tenant_id: $tenant_id})
        WHERE s.account_id = $account_id OR s.target_account_id = $account_id
        RETURN s {.*} AS signal
        ORDER BY s.confidence_score DESC
        LIMIT $limit
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "account_id": account_id,
                "limit": MAX_SIGNALS_QUERY_LIMIT,
            },
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_account_signals",
        )
        return [r["signal"] for r in records]

    async def _get_account_hypotheses(
        self, account_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Fetch value hypotheses for an account."""
        tenant_id = _get_tenant_id()
        query = """
        MATCH (vh:ValueHypothesis {tenant_id: $tenant_id, account_id: $account_id})
        RETURN vh {.*} AS hypothesis
        ORDER BY vh.confidence_score DESC
        LIMIT $limit
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "account_id": account_id,
                "limit": limit,
            },
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_account_hypotheses",
        )
        return [r["hypothesis"] for r in records]

    async def _get_competitive_landscape(
        self
    ) -> dict[str, Any]:
        """Fetch competitive landscape summary."""
        tenant_id = _get_tenant_id()
        query = """
        MATCH (c:Competitor {tenant_id: $tenant_id})
        OPTIONAL MATCH (c)<-[won:WON_AGAINST]-(p1:Product)
        OPTIONAL MATCH (c)<-[lost:LOST_TO]-(p2:Product)
        RETURN count(DISTINCT c) AS total_competitors,
               count(DISTINCT won) AS total_wins,
               count(DISTINCT lost) AS total_losses
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={"tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_competitive_landscape",
        )
        record = records[0] if records else None

        if not record:
            return IntelligenceOrchestrator__get_competitive_landscapeResult.model_validate({"total_competitors": 0, "total_wins": 0, "total_losses": 0})

        total_wins = record["total_wins"] or 0
        total_losses = record["total_losses"] or 0
        total_deals = total_wins + total_losses

        return IntelligenceOrchestrator__get_competitive_landscapeResult.model_validate({
            "total_competitors": record["total_competitors"] or 0,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "overall_win_rate": round(total_wins / total_deals, 3) if total_deals > 0 else 0,
        })


    async def _get_roi_summary(
        self, account_id: str
    ) -> dict[str, Any]:
        """Fetch most recent ROI calculation for an account."""
        tenant_id = _get_tenant_id()
        query = """
        MATCH (rc:ROICalculation {tenant_id: $tenant_id, account_id: $account_id})
        RETURN rc {.*} AS calculation
        ORDER BY rc.created_at DESC
        LIMIT 1
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "account_id": account_id,
            },
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_roi_summary",
        )
        record = records[0] if records else None

        if not record or not record["calculation"]:
            return IntelligenceOrchestrator__get_roi_summaryResult.model_validate({})

        import json
        calc = record["calculation"]
        for json_field in ("inputs", "outputs", "assumptions"):
            if isinstance(calc.get(json_field), str):
                try:
                    calc[json_field] = json.loads(calc[json_field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return calc

    async def _get_matched_evidence(
        self, account_id: str
    ) -> list[dict[str, Any]]:
        """Fetch evidence/case studies relevant to an account's industry."""
        tenant_id = _get_tenant_id()
        query = """
        MATCH (e:Evidence {tenant_id: $tenant_id})
        RETURN e {.*} AS evidence
        ORDER BY e.created_at DESC
        LIMIT 10
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={"tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_recent_evidence",
        )
        return [r["evidence"] for r in records]

    async def _get_latest_narrative(
        self, account_id: str
    ) -> dict[str, Any] | None:
        """Fetch the most recent narrative for an account."""
        tenant_id = _get_tenant_id()
        query = """
        MATCH (n:Narrative {tenant_id: $tenant_id, account_id: $account_id})
        RETURN n {.id, .title, .status, .tone, .audience, .version, .created_at} AS narrative
        ORDER BY n.updated_at DESC
        LIMIT 1
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "account_id": account_id,
            },
            tenant_id=tenant_id,
            operation="intelligence_orchestrator.get_latest_narrative",
        )
        record = records[0] if records else None

        if not record or not record["narrative"]:
            return None
        return record["narrative"]
