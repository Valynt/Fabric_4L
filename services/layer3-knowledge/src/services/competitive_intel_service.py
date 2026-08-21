from __future__ import annotations

"""
Competitive Intelligence Service — Data Intelligence Layer Phase 2, Task 2.2.

Manages competitive intelligence data in the Neo4j knowledge graph, including:
  - Competitor profiles with strengths, weaknesses, and market positioning
  - Battlecards linking competitors to products with differentiators
  - Win/loss tracking for competitive deals
  - Competitive landscape analysis per product

Architecture:
  - Competitor nodes store company-level competitive data
  - Battlecard nodes store product-specific competitive positioning
  - COMPETES_WITH relationships link Products to Competitors (with overlap_score)
  - WON_AGAINST / LOST_TO relationships track deal outcomes
  - All data is tenant-scoped for multi-tenancy isolation

Neo4j Node Schema:
  Competitor:
    id, tenant_id, name, domain, description, founded_year,
    strengths (list), weaknesses (list), market_position,
    pricing_tier, target_segments (list), created_at, updated_at

  Battlecard:
    id, tenant_id, competitor_id, product_id,
    positioning, differentiators (list), objection_handlers (list),
    talk_tracks (list), win_themes (list), trap_questions (list),
    last_reviewed_at, created_at, updated_at
"""


import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.audited_mutation import AuditedGraphMutation
from ..db.query_execution import run_validated_query
from ..security.query_validator import ValidatedNeo4jSession
from ..utils.cypher_security import ALLOWED_REL_TYPES, validate_cypher_identifier
from .cypher_scope_guard import (
    validate_tenant_scoped_cypher,
)


class CompetitiveIntelService_add_competitorResult(TypedDictModel):
    id: Any

class CompetitiveIntelService_get_competitorResult(TypedDictModel):
    battlecards: Any
    competing_products: Any

class CompetitiveIntelService_list_competitorsResult(TypedDictModel):
    competitors: Any
    limit: Any
    skip: Any
    total: Any

class CompetitiveIntelService_add_battlecardResult(TypedDictModel):
    id: Any

class CompetitiveIntelService_record_win_lossResult(TypedDictModel):
    id: Any
    outcome: Any

class CompetitiveIntelService_analyze_competitive_landscapeResult(TypedDictModel):
    landscape: Any
    overall_win_rate: Any
    total_competitors: Any
    total_losses: Any
    total_wins: Any

class CompetitiveIntelService_get_win_loss_summaryResult(TypedDictModel):
    competitors: Any
    total_competitors: Any

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None

logger = structlog.get_logger()
_TENANT_OWNED_LABELS = {"Competitor", "Product", "Battlecard"}


def _get_tenant_id() -> str:
    """Safely retrieve tenant ID from request context.

    Returns "default" if context is not available (e.g., in tests or background tasks).
    """
    if not require_context:
        raise RuntimeError("tenant_id is required in request context")
    try:
        return str(require_context().tenant_id)
    except RuntimeError:
        raise RuntimeError("tenant_id is required in request context")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class CompetitorCreate:
    """Input for creating a competitor node."""

    name: str
    description: str
    domain: str | None = None
    founded_year: int | None = None
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    market_position: str = "challenger"  # leader, challenger, niche, emerging
    pricing_tier: str = "mid"  # low, mid, high, premium
    target_segments: list[str] = field(default_factory=list)


@dataclass
class BattlecardCreate:
    """Input for creating a battlecard."""

    product_id: str
    positioning: str  # How we position against this competitor
    differentiators: list[str] = field(default_factory=list)
    objection_handlers: list[dict[str, str]] = field(default_factory=list)
    talk_tracks: list[str] = field(default_factory=list)
    win_themes: list[str] = field(default_factory=list)
    trap_questions: list[str] = field(default_factory=list)


@dataclass
class WinLossRecord:
    """Input for recording a win or loss against a competitor."""

    competitor_id: str
    product_id: str
    outcome: str  # "won" or "lost"
    deal_size_usd: float = 0.0
    reason: str = ""
    industry: str = ""
    deal_date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ---------------------------------------------------------------------------
# Competitive Intelligence Service
# ---------------------------------------------------------------------------


class CompetitiveIntelService:
    """Service for managing competitive intelligence in the knowledge graph."""

    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    @staticmethod
    def _validate_query_scope(query: str) -> None:
        validate_tenant_scoped_cypher(
            query,
            tenant_owned_labels=_TENANT_OWNED_LABELS,
            query_name="CompetitiveIntelService",
        )

    async def _run_cypher(
        self,
        session: Any,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """Execute Cypher through mandatory validation gateway."""
        params = parameters or {}
        tenant_id = params.get("tenant_id", None)
        if not tenant_id:
            raise RuntimeError("tenant_id is required for CompetitiveIntelService cypher execution")
        self._validate_query_scope(query)
        validated_session = ValidatedNeo4jSession(session, tenant_id=str(tenant_id), strict=True)
        return await run_validated_query(
            validated_session,
            query,
            params,
            tenant_id=str(tenant_id),
            require_explicit_tenant_id=True,
            query_name="competitive_intel_service.run_cypher",
        )

    # ------------------------------------------------------------------
    # Competitor CRUD
    # ------------------------------------------------------------------

    async def add_competitor(
        self,
        tenant_id: str,
        competitor: CompetitorCreate,
    ) -> dict[str, Any]:
        """Create a Competitor node in the knowledge graph."""
        competitor_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        competitor_props = {
            "id": competitor_id,
            "tenant_id": tenant_id,
            "name": competitor.name,
            "description": competitor.description,
            "domain": competitor.domain or "",
            "founded_year": competitor.founded_year,
            "strengths": competitor.strengths,
            "weaknesses": competitor.weaknesses,
            "market_position": competitor.market_position,
            "pricing_tier": competitor.pricing_tier,
            "target_segments": competitor.target_segments,
            "entity_type": "Competitor",
            "created_at": now,
            "updated_at": now,
        }
        async with self._driver.session() as session:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="competitive_intel_service.add_competitor",
            )
            await mutation.write_node("Competitor", competitor_id, competitor_props)

        logger.info(
            "competitor_created",
            competitor_id=competitor_id,
            name=competitor.name,
        )
        return CompetitiveIntelService_add_competitorResult.model_validate(competitor_props)

    async def get_competitor(
        self,
        tenant_id: str,
        competitor_id: str,
    ) -> dict[str, Any] | None:
        """Get a single competitor with related products and battlecards."""
        query = """
        MATCH (c:Competitor {id: $competitor_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[cw:COMPETES_WITH]->(c)
        OPTIONAL MATCH (bc:Battlecard {competitor_id: $competitor_id, tenant_id: $tenant_id})
        RETURN c {.*} AS competitor,
               collect(DISTINCT p {.id, .name, overlap_score: cw.overlap_score}) AS competing_products,
               collect(DISTINCT bc {.id, .product_id, .positioning}) AS battlecards
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {
                "competitor_id": competitor_id,
                "tenant_id": tenant_id,
            })
            record = await result.single()

        if not record or not record["competitor"]:
            return None

        return CompetitiveIntelService_get_competitorResult.model_validate({
            **record["competitor"],
            "competing_products": record["competing_products"],
            "battlecards": record["battlecards"],
        })


    async def list_competitors(
        self,
        tenant_id: str,
        *,
        market_position: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List competitors with optional filtering."""
        where_clauses: list[str] = []
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "skip": skip,
            "limit": limit,
        }

        if market_position:
            where_clauses.append("c.market_position = $market_position")
            params["market_position"] = market_position

        where = " AND ".join(where_clauses) if where_clauses else "true"

        count_query = f"MATCH (c:Competitor {{tenant_id: $tenant_id}}) WHERE {where} RETURN count(c) AS total"
        list_query = f"""
        // strict-scoped-query-execution: where includes c.tenant_id = $tenant_id
        MATCH (c:Competitor {{tenant_id: $tenant_id}}) WHERE {where}
        OPTIONAL MATCH (p:Product {{tenant_id: $tenant_id}})-[cw:COMPETES_WITH]->(c)
        RETURN c {{.*}} AS competitor,
               count(DISTINCT p) AS product_overlap_count
        ORDER BY c.name
        SKIP $skip LIMIT $limit
        """

        self._validate_query_scope(count_query)
        self._validate_query_scope(list_query)

        async with self._driver.session() as session:
            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            count_result = await self._run_cypher(session, count_query, params)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            # strict-scoped-query-execution: dynamic query parameters include tenant_id
            list_result = await self._run_cypher(session, list_query, params)
            records = [record async for record in list_result]

        competitors = [
            {
                **r["competitor"],
                "product_overlap_count": r["product_overlap_count"],
            }
            for r in records
        ]

        return CompetitiveIntelService_list_competitorsResult.model_validate({
            "competitors": competitors,
            "total": total,
            "skip": skip,
            "limit": limit,
        })


    async def update_competitor(
        self,
        tenant_id: str,
        competitor_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a competitor's properties."""
        protected = {"id", "tenant_id", "entity_type", "created_at"}
        safe_updates = {k: v for k, v in updates.items() if k not in protected}
        safe_updates["updated_at"] = datetime.now(UTC).isoformat()

        if not safe_updates:
            return None

        set_parts = [f"c.{k} = ${k}" for k in safe_updates]
        set_clause = ", ".join(set_parts)

        query = f"""
        MATCH (c:Competitor {{id: $competitor_id, tenant_id: $tenant_id}})
        SET {set_clause}
        RETURN c {{.*}} AS competitor
        """
        params = {"competitor_id": competitor_id, "tenant_id": tenant_id, **safe_updates}

        async with self._driver.session() as session:
            # strict-scoped-query-execution: query parameters include tenant_id
            result = await self._run_cypher(session, query, params)
            record = await result.single()

        if not record:
            return None
        return record["competitor"]

    async def delete_competitor(
        self,
        tenant_id: str,
        competitor_id: str,
    ) -> bool:
        """Delete a competitor and all related battlecards."""
        exists_query = """
        MATCH (c:Competitor {id: $competitor_id, tenant_id: $tenant_id})
        RETURN count(c) AS found
        """
        battlecards_query = """
        MATCH (bc:Battlecard {competitor_id: $competitor_id, tenant_id: $tenant_id})
        RETURN collect(bc.id) AS battlecard_ids
        """
        async with self._driver.session() as session:
            result = await self._run_cypher(
                session,
                exists_query,
                {
                    "competitor_id": competitor_id,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()
            found_count = 0
            if record:
                try:
                    found_count = record["found"]
                except KeyError:
                    found_count = record["deleted"]
            if found_count <= 0:
                return False

            battlecard_result = await self._run_cypher(
                session,
                battlecards_query,
                {
                    "competitor_id": competitor_id,
                    "tenant_id": tenant_id,
                },
            )
            battlecard_record = await battlecard_result.single()
            battlecard_ids = []
            if battlecard_record:
                try:
                    battlecard_ids = battlecard_record["battlecard_ids"]
                except KeyError:
                    battlecard_ids = []

            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="competitive_intel_service.delete_competitor",
            )
            await mutation.delete_node("Competitor", competitor_id)
            for battlecard_id in battlecard_ids:
                await mutation.delete_node("Battlecard", battlecard_id)
        return True

    # ------------------------------------------------------------------
    # Battlecard Management
    # ------------------------------------------------------------------

    async def add_battlecard(
        self,
        tenant_id: str,
        competitor_id: str,
        battlecard: BattlecardCreate,
    ) -> dict[str, Any]:
        """Create a battlecard for a competitor + product pair."""
        bc_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Serialize objection handlers to strings for Neo4j storage
        objection_strs = [
            f"{oh.get('objection', '')}: {oh.get('response', '')}"
            for oh in battlecard.objection_handlers
        ]

        query = """
        MATCH (c:Competitor {id: $competitor_id, tenant_id: $tenant_id})
        MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
        CREATE (bc:Battlecard {
            id: $id,
            tenant_id: $tenant_id,
            competitor_id: $competitor_id,
            product_id: $product_id,
            positioning: $positioning,
            differentiators: $differentiators,
            objection_handlers: $objection_handlers,
            talk_tracks: $talk_tracks,
            win_themes: $win_themes,
            trap_questions: $trap_questions,
            entity_type: 'Battlecard',
            last_reviewed_at: $now,
            created_at: $now,
            updated_at: $now
        })
        MERGE (p)-[cw:COMPETES_WITH]->(c)
        ON CREATE SET cw.overlap_score = 0.5
        RETURN bc {.*} AS battlecard
        """
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {
                "id": bc_id,
                "tenant_id": tenant_id,
                "competitor_id": competitor_id,
                "product_id": battlecard.product_id,
                "positioning": battlecard.positioning,
                "differentiators": battlecard.differentiators,
                "objection_handlers": objection_strs,
                "talk_tracks": battlecard.talk_tracks,
                "win_themes": battlecard.win_themes,
                "trap_questions": battlecard.trap_questions,
                "now": now,
            })
            record = await result.single()

        logger.info(
            "battlecard_created",
            battlecard_id=bc_id,
            competitor_id=competitor_id,
            product_id=battlecard.product_id,
        )
        return CompetitiveIntelService_add_battlecardResult.model_validate({"id": bc_id, **(record["battlecard"] if record else {})})

    async def get_battlecard(
        self,
        tenant_id: str,
        competitor_id: str,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get battlecards for a competitor, optionally filtered by product."""
        where_clauses = [
            "bc.tenant_id = $tenant_id",
            "bc.competitor_id = $competitor_id",
        ]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "competitor_id": competitor_id,
        }

        if product_id:
            where_clauses.append("bc.product_id = $product_id")
            params["product_id"] = product_id

        where = " AND ".join(where_clauses)

        query = f"""
        // strict-scoped-query-execution: where includes bc.tenant_id = $tenant_id
        MATCH (bc:Battlecard {{tenant_id: $tenant_id}}) WHERE {where}
        RETURN bc {{.*}} AS battlecard
        ORDER BY bc.updated_at DESC
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            # strict-scoped-query-execution: query parameters include tenant_id
            result = await self._run_cypher(session, query, params)
            records = [record async for record in result]

        return [r["battlecard"] for r in records]

    # ------------------------------------------------------------------
    # Win/Loss Tracking
    # ------------------------------------------------------------------

    async def record_win_loss(
        self,
        tenant_id: str,
        record_data: WinLossRecord,
    ) -> dict[str, Any]:
        """Record a competitive win or loss."""
        wl_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        rel_type = "WON_AGAINST" if record_data.outcome == "won" else "LOST_TO"
        validate_cypher_identifier(rel_type, ALLOWED_REL_TYPES, kind="rel_type")

        query = (
            "MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})\n"
            "MATCH (c:Competitor {id: $competitor_id, tenant_id: $tenant_id})\n"
            f"CREATE (p)-[r:{rel_type} {{\n"  # cypher-dynamic-safe: validated against ALLOWED_REL_TYPES allowlist (hardcoded literal)
            "            id: $id,\n"
            "            deal_size_usd: $deal_size_usd,\n"
            "            reason: $reason,\n"
            "            industry: $industry,\n"
            "            deal_date: $deal_date,\n"
            "            recorded_at: $now\n"
            "        }]->(c)\n"
            "        RETURN r {.*} AS record\n"
            "        "
        )
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {
                "id": wl_id,
                "tenant_id": tenant_id,
                "product_id": record_data.product_id,
                "competitor_id": record_data.competitor_id,
                "deal_size_usd": record_data.deal_size_usd,
                "reason": record_data.reason,
                "industry": record_data.industry,
                "deal_date": record_data.deal_date,
                "now": now,
            })
            rec = await result.single()

        logger.info(
            "win_loss_recorded",
            outcome=record_data.outcome,
            competitor_id=record_data.competitor_id,
            product_id=record_data.product_id,
        )
        return CompetitiveIntelService_record_win_lossResult.model_validate({
            "id": wl_id,
            "outcome": record_data.outcome,
            **(rec["record"] if rec else {}),
        })


    # ------------------------------------------------------------------
    # Competitive Analysis
    # ------------------------------------------------------------------

    async def analyze_competitive_landscape(
        self,
        tenant_id: str,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        """Analyze the competitive landscape for a product or all products."""
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if product_id:
            product_match = "MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})-[cw:COMPETES_WITH]->(c)"
            params["product_id"] = product_id
        else:
            product_match = "OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[cw:COMPETES_WITH]->(c)"

        query = f"""
        // strict-scoped-query-execution: where includes c.tenant_id = $tenant_id
        MATCH (c:Competitor {{tenant_id: $tenant_id}})
        {product_match}
        OPTIONAL MATCH (p2:Product {{tenant_id: $tenant_id}})-[won:WON_AGAINST]->(c)
        OPTIONAL MATCH (p3:Product {{tenant_id: $tenant_id}})-[lost:LOST_TO]->(c)
        RETURN c {{.id, .name, .market_position, .pricing_tier}} AS competitor,
               count(DISTINCT p) AS product_overlaps,
               count(DISTINCT won) AS wins,
               count(DISTINCT lost) AS losses,
               COALESCE(cw.overlap_score, 0) AS overlap_score
        ORDER BY (count(DISTINCT won) + count(DISTINCT lost)) DESC
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            # strict-scoped-query-execution: query parameters include tenant_id
            result = await self._run_cypher(session, query, params)
            records = [record async for record in result]

        landscape = []
        total_wins = 0
        total_losses = 0

        for r in records:
            wins = r["wins"]
            losses = r["losses"]
            total_wins += wins
            total_losses += losses
            win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0

            landscape.append({
                "competitor": r["competitor"],
                "product_overlaps": r["product_overlaps"],
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 3),
                "overlap_score": r["overlap_score"],
            })

        overall_win_rate = (
            total_wins / (total_wins + total_losses)
            if (total_wins + total_losses) > 0
            else 0.0
        )

        return CompetitiveIntelService_analyze_competitive_landscapeResult.model_validate({
            "landscape": landscape,
            "total_competitors": len(landscape),
            "total_wins": total_wins,
            "total_losses": total_losses,
            "overall_win_rate": round(overall_win_rate, 3),
        })


    async def get_win_loss_summary(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Get aggregated win/loss data across all competitors."""
        query = """
        MATCH (c:Competitor {tenant_id: $tenant_id})
        OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[won:WON_AGAINST]->(c)
        OPTIONAL MATCH (p2:Product {tenant_id: $tenant_id})-[lost:LOST_TO]->(c)
        WITH c,
             count(DISTINCT won) AS wins,
             count(DISTINCT lost) AS losses,
             sum(COALESCE(won.deal_size_usd, 0)) AS won_revenue,
             sum(COALESCE(lost.deal_size_usd, 0)) AS lost_revenue
        RETURN c {.id, .name, .market_position} AS competitor,
               wins, losses, won_revenue, lost_revenue
        ORDER BY (wins + losses) DESC
        """
        self._validate_query_scope(query)
        async with self._driver.session() as session:
            result = await self._run_cypher(session, query, {"tenant_id": tenant_id})
            records = [record async for record in result]

        summary = []
        for r in records:
            wins = r["wins"]
            losses = r["losses"]
            total = wins + losses
            summary.append({
                "competitor": r["competitor"],
                "wins": wins,
                "losses": losses,
                "total_deals": total,
                "win_rate": round(wins / total, 3) if total > 0 else 0.0,
                "won_revenue": r["won_revenue"],
                "lost_revenue": r["lost_revenue"],
            })

        return CompetitiveIntelService_get_win_loss_summaryResult.model_validate({"competitors": summary, "total_competitors": len(summary)})
