from __future__ import annotations

"""
Value Hypothesis Engine — Data Intelligence Layer Phase 2, Task 2.1.

Generates, ranks, and manages value hypotheses by connecting:
  - Account pain signals (from enrichment pipeline)
  - Product capabilities (from product portfolio graph)
  - Supporting evidence (from evidence library)
  - Estimated financial impact (from signal quantification)

A ValueHypothesis is the core intelligence artifact that powers value-based
selling. It answers: "For this account, this pain signal can be addressed by
this product capability, supported by this evidence, with this estimated impact."

Architecture:
  - Hypotheses are stored as ValueHypothesis nodes in Neo4j (L3 knowledge graph)
  - Generation queries traverse: Account → PainSignal → Capability → Product
  - Evidence matching uses: PainSignal.industry + Product → Evidence nodes
  - Ranking uses a weighted scoring model combining signal confidence,
    evidence strength, and estimated impact
  - The engine is in L4 because it orchestrates across multiple L3 services
    and may invoke LLM-based enrichment for hypothesis text generation
"""


import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.services.tenant_cypher import fetch_tenant_validated_records


class ValueHypothesis_to_node_propertiesResult(TypedDictModel):
    account_id: Any
    capability_id: Any
    capability_name: Any
    confidence_score: Any
    created_at: Any
    entity_type: str
    estimated_impact_usd: Any
    evidence_ids: Any
    hypothesis_text: Any
    id: Any
    impact_timeframe_days: Any
    product_id: Any
    product_name: Any
    signal_id: Any
    signal_name: Any
    status: Any
    tenant_id: Any
    updated_at: Any
    value_path_category: Any | None = None

class ValueHypothesisEngine_get_account_hypothesesResult(TypedDictModel):
    hypotheses: Any
    limit: Any
    skip: Any
    total: Any

class ValueHypothesisEngine_get_hypothesisResult(TypedDictModel):
    evidence_detail: Any
    product_detail: Any
    signal_detail: Any

class ValueHypothesisEngine_get_hypothesis_summaryResult(TypedDictModel):
    avg_confidence: Any | None = None
    avg_estimated_impact: Any | None = None
    by_status: dict[str, Any] | None = None
    total: int
    total_estimated_impact: Any | None = None
    unique_accounts: Any | None = None
    unique_products: Any | None = None

class ValueHypothesisEngine_convert_hypothesis_to_treeResult(TypedDictModel):
    hypothesis_id: str
    account_id: str
    tenant_id: str
    evidence_ids: list[str]
    value_model_id: str | None = None
    tree_id: str | None = None
    status: str

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Enums & Data Models
# ---------------------------------------------------------------------------


class HypothesisStatus(str, Enum):
    """Lifecycle status of a value hypothesis."""
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CONVERTED = "converted"  # Turned into a business case


class RankingStrategy(str, Enum):
    """Strategy for ranking hypotheses."""
    IMPACT = "impact"          # Highest estimated $ impact first
    CONFIDENCE = "confidence"  # Highest confidence score first
    BALANCED = "balanced"      # Weighted combination
    EVIDENCE = "evidence"      # Most evidence-backed first
    RECENCY = "recency"        # Most recently created first


@dataclass
class ValueHypothesis:
    """A value hypothesis connecting a pain signal to a product capability."""

    tenant_id: str
    account_id: str
    signal_id: str
    signal_name: str
    product_id: str
    product_name: str
    capability_id: str
    capability_name: str
    hypothesis_text: str
    confidence_score: float = 0.5
    estimated_impact_usd: float = 0.0
    impact_timeframe_days: int = 365
    evidence_ids: list[str] = field(default_factory=list)
    status: str = HypothesisStatus.DRAFT
    value_path_category: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_node_properties(self) -> dict[str, Any]:
        """Serialize to Neo4j node properties."""
        return ValueHypothesis_to_node_propertiesResult.model_validate({
            "id": self.id,
            "tenant_id": self.tenant_id,
            "account_id": self.account_id,
            "signal_id": self.signal_id,
            "signal_name": self.signal_name,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "capability_id": self.capability_id,
            "capability_name": self.capability_name,
            "hypothesis_text": self.hypothesis_text,
            "confidence_score": self.confidence_score,
            "estimated_impact_usd": self.estimated_impact_usd,
            "impact_timeframe_days": self.impact_timeframe_days,
            "evidence_ids": self.evidence_ids,
            "status": self.status,
            "value_path_category": self.value_path_category,
            "entity_type": "ValueHypothesis",
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        })


# ---------------------------------------------------------------------------
# Ranking weights
# ---------------------------------------------------------------------------

RANKING_WEIGHTS: dict[str, dict[str, float]] = {
    RankingStrategy.IMPACT: {"impact": 0.7, "confidence": 0.2, "evidence": 0.1},
    RankingStrategy.CONFIDENCE: {"impact": 0.2, "confidence": 0.7, "evidence": 0.1},
    RankingStrategy.BALANCED: {"impact": 0.4, "confidence": 0.35, "evidence": 0.25},
    RankingStrategy.EVIDENCE: {"impact": 0.2, "confidence": 0.2, "evidence": 0.6},
    RankingStrategy.RECENCY: {"impact": 0.0, "confidence": 0.0, "evidence": 0.0},
}


# ---------------------------------------------------------------------------
# Value Hypothesis Engine
# ---------------------------------------------------------------------------


class ValueHypothesisEngine:
    """Generates and manages value hypotheses for accounts.

    The engine queries the Neo4j knowledge graph to find signal→capability→product
    paths, enriches them with evidence and impact estimates, and stores the
    resulting hypotheses for downstream consumption (business case generation,
    sales enablement, etc.).
    """

    def __init__(self, driver: Any, db: Any | None = None):
        """Initialize the engine.

        Args:
            driver: Neo4j async driver for knowledge graph queries.
            db: Optional SQLAlchemy async session for L4 relational data.
        """
        self._driver = driver
        self._db = db

    # ------------------------------------------------------------------
    # Hypothesis Generation
    # ------------------------------------------------------------------

    async def generate_hypotheses_from_context(
        self,
        context: Any, # EnrichedAccountContext
    ) -> list[ValueHypothesis]:
        """Generate value hypotheses directly from an EnrichedAccountContext (Cargo Phase 3).
        
        Maps firmographics and signals directly to ROI drivers without requiring pre-existing L3 PainSignals.
        """
        tenant_id = str(context.tenant_id)
        account_id = str(context.account_id) if context.account_id else "unknown_account"
        
        hypotheses: list[ValueHypothesis] = []
        
        # Mapping rules for Firmographics -> Drivers
        emp_count = context.company.employee_count or 0
        if emp_count > 1000:
            hypotheses.append(ValueHypothesis(
                tenant_id=tenant_id,
                account_id=account_id,
                signal_id="cargo-firmographic-size",
                signal_name="Enterprise Workforce Scale",
                product_id="prod_automation",
                product_name="Automation Suite",
                capability_id="cap_labor_efficiency",
                capability_name="Workforce Automation",
                hypothesis_text=f"With {emp_count} employees, this account can drive massive Labor Productivity and Cost Reduction through process automation.",
                confidence_score=0.85,
                estimated_impact_usd=emp_count * 1250.0,  # rough impact heuristic
                status=HypothesisStatus.DRAFT,
                value_path_category="Labor Productivity"
            ))

        # Mapping rules for tech stack
        tech_stack = context.company.technologies or []
        tech_lower = [t.lower() for t in tech_stack]
        if any("salesforce" in t or "hubspot" in t or "crm" in t for t in tech_lower):
            hypotheses.append(ValueHypothesis(
                tenant_id=tenant_id,
                account_id=account_id,
                signal_id="cargo-tech-crm",
                signal_name="Large CRM Footprint",
                product_id="prod_sales_intel",
                product_name="Sales Intelligence",
                capability_id="cap_sales_efficiency",
                capability_name="Revenue Intelligence",
                hypothesis_text="Detected a CRM in the tech stack. There is high potential to improve Sales Efficiency and Win Rates by integrating directly.",
                confidence_score=0.9,
                estimated_impact_usd=500000.0,
                status=HypothesisStatus.DRAFT,
                value_path_category="Revenue Growth"
            ))
            
        # Mapping rules for Signals
        for signal in context.signals:
            if signal.signal_type == "funding":
                amount = signal.metadata.get("amount", 0)
                hypotheses.append(ValueHypothesis(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    signal_id=f"cargo-sig-{signal.signal_type}",
                    signal_name=signal.headline,
                    product_id="prod_expansion",
                    product_name="Expansion Suite",
                    capability_id="cap_growth",
                    capability_name="Growth Orchestration",
                    hypothesis_text=f"Recent funding round detected. They are likely in growth mode and need scalable systems to support Expansion.",
                    confidence_score=0.8,
                    estimated_impact_usd=float(amount) * 0.05 if amount else 200000.0,
                    status=HypothesisStatus.DRAFT,
                    value_path_category="Expansion"
                ))
            elif signal.signal_type == "leadership_change":
                hypotheses.append(ValueHypothesis(
                    tenant_id=tenant_id,
                    account_id=account_id,
                    signal_id=f"cargo-sig-{signal.signal_type}",
                    signal_name=signal.headline,
                    product_id="prod_transformation",
                    product_name="Transformation Suite",
                    capability_id="cap_operational_efficiency",
                    capability_name="Process Excellence",
                    hypothesis_text=f"New leadership detected. Executive transitions are major catalysts for buying new operational platforms.",
                    confidence_score=0.75,
                    estimated_impact_usd=300000.0,
                    status=HypothesisStatus.DRAFT,
                    value_path_category="Operational Efficiency"
                ))

        # Store these newly generated hypotheses in Neo4j
        stored = []
        for h in hypotheses:
            stored_h = await self._store_hypothesis(h)
            stored.append(stored_h)

        logger.info(
            "cargo_hypotheses_generated",
            tenant_id=tenant_id,
            account_id=account_id,
            count=len(stored)
        )
        return stored

    async def generate_hypotheses(
        self,
        tenant_id: str,
        account_id: str,
        *,
        min_confidence: float = 0.3,
        max_hypotheses: int = 20,
        include_evidence: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate value hypotheses for an account.

        Traverses the knowledge graph to find:
          PainSignal (account) → INDICATES_NEED_FOR → Capability ← ENABLES_CAPABILITY ← Product

        For each path, creates a hypothesis with confidence scoring and
        optionally attaches supporting evidence.

        Returns:
            List of hypothesis dicts, ranked by balanced score.
        """
        # Step 1: Find signal→capability→product paths for this account
        query = """
        MATCH (ps:PainSignal {tenant_id: $tenant_id, account_id: $account_id})
              -[:INDICATES_NEED_FOR]->(c:Capability)
              <-[ec:ENABLES_CAPABILITY]-(p:Product {tenant_id: $tenant_id})
        WHERE ps.confidence_score >= $min_confidence
        WITH ps, c, p, ec,
             ps.confidence_score * COALESCE(ec.strength, 1.0) AS match_score
        RETURN ps {.id, .name, .confidence_score, .industry, .impact_value} AS signal,
               c {.id, .name} AS capability,
               p {.id, .name, .category} AS product,
               match_score
        ORDER BY match_score DESC
        LIMIT $max_hypotheses
        """
        hypotheses = []
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "account_id": account_id,
                "min_confidence": min_confidence,
                "max_hypotheses": max_hypotheses,
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.generate_for_account",
        )

        for record in records:
            signal = record["signal"]
            capability = record["capability"]
            product = record["product"]
            match_score = record["match_score"]

            # Build hypothesis text
            hypothesis_text = (
                f"By deploying {product['name']}'s {capability['name']} capability, "
                f"this account can address the '{signal['name']}' pain point"
            )

            # Estimate impact from signal data
            impact_value = float(signal.get("impact_value") or 0)

            hypothesis = ValueHypothesis(
                tenant_id=tenant_id,
                account_id=account_id,
                signal_id=signal["id"],
                signal_name=signal["name"],
                product_id=product["id"],
                product_name=product["name"],
                capability_id=capability["id"],
                capability_name=capability["name"],
                hypothesis_text=hypothesis_text,
                confidence_score=min(match_score, 1.0),
                estimated_impact_usd=impact_value,
            )

            # Step 2: Find supporting evidence
            evidence_ids = []
            if include_evidence:
                evidence_ids = await self._find_supporting_evidence(
                    tenant_id, signal, product
                )
                hypothesis.evidence_ids = evidence_ids

            hypotheses.append(hypothesis)

        # Step 3: Store hypotheses in Neo4j
        stored = []
        for h in hypotheses:
            stored_h = await self._store_hypothesis(h)
            stored.append(stored_h)

        # Step 4: Rank by balanced strategy
        ranked = self.rank_hypotheses(stored, RankingStrategy.BALANCED)

        logger.info(
            "hypotheses_generated",
            tenant_id=tenant_id,
            account_id=account_id,
            count=len(ranked),
        )
        return ranked

    async def _find_supporting_evidence(
        self,
        tenant_id: str,
        signal: dict[str, Any],
        product: dict[str, Any],
    ) -> list[str]:
        """Find case studies that support a signal→product hypothesis."""
        industry = signal.get("industry", "")
        query = """
        MATCH (e:Evidence {tenant_id: $tenant_id, evidence_type: 'case_study'})
        WHERE (e.industry = $industry OR $industry = '')
          AND ($product_name IN e.products_used OR size(e.products_used) = 0)
        RETURN e.id AS evidence_id
        LIMIT 5
        """
        evidence_ids = []
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "industry": industry,
                "product_name": product.get("name", ""),
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.find_supporting_evidence",
        )
        evidence_ids = [r["evidence_id"] for r in records]

        return evidence_ids

    async def _store_hypothesis(self, hypothesis: ValueHypothesis) -> dict[str, Any]:
        """Store a hypothesis as a Neo4j node with relationships."""
        props = hypothesis.to_node_properties()
        query = """
        MERGE (vh:ValueHypothesis {id: $id})
        SET vh += $props
        WITH vh
        // Link to account
        OPTIONAL MATCH (a:Account {id: $account_id, tenant_id: $tenant_id})
        FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
            MERGE (a)-[:HAS_HYPOTHESIS]->(vh)
        )
        WITH vh
        // Link to signal
        OPTIONAL MATCH (ps:PainSignal {id: $signal_id, tenant_id: $tenant_id})
        FOREACH (_ IN CASE WHEN ps IS NOT NULL THEN [1] ELSE [] END |
            MERGE (vh)-[:ADDRESSES_SIGNAL]->(ps)
        )
        WITH vh
        // Link to product
        OPTIONAL MATCH (p:Product {id: $product_id, tenant_id: $tenant_id})
        FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
            MERGE (vh)-[:RECOMMENDS_PRODUCT]->(p)
        )
        RETURN vh {.*} AS hypothesis
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "id": props["id"],
                "props": props,
                "account_id": props["account_id"],
                "tenant_id": props["tenant_id"],
                "signal_id": props["signal_id"],
                "product_id": props["product_id"],
            },
            tenant_id=props["tenant_id"],
            operation="value_hypothesis_engine.store_hypothesis",
        )
        record = records[0] if records else None
        if record:
            return record["hypothesis"]
        return props

    async def promote_signal(
        self,
        tenant_id: str,
        account_id: str,
        signal_id: str,
        *,
        value_path_category: str | None = None,
        product_id: str | None = None,
        product_name: str | None = None,
        capability_id: str | None = None,
        capability_name: str | None = None,
    ) -> dict[str, Any]:
        """Promote a single pain signal to a value hypothesis (opportunity).

        Looks up the signal in the knowledge graph and creates a ValueHypothesis
        node linked to the signal and account. This is the canonical hinge
        between Signal Discovery and Value Path Classification.

        Args:
            tenant_id: Tenant scope.
            account_id: Account the signal belongs to.
            signal_id: ID of the pain signal to promote.
            value_path_category: Optional initial value path (revenue_uplift,
                cost_savings, risk_reduction, blended).
            product_id: Optional product to associate.
            product_name: Optional product name.
            capability_id: Optional capability to associate.
            capability_name: Optional capability name.

        Returns:
            The created hypothesis dict.
        """
        # Fetch signal details from Neo4j
        signal_query = """
        MATCH (ps:PainSignal {id: $signal_id, tenant_id: $tenant_id, account_id: $account_id})
        RETURN ps {.id, .name, .category, .confidence_score, .impact_value, .description} AS signal
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=signal_query,
            params={
                "signal_id": signal_id,
                "tenant_id": tenant_id,
                "account_id": account_id,
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.promote_signal",
        )
        record = records[0] if records else None
        if not record or not record["signal"]:
            raise ValueError(f"Signal {signal_id} not found for account {account_id}")

        signal = record["signal"]

        # Use signal category as fallback capability if none provided
        cap_id = capability_id or signal["id"]
        cap_name = capability_name or signal.get("category", "Unknown")
        prod_id = product_id or ""
        prod_name = product_name or "Unknown Product"

        hypothesis_text = (
            f"Address '{signal['name']}' through {cap_name} "
            f"to unlock {value_path_category or 'value'} impact."
        )

        hypothesis = ValueHypothesis(
            tenant_id=tenant_id,
            account_id=account_id,
            signal_id=signal["id"],
            signal_name=signal["name"],
            product_id=prod_id,
            product_name=prod_name,
            capability_id=cap_id,
            capability_name=cap_name,
            hypothesis_text=hypothesis_text,
            confidence_score=float(signal.get("confidence_score") or 0.5),
            estimated_impact_usd=float(signal.get("impact_value") or 0),
            value_path_category=value_path_category,
            status=HypothesisStatus.DRAFT,
        )

        stored = await self._store_hypothesis(hypothesis)
        logger.info(
            "signal_promoted",
            signal_id=signal_id,
            account_id=account_id,
            hypothesis_id=hypothesis.id,
            value_path_category=value_path_category,
        )
        return stored

    # ------------------------------------------------------------------
    # Hypothesis Ranking
    # ------------------------------------------------------------------

    def rank_hypotheses(
        self,
        hypotheses: list[dict[str, Any]],
        strategy: RankingStrategy | str = RankingStrategy.BALANCED,
    ) -> list[dict[str, Any]]:
        """Rank hypotheses using the specified strategy.

        Each hypothesis gets a composite_score based on weighted factors:
          - impact: normalized estimated_impact_usd
          - confidence: confidence_score (already 0-1)
          - evidence: normalized evidence count

        Returns:
            Sorted list with composite_score added to each hypothesis.
        """
        if isinstance(strategy, str):
            strategy = RankingStrategy(strategy)

        if strategy == RankingStrategy.RECENCY:
            return sorted(
                hypotheses,
                key=lambda h: h.get("created_at", ""),
                reverse=True,
            )

        weights = RANKING_WEIGHTS[strategy]

        # Normalize impact values
        max_impact = max(
            (abs(float(h.get("estimated_impact_usd", 0))) for h in hypotheses),
            default=1.0,
        ) or 1.0

        max_evidence = max(
            (len(h.get("evidence_ids", [])) for h in hypotheses),
            default=1,
        ) or 1

        for h in hypotheses:
            impact_norm = abs(float(h.get("estimated_impact_usd", 0))) / max_impact
            confidence = float(h.get("confidence_score", 0))
            evidence_norm = len(h.get("evidence_ids", [])) / max_evidence

            h["composite_score"] = round(
                weights["impact"] * impact_norm
                + weights["confidence"] * confidence
                + weights["evidence"] * evidence_norm,
                4,
            )

        return sorted(hypotheses, key=lambda h: h["composite_score"], reverse=True)

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def get_hypothesis(
        self, tenant_id: str, hypothesis_id: str
    ) -> dict[str, Any] | None:
        """Get a single hypothesis by ID."""
        query = """
        MATCH (vh:ValueHypothesis {id: $hypothesis_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (vh)-[:ADDRESSES_SIGNAL]->(ps:PainSignal)
        OPTIONAL MATCH (vh)-[:RECOMMENDS_PRODUCT]->(p:Product)
        OPTIONAL MATCH (e:Evidence) WHERE e.id IN vh.evidence_ids
        RETURN vh {.*} AS hypothesis,
               ps {.id, .name} AS signal,
               p {.id, .name} AS product,
               collect(DISTINCT e {.id, .title, .industry}) AS evidence
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "hypothesis_id": hypothesis_id,
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.get_hypothesis",
        )
        record = records[0] if records else None
        if not record or not record["hypothesis"]:
            return None
        return ValueHypothesisEngine_get_hypothesisResult.model_validate({
            **record["hypothesis"],
            "signal_detail": record["signal"],
            "product_detail": record["product"],
            "evidence_detail": record["evidence"],
        })


    async def get_account_hypotheses(
        self,
        tenant_id: str,
        account_id: str,
        *,
        status: str | None = None,
        value_path_category: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get all hypotheses for an account with optional status and value_path filters."""
        where_clauses = [
            "vh.tenant_id = $tenant_id",
            "vh.account_id = $account_id",
        ]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "account_id": account_id,
            "skip": skip,
            "limit": limit,
        }
        if status:
            where_clauses.append("vh.status = $status")
            params["status"] = status
        if value_path_category:
            where_clauses.append("vh.value_path_category = $value_path_category")
            params["value_path_category"] = value_path_category

        where = " AND ".join(where_clauses)

        # Controlled clause concatenation: only hard-coded parameterised
        # fragments are joined; user input is bound via $params below.
        count_query = (
            "MATCH (vh:ValueHypothesis) WHERE " + where + " RETURN count(vh) AS total"
        )
        list_query = (
            "MATCH (vh:ValueHypothesis) WHERE " + where + "\n"
            "RETURN vh {.*} AS hypothesis\n"
            "ORDER BY vh.confidence_score DESC\n"
            "SKIP $skip LIMIT $limit"
        )

        count_records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=count_query,
            params=params,
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.get_account_hypotheses.count",
        )
        count_record = count_records[0] if count_records else None
        total = count_record["total"] if count_record else 0

        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=list_query,
            params=params,
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.get_account_hypotheses.list",
        )

        return ValueHypothesisEngine_get_account_hypothesesResult.model_validate({
            "hypotheses": [r["hypothesis"] for r in records],
            "total": total,
            "skip": skip,
            "limit": limit,
        })


    async def validate_hypothesis(
        self,
        tenant_id: str,
        hypothesis_id: str,
        *,
        feedback: str,
        new_status: str | None = None,
        confidence_adjustment: float = 0.0,
    ) -> dict[str, Any] | None:
        """Update a hypothesis based on user feedback.

        Args:
            feedback: Free-text feedback from the user.
            new_status: Optional status transition (validated/rejected).
            confidence_adjustment: Additive adjustment to confidence (-1 to 1).

        Returns:
            Updated hypothesis dict, or None if not found.
        """
        now = datetime.now(UTC).isoformat()

        # Build SET clauses
        set_parts = [
            "vh.updated_at = $now",
            "vh.last_feedback = $feedback",
        ]
        params: dict[str, Any] = {
            "hypothesis_id": hypothesis_id,
            "tenant_id": tenant_id,
            "now": now,
            "feedback": feedback,
        }

        if new_status:
            set_parts.append("vh.status = $new_status")
            params["new_status"] = new_status

        if confidence_adjustment != 0.0:
            # Clamp confidence between 0 and 1
            set_parts.append(
                "vh.confidence_score = "
                "CASE WHEN vh.confidence_score + $adj > 1.0 THEN 1.0 "
                "     WHEN vh.confidence_score + $adj < 0.0 THEN 0.0 "
                "     ELSE vh.confidence_score + $adj END"
            )
            params["adj"] = confidence_adjustment

        set_clause = ", ".join(set_parts)

        query = f"""
        MATCH (vh:ValueHypothesis {{id: $hypothesis_id, tenant_id: $tenant_id}})
        SET {set_clause}
        RETURN vh {{.*}} AS hypothesis
        """

        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params=params,
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.validate_hypothesis",
        )
        record = records[0] if records else None
        if not record:
            return None

        logger.info(
            "hypothesis_validated",
            hypothesis_id=hypothesis_id,
            new_status=new_status,
            confidence_adjustment=confidence_adjustment,
        )
        return record["hypothesis"]

    async def promote_validated_hypothesis(
        self,
        tenant_id: str,
        hypothesis_id: str,
    ) -> dict[str, Any]:
        """Create idempotent driver-tree artifacts for a validated hypothesis."""
        driver_id = f"driver_{hypothesis_id}"
        lever_id = f"lever_{hypothesis_id}"
        linkage_id = f"vh:{hypothesis_id}:driver:{driver_id}"
        now = datetime.now(UTC).isoformat()

        query = """
        MATCH (vh:ValueHypothesis {id: $hypothesis_id, tenant_id: $tenant_id})
        OPTIONAL MATCH (vh)-[:ADDRESSES_SIGNAL]->(ps:PainSignal)
        OPTIONAL MATCH (vh)-[:SUPPORTED_BY]->(e:Evidence)
        WITH vh, ps, collect(DISTINCT e.id) AS evidence_ids
        MERGE (d:ValueDriver {id: $driver_id, tenant_id: $tenant_id})
        ON CREATE SET d.created_at = $now
        SET d.updated_at = $now,
            d.account_id = coalesce(vh.account_id, ps.account_id),
            d.hypothesis_id = vh.id,
            d.signal_id = coalesce(vh.signal_id, ps.id),
            d.name = coalesce(vh.value_path_category, vh.capability_name, ps.category, 'Value driver'),
            d.description = coalesce(vh.hypothesis_text, ps.description, ps.name, 'Validated value hypothesis'),
            d.category = coalesce(vh.value_path_category, 'blended'),
            d.confidence = coalesce(vh.confidence_score, vh.confidence, 0.5),
            d.estimated_impact_usd = coalesce(vh.estimated_impact_usd, ps.impact_value, 0),
            d.evidence_ids = evidence_ids,
            d.source = 'hypothesis_validation',
            d.hypothesis_driver_linkage_id = $linkage_id
        MERGE (l:ValueLever {id: $lever_id, tenant_id: $tenant_id})
        ON CREATE SET l.created_at = $now
        SET l.updated_at = $now,
            l.account_id = d.account_id,
            l.driver_id = d.id,
            l.hypothesis_id = vh.id,
            l.name = d.name,
            l.category = d.category,
            l.base_value = coalesce(d.estimated_impact_usd, 0),
            l.min_value = coalesce(d.estimated_impact_usd, 0) * 0.5,
            l.max_value = coalesce(d.estimated_impact_usd, 0) * 1.5,
            l.annual_impact = coalesce(d.estimated_impact_usd, 0),
            l.unit = 'USD',
            l.confidence = toInteger(round(coalesce(d.confidence, 0.5) * 100))
        MERGE (vh)-[:PROMOTED_TO_DRIVER]->(d)
        MERGE (d)-[:HAS_LEVER]->(l)
        WITH vh, ps, d, l
        FOREACH (_ IN CASE WHEN ps IS NULL THEN [] ELSE [1] END |
          MERGE (d)-[:DERIVED_FROM_SIGNAL]->(ps)
        )
        RETURN d {.*} AS driver, l {.*} AS lever, $linkage_id AS linkage_id
        """

        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "tenant_id": tenant_id,
                "hypothesis_id": hypothesis_id,
                "driver_id": driver_id,
                "lever_id": lever_id,
                "linkage_id": linkage_id,
                "now": now,
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.promote_validated_hypothesis",
        )
        record = records[0] if records else None

        if not record:
            return {"drivers": [], "levers": [], "created": False}

        return {
            "drivers": [record["driver"]],
            "levers": [record["lever"]],
            "linkages": [{
                "hypothesis_id": hypothesis_id,
                "driver_id": record["driver"]["id"],
                "linkage_id": record["linkage_id"],
            }],
            "created": True,
        }

    async def orchestrate_post_validation(
        self,
        tenant_id: str,
        hypothesis_id: str,
        *,
        new_status: str | None = None,
    ) -> dict[str, Any] | None:
        """Run post-validation orchestration steps (driver generation workflow)."""
        if new_status != HypothesisStatus.VALIDATED.value:
            return None
        return await self.promote_validated_hypothesis(tenant_id, hypothesis_id)

    async def convert_hypothesis_to_tree(
        self,
        tenant_id: str,
        hypothesis_id: str,
    ) -> dict[str, Any] | None:
        """Convert a validated hypothesis into downstream tree/model linkage."""
        converted = await self.validate_hypothesis(
            tenant_id,
            hypothesis_id,
            feedback="Converted hypothesis to tree",
            new_status=HypothesisStatus.CONVERTED.value,
            confidence_adjustment=0.0,
        )
        if not converted:
            return None

        return ValueHypothesisEngine_convert_hypothesis_to_treeResult.model_validate({
            "hypothesis_id": converted["id"],
            "account_id": converted["account_id"],
            "tenant_id": converted["tenant_id"],
            "evidence_ids": converted.get("evidence_ids", []),
            "value_model_id": converted.get("value_model_id"),
            "tree_id": converted.get("tree_id"),
            "status": converted.get("status", HypothesisStatus.CONVERTED.value),
        })

    async def delete_hypothesis(
        self, tenant_id: str, hypothesis_id: str
    ) -> bool:
        """Delete a hypothesis and its relationships."""
        query = """
        MATCH (vh:ValueHypothesis {id: $hypothesis_id, tenant_id: $tenant_id})
        DETACH DELETE vh
        RETURN count(vh) AS deleted
        """
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params={
                "hypothesis_id": hypothesis_id,
                "tenant_id": tenant_id,
            },
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.delete_hypothesis",
        )
        record = records[0] if records else None
        return record["deleted"] > 0 if record else False

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    async def get_hypothesis_summary(
        self, tenant_id: str, account_id: str | None = None
    ) -> dict[str, Any]:
        """Get aggregate statistics about hypotheses."""
        where_parts = ["vh.tenant_id = $tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if account_id:
            where_parts.append("vh.account_id = $account_id")
            params["account_id"] = account_id

        where = " AND ".join(where_parts)

        # Controlled clause concatenation using parameterised fragments only.
        query = (
            "MATCH (vh:ValueHypothesis) WHERE " + where + "\n"
            "RETURN count(vh) AS total,\n"
            "       sum(CASE WHEN vh.status = 'draft' THEN 1 ELSE 0 END) AS draft_count,\n"
            "       sum(CASE WHEN vh.status = 'validated' THEN 1 ELSE 0 END) AS validated_count,\n"
            "       sum(CASE WHEN vh.status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count,\n"
            "       sum(CASE WHEN vh.status = 'converted' THEN 1 ELSE 0 END) AS converted_count,\n"
            "       avg(vh.confidence_score) AS avg_confidence,\n"
            "       sum(vh.estimated_impact_usd) AS total_estimated_impact,\n"
            "       avg(vh.estimated_impact_usd) AS avg_estimated_impact,\n"
            "       count(DISTINCT vh.product_id) AS unique_products,\n"
            "       count(DISTINCT vh.account_id) AS unique_accounts"
        )
        records = await fetch_tenant_validated_records(
            driver=self._driver,
            query=query,
            params=params,
            tenant_id=tenant_id,
            operation="value_hypothesis_engine.get_hypothesis_summary",
        )
        record = records[0] if records else None
        if not record:
            return ValueHypothesisEngine_get_hypothesis_summaryResult.model_validate({"total": 0})

        return ValueHypothesisEngine_get_hypothesis_summaryResult.model_validate({
            "total": record["total"],
            "by_status": {
                "draft": record["draft_count"],
                "validated": record["validated_count"],
                "rejected": record["rejected_count"],
                "converted": record["converted_count"],
            },
            "avg_confidence": round(record["avg_confidence"] or 0, 3),
            "total_estimated_impact": round(record["total_estimated_impact"] or 0, 2),
            "avg_estimated_impact": round(record["avg_estimated_impact"] or 0, 2),
            "unique_products": record["unique_products"],
            "unique_accounts": record["unique_accounts"],
        })
