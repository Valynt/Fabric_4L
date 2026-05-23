"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Evidence Library API Routes — Data Intelligence Layer Phase 1.

Provides endpoints for managing the evidence library (case studies,
benchmarks, proof points) in the Neo4j knowledge graph.

Routes:
- POST   /evidence/case-studies              — Create a case study
- GET    /evidence/case-studies               — Search case studies
- GET    /evidence/case-studies/{id}          — Get a case study
- PUT    /evidence/case-studies/{id}          — Update a case study
- DELETE /evidence/case-studies/{id}          — Delete a case study
- POST   /evidence/case-studies/bulk-import   — Bulk import case studies
- GET    /evidence/stats/by-industry          — Case study counts by industry
- GET    /evidence/stats/by-product           — Case study counts by product
- POST   /evidence/search                     — Semantic evidence search
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.security.dil_auth import get_verified_tenant_id

from ...api.dependencies import get_neo4j_driver
from ...db.query_execution import run_validated_query
from ...services.case_study_service import CaseStudy, CaseStudyService
from ...services.embedding_errors import EmbeddingProviderUnavailableError
from ...services.evidence_search import EvidenceSearchService
from ..exceptions import create_service_unavailable_http_exception


class delete_case_studyResult(TypedDictModel):
    id: Any
    status: str

class semantic_searchResult(TypedDictModel):
    query: Any
    results: Any
    total: Any

logger = structlog.get_logger()

router = APIRouter(prefix="/evidence", tags=["evidence"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class OutcomeModel(BaseModel):
    metric: str = Field(..., description="The metric being measured")
    before_value: str | None = Field(None, description="Value before implementation")
    after_value: str | None = Field(None, description="Value after implementation")
    improvement_pct: float | None = Field(None, description="Percentage improvement")
    time_to_achieve_days: int | None = Field(None, description="Days to achieve this outcome")


class CreateCaseStudyRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500, description="Case study title")
    content: str = Field(..., min_length=50, description="Full case study narrative")
    industry: str = Field(..., description="Industry vertical")
    summary: str | None = Field(None, max_length=1000, description="2-3 sentence abstract")
    company_name: str | None = Field(None, description="Customer company name (can be anonymized)")
    company_size: str | None = Field(None, description="small, medium, large, or enterprise")
    products_used: list[str] | None = Field(None, description="Product names used in this case")
    pain_signals_addressed: list[str] | None = Field(None, description="Pain signals this case addresses")
    outcomes: list[OutcomeModel] | None = Field(None, description="Quantified outcomes")
    time_to_value_days: int | None = Field(None, ge=0, description="Days to first value")
    deal_size_usd: float | None = Field(None, ge=0, description="Deal size in USD")
    published_date: str | None = Field(None, description="Publication date (YYYY-MM-DD)")
    tags: list[str] | None = Field(None, description="Searchable tags")


class UpdateCaseStudyRequest(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=500)
    content: str | None = None
    summary: str | None = None
    industry: str | None = None
    company_name: str | None = None
    company_size: str | None = None
    products_used: list[str] | None = None
    pain_signals_addressed: list[str] | None = None
    outcomes: list[OutcomeModel] | None = None
    time_to_value_days: int | None = None
    deal_size_usd: float | None = None
    tags: list[str] | None = None


class BulkImportRequest(BaseModel):
    case_studies: list[CreateCaseStudyRequest] = Field(
        ..., min_length=1, max_length=100, description="List of case studies to import"
    )


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language search query")
    evidence_types: list[str] | None = Field(None, description="Filter by evidence type")
    limit: int = Field(10, ge=1, le=50, description="Max results")


# ---------------------------------------------------------------------------
# Case Study CRUD Routes
# ---------------------------------------------------------------------------

@router.post("/case-studies", summary="Create a case study")
async def create_case_study(
    request: CreateCaseStudyRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Create a new case study in the evidence library.

    The case study is stored as an Evidence node in the knowledge graph
    and linked to any referenced products and pain signals.
    """
    service = CaseStudyService(driver)

    case_study = CaseStudy(
        tenant_id=tenant_id,
        title=request.title,
        content=request.content,
        industry=request.industry,
        summary=request.summary,
        company_name=request.company_name,
        company_size=request.company_size,
        products_used=request.products_used,
        pain_signals_addressed=request.pain_signals_addressed,
        outcomes=[o.model_dump() for o in request.outcomes] if request.outcomes else None,
        time_to_value_days=request.time_to_value_days,
        deal_size_usd=request.deal_size_usd,
        published_date=request.published_date,
        tags=request.tags,
    )

    result = await service.create(case_study)
    return result


@router.get("/case-studies", summary="Search case studies")
async def search_case_studies(
    tenant_id: str = Depends(get_verified_tenant_id),
    industry: str | None = Query(None, description="Filter by industry"),
    company_size: str | None = Query(None, description="Filter by company size"),
    product: str | None = Query(None, description="Filter by product name"),
    tag: str | None = Query(None, description="Filter by tag"),
    min_deal_size: float | None = Query(None, ge=0, description="Minimum deal size USD"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Search case studies with optional filters.

    Returns paginated results with linked products.
    """
    service = CaseStudyService(driver)

    products = [product] if product else None
    tags = [tag] if tag else None

    return await service.search(
        tenant_id=tenant_id,
        industry=industry,
        company_size=company_size,
        products=products,
        tags=tags,
        min_deal_size=min_deal_size,
        limit=limit,
        offset=offset,
    )


@router.get("/case-studies/{case_study_id}", summary="Get a case study")
async def get_case_study(
    case_study_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Get a case study by ID with linked products and signals."""
    service = CaseStudyService(driver)
    result = await service.get(tenant_id, case_study_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Case study {case_study_id} not found")

    return result


@router.put("/case-studies/{case_study_id}", summary="Update a case study")
async def update_case_study(
    case_study_id: str,
    request: UpdateCaseStudyRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Update a case study's properties."""
    service = CaseStudyService(driver)

    updates = request.model_dump(exclude_none=True)
    if "outcomes" in updates:
        updates["outcomes"] = [o.model_dump() if hasattr(o, "model_dump") else o for o in updates["outcomes"]]

    result = await service.update(tenant_id, case_study_id, updates)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Case study {case_study_id} not found")

    return result


@router.delete("/case-studies/{case_study_id}", summary="Delete a case study")
async def delete_case_study(
    case_study_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, str]:
    """Delete a case study and its relationships."""
    service = CaseStudyService(driver)
    deleted = await service.delete(tenant_id, case_study_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Case study {case_study_id} not found")

    return delete_case_studyResult.model_validate({"status": "deleted", "id": case_study_id})


# ---------------------------------------------------------------------------
# Bulk Import
# ---------------------------------------------------------------------------

@router.post("/case-studies/bulk-import", summary="Bulk import case studies")
async def bulk_import_case_studies(
    request: BulkImportRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Import multiple case studies in a single operation.

    Accepts up to 100 case studies per request.
    """
    service = CaseStudyService(driver)

    case_studies_data = [
        {
            **cs.model_dump(exclude_none=True),
            "outcomes": [o.model_dump() for o in cs.outcomes] if cs.outcomes else None,
        }
        for cs in request.case_studies
    ]

    return await service.bulk_import(tenant_id, case_studies_data)


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.get("/stats/by-industry", summary="Case study counts by industry")
async def stats_by_industry(
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, int]:
    """Get case study counts grouped by industry."""
    service = CaseStudyService(driver)
    return await service.get_by_industry(tenant_id)


@router.get("/stats/by-product", summary="Case study counts by product")
async def stats_by_product(
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, int]:
    """Get case study counts grouped by product."""
    service = CaseStudyService(driver)
    return await service.get_by_product(tenant_id)


# ---------------------------------------------------------------------------
# Semantic Search (uses existing evidence_search service)
# ---------------------------------------------------------------------------

@router.post("/search", summary="Semantic evidence search")
async def semantic_search(
    request: SemanticSearchRequest,
    http_request: Request,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Search evidence using vector similarity.

    Uses the existing evidence embedding index for semantic matching.
    Returns ranked results with relevance scores.
    """
    search_service = EvidenceSearchService(driver)

    correlation_id = http_request.headers.get("x-correlation-id") or http_request.headers.get("x-request-id") or "unknown"
    try:
        results = await search_service.find_matching_evidence(
            tenant_id=tenant_id,
            signal_description=request.query,
            evidence_types=request.evidence_types,
            limit=request.limit,
        )
    except EmbeddingProviderUnavailableError as exc:
        logger.warning(
            "semantic_search_embedding_provider_unavailable",
            provider=exc.provider,
            failure_cause=exc.failure_cause,
            retry_hint=exc.retry_hint,
            correlation_id=correlation_id,
        )
        raise create_service_unavailable_http_exception(
            message="Embedding provider unavailable",
            service=exc.provider,
            retry_after=exc.retry_after_seconds,
            details={
                "failure_cause": exc.failure_cause,
                "retry_hint": exc.retry_hint,
                "correlation_id": correlation_id,
            },
        ) from exc

    return semantic_searchResult.model_validate({
        "query": request.query,
        "total": len(results),
        "results": results,
    })


# ---------------------------------------------------------------------------
# Evidence-to-Driver Linking
# ---------------------------------------------------------------------------

class EvidenceLinkRequest(BaseModel):
    evidence_id: str = Field(..., description="Evidence (case study) identifier")
    driver_id: str = Field(..., description="Value driver identifier")


class EvidenceLinkResponse(BaseModel):
    evidence_id: str
    driver_id: str
    linked: bool
    linked_at: str


@router.post("/links", summary="Link evidence to a value driver")
async def link_evidence_to_driver(
    request: EvidenceLinkRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> EvidenceLinkResponse:
    """Create a graph relationship between Evidence and ValueDriver.

    Establishes `HAS_EVIDENCE` from ValueDriver to Evidence node,
    enabling value traceability from driver tree back to proof points.
    """
    query = """
    MATCH (e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
    MATCH (d:ValueDriver {id: $driver_id, tenant_id: $tenant_id})
    MERGE (d)-[r:HAS_EVIDENCE]->(e)
    ON CREATE SET r.linked_at = datetime()
    RETURN r.linked_at AS linked_at
    """
    try:
        async with driver.session() as session:
            result = await run_validated_query(session, query, {
                "evidence_id": request.evidence_id,
                "driver_id": request.driver_id,
                "tenant_id": tenant_id,
            })
            record = await result.single()
            if record is None:
                raise HTTPException(
                    status_code=404,
                    detail="Evidence or driver not found for tenant",
                )
            return EvidenceLinkResponse(
                evidence_id=request.evidence_id,
                driver_id=request.driver_id,
                linked=True,
                linked_at=record["linked_at"],
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to link evidence to driver", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail=f"Link creation failed: {str(e)}")


@router.delete("/links", summary="Unlink evidence from a value driver")
async def unlink_evidence_from_driver(
    evidence_id: str = Query(..., description="Evidence identifier"),
    driver_id: str = Query(..., description="Value driver identifier"),
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Remove the graph relationship between Evidence and ValueDriver."""
    query = """
    MATCH (d:ValueDriver {id: $driver_id, tenant_id: $tenant_id})-[r:HAS_EVIDENCE]->(e:Evidence {id: $evidence_id, tenant_id: $tenant_id})
    DELETE r
    RETURN count(r) AS deleted
    """
    try:
        async with driver.session() as session:
            result = await run_validated_query(session, query, {
                "evidence_id": evidence_id,
                "driver_id": driver_id,
                "tenant_id": tenant_id,
            })
            record = await result.single()
            deleted = record["deleted"] if record else 0
            return {"evidence_id": evidence_id, "driver_id": driver_id, "deleted": deleted}
    except Exception as e:
        logger.error("Failed to unlink evidence from driver", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail=f"Link deletion failed: {str(e)}")


@router.get("/links", summary="List evidence links for a driver")
async def list_evidence_links(
    driver_id: str = Query(..., description="Value driver identifier"),
    tenant_id: str = Depends(get_verified_tenant_id),
    driver=Depends(get_neo4j_driver),
) -> dict[str, Any]:
    """Return all Evidence nodes linked to a given ValueDriver."""
    query = """
    MATCH (d:ValueDriver {id: $driver_id, tenant_id: $tenant_id})-[:HAS_EVIDENCE]->(e:Evidence {tenant_id: $tenant_id})
    WHERE e.tenant_id = $tenant_id
    RETURN e.id AS evidence_id, e.title AS evidence_title, e.evidence_type AS evidence_type
    """
    try:
        async with driver.session() as session:
            result = await run_validated_query(session, query, {"driver_id": driver_id, "tenant_id": tenant_id})
            records = await result.data()
            return {
                "driver_id": driver_id,
                "links": [
                    {
                        "evidence_id": r["evidence_id"],
                        "evidence_title": r["evidence_title"],
                        "evidence_type": r["evidence_type"],
                    }
                    for r in records
                ],
            }
    except Exception as e:
        logger.error("Failed to list evidence links", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail=f"Link listing failed: {str(e)}")
