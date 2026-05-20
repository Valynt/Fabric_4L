"""ContextGatheringService - real data fetcher for ValuePilot conversations.

When the GATE ConversationAgent is unavailable, this service queries
PostgreSQL (accounts) and Neo4j (signals, hypotheses, evidence) to build
a compact context payload for LLM consumption.

Design principles:
  - Graceful degradation: every method returns empty dict/list on failure
  - Tenant isolation: all queries are scoped to tenant_id
  - Compact output: shapes data for LLM prompts, not full API responses
  - Optional dependencies: works without neo4j_driver or db_session
"""

from __future__ import annotations

import logging
from collections.abc import Hashable
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel

from .tenant_cypher import fetch_tenant_validated_records, fetch_tenant_validated_single

logger = logging.getLogger(__name__)

MAX_SIGNALS = 10
MAX_HYPOTHESES = 8


def _hypothesis_dedup_key(hypothesis: dict[str, Any]) -> Hashable:
    """Return a deterministic de-duplication key for hypothesis rows."""
    hypothesis_id = hypothesis.get("id")
    if hypothesis_id:
        return f"id:{hypothesis_id}"

    return (
        "fallback",
        hypothesis.get("hypothesis_text"),
        hypothesis.get("status"),
        hypothesis.get("confidence_score"),
        hypothesis.get("value_path_category"),
        hypothesis.get("capability_name"),
        hypothesis.get("signal_name"),
    )


class ContextGathererResult(TypedDictModel):
    account: dict[str, Any]
    signals: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    evidence_summary: dict[str, Any]
    competitive: dict[str, Any]


class ContextGatheringService:
    """Fetch real account intelligence from PostgreSQL and Neo4j."""

    def __init__(
        self,
        *,
        neo4j_driver: Any | None = None,
        db: Any | None = None,
    ) -> None:
        self._driver = neo4j_driver
        self._db = db

    async def gather(
        self,
        *,
        account_id: str | None,
        tenant_id: str,
        industry: str | None = None,
    ) -> dict[str, Any]:
        """Build a compact intelligence dossier for the given account.

        Returns a dict shaped for injection into an LLM system prompt.
        """
        if not account_id:
            return {"tenant_id": tenant_id}

        account, signals, hypotheses, evidence = await self._gather_parallel(
            account_id=account_id,
            tenant_id=tenant_id,
            industry=industry,
        )

        result: dict[str, Any] = {
            "tenant_id": tenant_id,
            "account": account,
            "signals": signals,
            "hypotheses": hypotheses,
            "evidence": evidence,
        }

        return {k: v for k, v in result.items() if v is not None}

    async def _gather_parallel(
        self,
        *,
        account_id: str,
        tenant_id: str,
        industry: str | None,
    ) -> tuple[
        dict[str, Any] | None,
        list[dict[str, Any]],
        list[dict[str, Any]],
        dict[str, Any] | None,
    ]:
        """Run independent queries concurrently."""
        import asyncio

        tasks = [
            self._get_account_summary(account_id, tenant_id),
            self._get_account_signals(account_id, tenant_id),
            self._get_account_hypotheses(account_id, tenant_id),
            self._get_evidence_summary(industry, tenant_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        account = results[0] if not isinstance(results[0], Exception) else None
        signals = results[1] if not isinstance(results[1], Exception) else []
        hypotheses = results[2] if not isinstance(results[2], Exception) else []
        evidence = results[3] if not isinstance(results[3], Exception) else None

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.warning("Context gathering task %d failed: %s", i, r)

        return account, signals, hypotheses, evidence

    async def _get_account_summary(
        self,
        account_id: str,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Fetch account details from PostgreSQL."""
        if not self._db:
            return None

        try:
            from uuid import UUID

            from ..services.account_service import AccountService

            service = AccountService(self._db)
            account = await service.get_account(UUID(account_id), tenant_id=tenant_id)
            if not account:
                return None

            return {
                "id": str(account.id),
                "name": account.name,
                "industry": account.industry,
                "region": account.region,
                "company_size": account.company_size,
                "annual_revenue": account.annual_revenue,
                "headquarters": account.headquarters,
                "website": account.website,
                "stage": account.stage,
                "segment": account.segment,
                "owner_name": account.owner_name,
            }
        except Exception as e:
            logger.warning("Failed to load account summary: %s", e)
            return None

    async def _get_account_signals(
        self,
        account_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch top signals from Neo4j."""
        if not self._driver:
            return []

        try:
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
                    "account_id": account_id,
                    "limit": MAX_SIGNALS,
                },
                tenant_id=tenant_id,
                operation="context_gatherer.account_signals",
            )

            return [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "category": s.get("category"),
                    "confidence": s.get("confidence_score"),
                    "impact": s.get("impact_description") or s.get("description"),
                    "status": s.get("review_status", "unreviewed"),
                }
                for r in records
                if (s := r.get("signal"))
            ]
        except Exception as e:
            logger.warning("Failed to load account signals: %s", e)
            return []

    async def _get_account_hypotheses(
        self,
        account_id: str,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Fetch top hypotheses from Neo4j."""
        if not self._driver:
            return []

        try:
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
                    "account_id": account_id,
                    "limit": MAX_HYPOTHESES,
                },
                tenant_id=tenant_id,
                operation="context_gatherer.account_hypotheses",
            )

            return [
                {
                    "id": h.get("id"),
                    "text": h.get("hypothesis_text"),
                    "status": h.get("status"),
                    "confidence": h.get("confidence_score"),
                    "value_path": h.get("value_path_category"),
                    "estimated_impact_usd": h.get("estimated_impact_usd"),
                    "capability": h.get("capability_name"),
                    "signal": h.get("signal_name"),
                }
                for record in records
                if (h := record.get("hypothesis"))
            ]
        except Exception as e:
            logger.warning("Failed to load account hypotheses: %s", e)
            return []

    async def _get_evidence_summary(
        self,
        industry: str | None,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Fetch evidence counts from Neo4j."""
        if not self._driver:
            return None

        try:
            query = """
            MATCH (e:Evidence {tenant_id: $tenant_id})
            WHERE e.evidence_type = 'case_study'
            """
            params: dict[str, Any] = {}

            if industry:
                query += " AND e.industry = $industry"
                params["industry"] = industry

            query += """
            RETURN count(e) AS total,
                   avg(COALESCE(e.deal_size_usd, 0)) AS avg_deal_size,
                   avg(COALESCE(e.time_to_value_days, 180)) AS avg_ttv
            """

            record = await fetch_tenant_validated_single(
                driver=self._driver,
                query=query,
                params=params,
                tenant_id=tenant_id,
                operation="context_gatherer.evidence_summary",
            )

            if not record:
                return None

            return {
                "total_case_studies": record["total"] or 0,
                "avg_deal_size": round(record["avg_deal_size"] or 0, 2),
                "avg_time_to_value_days": round(record["avg_ttv"] or 180, 0),
            }
        except Exception as e:
            logger.warning("Failed to load evidence summary: %s", e)
            return None
