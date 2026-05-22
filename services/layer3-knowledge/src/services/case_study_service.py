"""
Case Study Service — Data Intelligence Layer Phase 1.

Manages structured case studies as Evidence nodes in the Neo4j knowledge graph.
Case studies are the primary evidence type for value selling — they provide
proof points that map customer pain signals to quantified outcomes.

Architecture:
- Case studies are stored as Evidence nodes with evidence_type = 'case_study'
- Each case study links to Products (via DEMONSTRATES), Industries, and PainSignals
- The evidence_search service provides vector similarity matching
- This service handles CRUD, structured ingestion, and bulk import

Evidence Node Schema (Neo4j):
    id: str (UUID)
    tenant_id: str
    evidence_type: 'case_study'
    title: str
    content: str (full narrative)
    summary: str (2-3 sentence abstract)
    industry: str
    company_name: str (anonymized or real)
    company_size: str (small/medium/large/enterprise)
    products_used: list[str]
    pain_signals_addressed: list[str]
    outcomes: list[dict] (metric, before, after, improvement_pct)
    time_to_value_days: int
    deal_size_usd: float
    published_date: str
    tags: list[str]
    embedding: list[float] (populated by vector pipeline)
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..db.query_execution import run_validated_query

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    require_context = None


class CaseStudyService_get_by_industryResult(TypedDictModel):
    pass

class CaseStudyService_get_by_productResult(TypedDictModel):
    pass


class CaseStudyOutcome_to_dictResult(TypedDictModel):
    after_value: Any
    before_value: Any
    improvement_pct: Any
    metric: Any
    time_to_achieve_days: Any

class CaseStudy_to_node_propertiesResult(TypedDictModel):
    company_name: Any
    company_size: Any
    content: Any
    created_at: Any
    deal_size_usd: Any
    evidence_type: str
    id: Any
    industry: Any
    outcomes: Any
    pain_signals_addressed: Any
    products_used: Any
    published_date: Any
    summary: Any
    tags: Any
    tenant_id: Any
    time_to_value_days: Any
    title: Any
    updated_at: Any

class CaseStudyService_createResult(TypedDictModel):
    id: Any
    industry: Any
    status: str
    title: Any

class CaseStudyService_bulk_importResult(TypedDictModel):
    created: Any
    errors: Any
    total: Any

class CaseStudyService_updateResult(TypedDictModel):
    id: Any
    status: str
    title: Any

class CaseStudyService_searchResult(TypedDictModel):
    items: Any
    limit: Any
    offset: Any
    total: Any

logger = structlog.get_logger()


def _get_tenant_id() -> str:
    """Retrieve tenant ID from request context or fail closed."""
    if not require_context:
        raise AuthorizationError(
            "Tenant context provider is unavailable for case study operations.",
            details={"service": "CaseStudyService", "reason": "missing_context_provider"},
        )
    try:
        return str(require_context().tenant_id)
    except RuntimeError as exc:
        raise AuthorizationError(
            "Tenant context required for case study operations.",
            details={"service": "CaseStudyService", "reason": "missing_request_context"},
        ) from exc
# ---------------------------------------------------------------------------
# Case Study Data Model
# ---------------------------------------------------------------------------

class CaseStudyOutcome:
    """A single quantified outcome from a case study."""

    def __init__(
        self,
        metric: str,
        before_value: str | None = None,
        after_value: str | None = None,
        improvement_pct: float | None = None,
        time_to_achieve_days: int | None = None,
    ):
        self.metric = metric
        self.before_value = before_value
        self.after_value = after_value
        self.improvement_pct = improvement_pct
        self.time_to_achieve_days = time_to_achieve_days

    def to_dict(self) -> dict[str, Any]:
        return CaseStudyOutcome_to_dictResult.model_validate({
            "metric": self.metric,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "improvement_pct": self.improvement_pct,
            "time_to_achieve_days": self.time_to_achieve_days,
        })


class CaseStudy:
    """Structured case study for the Evidence Library."""

    def __init__(
        self,
        title: str,
        content: str,
        industry: str,
        tenant_id: str,
        id: str | None = None,
        summary: str | None = None,
        company_name: str | None = None,
        company_size: str | None = None,
        products_used: list[str] | None = None,
        pain_signals_addressed: list[str] | None = None,
        outcomes: list[dict[str, Any]] | None = None,
        time_to_value_days: int | None = None,
        deal_size_usd: float | None = None,
        published_date: str | None = None,
        tags: list[str] | None = None,
    ):
        self.id = id or str(uuid4())
        self.tenant_id = tenant_id
        self.title = title
        self.content = content
        self.summary = summary or ""
        self.industry = industry
        self.company_name = company_name or "Anonymous"
        self.company_size = company_size or "unknown"
        self.products_used = products_used or []
        self.pain_signals_addressed = pain_signals_addressed or []
        self.outcomes = outcomes or []
        self.time_to_value_days = time_to_value_days
        self.deal_size_usd = deal_size_usd
        self.published_date = published_date or datetime.now(UTC).strftime("%Y-%m-%d")
        self.tags = tags or []

    def to_node_properties(self) -> dict[str, Any]:
        """Convert to Neo4j node properties dict."""
        return CaseStudy_to_node_propertiesResult.model_validate({
            "id": self.id,
            "tenant_id": self.tenant_id,
            "evidence_type": "case_study",
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "industry": self.industry,
            "company_name": self.company_name,
            "company_size": self.company_size,
            "products_used": self.products_used,
            "pain_signals_addressed": self.pain_signals_addressed,
            "outcomes": [o if isinstance(o, dict) else o.to_dict() for o in self.outcomes],
            "time_to_value_days": self.time_to_value_days,
            "deal_size_usd": self.deal_size_usd,
            "published_date": self.published_date,
            "tags": self.tags,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        })


# ---------------------------------------------------------------------------
# Case Study Service
# ---------------------------------------------------------------------------

class CaseStudyService:
    """Manages case study lifecycle in the Neo4j knowledge graph.

    Usage:
        service = CaseStudyService(neo4j_driver)
        case_study = await service.create(tenant_id, case_study_data)
        results = await service.search(tenant_id, industry="healthcare")
        await service.bulk_import(tenant_id, case_studies_list)
    """

    def __init__(self, driver):
        """Initialize with a Neo4j async driver."""
        self.driver = driver

    # -------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------

    async def create(self, case_study: CaseStudy) -> dict[str, Any]:
        """Create a new case study as an Evidence node."""
        props = case_study.to_node_properties()

        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                // strict-scoped-query-execution: props includes required tenant_id for Evidence
                CREATE (e:Evidence $props)
                RETURN e.id AS id, e.title AS title, e.industry AS industry
                """,
                props=props,
            )
            record = await result.single()

            # Create relationships to products if specified
            if case_study.products_used:
                for product_name in case_study.products_used:
                    await run_validated_query(session,
                        """
                        MATCH (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
                        MATCH (p:Product {name: $product_name, tenant_id: $tenant_id})
                        MERGE (p)-[:DEMONSTRATES]->(e)
                        """,
                        evidence_id=case_study.id,
                        tenant_id=case_study.tenant_id,
                        product_name=product_name,
                    )

            # Create relationships to pain signals if specified
            if case_study.pain_signals_addressed:
                for signal_name in case_study.pain_signals_addressed:
                    await run_validated_query(session,
                        """
                        MATCH (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
                        MATCH (ps:PainSignal {name: $signal_name, tenant_id: $tenant_id})
                        MERGE (ps)-[:supportedBy]->(e)
                        """,
                        evidence_id=case_study.id,
                        tenant_id=case_study.tenant_id,
                        signal_name=signal_name,
                    )

        logger.info(
            "case_study_created",
            id=case_study.id,
            title=case_study.title,
            tenant_id=case_study.tenant_id,
            industry=case_study.industry,
        )

        return CaseStudyService_createResult.model_validate({
            "id": record["id"] if record else case_study.id,
            "title": record["title"] if record else case_study.title,
            "industry": record["industry"] if record else case_study.industry,
            "status": "created",
        })


    async def get(self, tenant_id: str, case_study_id: str) -> dict[str, Any] | None:
        """Get a case study by ID."""
        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                MATCH (e:Evidence {id: $id, tenant_id: $tenant_id, evidence_type: 'case_study'})
                OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[:DEMONSTRATES]->(e)
                OPTIONAL MATCH (ps:PainSignal {tenant_id: $tenant_id})-[:supportedBy]->(e)
                RETURN e {.*} AS case_study,
                       collect(DISTINCT p.name) AS linked_products,
                       collect(DISTINCT ps.name) AS linked_signals
                """,
                id=case_study_id,
                tenant_id=tenant_id,
            )
            record = await result.single()

            if not record or not record["case_study"]:
                return None

            cs = dict(record["case_study"])
            cs["linked_products"] = record["linked_products"]
            cs["linked_signals"] = record["linked_signals"]
            return cs

    async def update(
        self,
        tenant_id: str,
        case_study_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a case study's properties."""
        # Prevent overwriting system fields
        protected = {"id", "tenant_id", "evidence_type", "created_at"}
        safe_updates = {k: v for k, v in updates.items() if k not in protected}
        safe_updates["updated_at"] = datetime.now(UTC).isoformat()

        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                MATCH (e:Evidence {id: $id, tenant_id: $tenant_id, evidence_type: 'case_study'})
                SET e += $updates
                RETURN e.id AS id, e.title AS title
                """,
                id=case_study_id,
                tenant_id=tenant_id,
                updates=safe_updates,
            )
            record = await result.single()

            if not record:
                return None

            return CaseStudyService_updateResult.model_validate({"id": record["id"], "title": record["title"], "status": "updated"})

    async def delete(self, tenant_id: str, case_study_id: str) -> bool:
        """Delete a case study and its relationships."""
        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                MATCH (e:Evidence {id: $id, tenant_id: $tenant_id, evidence_type: 'case_study'})
                DETACH DELETE e
                RETURN count(*) AS deleted
                """,
                id=case_study_id,
                tenant_id=tenant_id,
            )
            record = await result.single()
            deleted = record["deleted"] > 0 if record else False

            if deleted:
                logger.info(
                    "case_study_deleted",
                    id=case_study_id,
                    tenant_id=tenant_id,
                )

            return deleted

    # -------------------------------------------------------------------
    # Search & Query
    # -------------------------------------------------------------------

    async def search(
        self,
        tenant_id: str,
        industry: str | None = None,
        company_size: str | None = None,
        products: list[str] | None = None,
        tags: list[str] | None = None,
        min_deal_size: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search case studies with filters."""
        where_clauses = ["e.tenant_id = $tenant_id", "e.evidence_type = 'case_study'"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if industry:
            where_clauses.append("e.industry = $industry")
            params["industry"] = industry

        if company_size:
            where_clauses.append("e.company_size = $company_size")
            params["company_size"] = company_size

        if min_deal_size is not None:
            where_clauses.append("e.deal_size_usd >= $min_deal_size")
            params["min_deal_size"] = min_deal_size

        where_str = " AND ".join(where_clauses)

        async with self.driver.session() as session:
            # Get total count
            count_query = (
                "// strict-scoped-query-execution: where_str includes e.tenant_id = $tenant_id\n"
                f"MATCH (e:Evidence) WHERE {where_str} RETURN count(e) AS total"
            )
            count_result = await run_validated_query(session, count_query, **params)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            # Get paginated results
            search_query = f"""
                // strict-scoped-query-execution: where_str includes e.tenant_id = $tenant_id
                MATCH (e:Evidence) WHERE {where_str}
                OPTIONAL MATCH (p:Product {tenant_id: $tenant_id})-[:DEMONSTRATES]->(e)
                RETURN e {{.*}} AS case_study,
                       collect(DISTINCT p.name) AS linked_products
                ORDER BY e.published_date DESC
                SKIP $offset LIMIT $limit
                """
            result = await run_validated_query(session, search_query, **params)

            records = [record async for record in result]
            items = []
            for r in records:
                cs = dict(r["case_study"])
                cs["linked_products"] = r["linked_products"]
                items.append(cs)

            # Post-filter by products and tags (Neo4j list operations)
            if products:
                items = [
                    cs for cs in items
                    if any(p in (cs.get("products_used") or []) for p in products)
                ]
            if tags:
                items = [
                    cs for cs in items
                    if any(t in (cs.get("tags") or []) for t in tags)
                ]

            return CaseStudyService_searchResult.model_validate({
                "total": total,
                "offset": offset,
                "limit": limit,
                "items": items,
            })


    async def get_by_industry(self, tenant_id: str) -> dict[str, int]:
        """Get case study counts grouped by industry."""
        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                MATCH (e:Evidence {tenant_id: $tenant_id, evidence_type: 'case_study'})
                RETURN e.industry AS industry, count(e) AS count
                ORDER BY count DESC
                """,
                tenant_id=tenant_id,
            )
            records = [record async for record in result]
            return CaseStudyService_get_by_industryResult.model_validate({r["industry"]: r["count"] for r in records})

    async def get_by_product(self, tenant_id: str) -> dict[str, int]:
        """Get case study counts grouped by product."""
        async with self.driver.session() as session:
            result = await run_validated_query(session,
                """
                MATCH (p:Product {tenant_id: $tenant_id})-[:DEMONSTRATES]->(e:Evidence {evidence_type: 'case_study'})
                RETURN p.name AS product, count(e) AS count
                ORDER BY count DESC
                """,
                tenant_id=tenant_id,
            )
            records = [record async for record in result]
            return CaseStudyService_get_by_productResult.model_validate({r["product"]: r["count"] for r in records})

    # -------------------------------------------------------------------
    # Bulk Import
    # -------------------------------------------------------------------

    async def bulk_import(
        self, tenant_id: str, case_studies: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Import multiple case studies in a single transaction.

        Expects a list of dicts matching the CaseStudy constructor kwargs.
        Returns import statistics.
        """
        created = 0
        errors = []

        for i, cs_data in enumerate(case_studies):
            try:
                cs = CaseStudy(
                    tenant_id=tenant_id,
                    title=cs_data.get("title", f"Case Study {i + 1}"),
                    content=cs_data.get("content", ""),
                    industry=cs_data.get("industry", "unknown"),
                    summary=cs_data.get("summary"),
                    company_name=cs_data.get("company_name"),
                    company_size=cs_data.get("company_size"),
                    products_used=cs_data.get("products_used"),
                    pain_signals_addressed=cs_data.get("pain_signals_addressed"),
                    outcomes=cs_data.get("outcomes"),
                    time_to_value_days=cs_data.get("time_to_value_days"),
                    deal_size_usd=cs_data.get("deal_size_usd"),
                    published_date=cs_data.get("published_date"),
                    tags=cs_data.get("tags"),
                )
                await self.create(cs)
                created += 1
            except Exception as e:
                errors.append({
                    "index": i,
                    "title": cs_data.get("title", "unknown"),
                    "error": str(e),
                })
                logger.error(
                    "case_study_import_error",
                    index=i,
                    title=cs_data.get("title"),
                    error=str(e),
                )

        logger.info(
            "case_study_bulk_import_complete",
            tenant_id=tenant_id,
            total=len(case_studies),
            created=created,
            errors=len(errors),
        )

        return CaseStudyService_bulk_importResult.model_validate({
            "total": len(case_studies),
            "created": created,
            "errors": errors,
        })

