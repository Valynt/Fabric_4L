import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
)
from value_fabric.shared.identity.dependencies import require_tenant_context

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session

"""Calculator API routes for Layer 3 Knowledge Graph.

Provides endpoints for value lever configuration and value case persistence.
Owner: layer3-knowledge
Removal/migration target: 2026-09-30
"""

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calculators", tags=["calculators"])


# ── Schemas ──────────────────────────────────────────────────────────────────────

class ValueLever(BaseModel):
    id: str
    name: str
    base_value: float
    min_value: float
    max_value: float
    unit: str
    annual_impact: float
    confidence: int = Field(ge=0, le=100)
    category: str


class LeverConfigRequest(BaseModel):
    industry: str | None = None
    company_size: str | None = None
    product_line: str | None = None


class LeverConfigResponse(BaseModel):
    levers: list[ValueLever]
    metadata: dict


class ValueCaseRequest(BaseModel):
    account_id: str
    prospect_id: str | None = None
    levers: list[dict]
    scenarios: list[dict]
    metadata: dict


class ValueCaseResponse(BaseModel):
    case_id: str
    account_id: str
    created_at: str
    updated_at: str
    levers: list[dict]
    scenarios: list[dict]
    metadata: dict


# ── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("/levers", response_model=LeverConfigResponse)
async def get_value_levers(
    request: LeverConfigRequest,
    http_request: Request,
    context = Depends(require_tenant_context),
):
    """Get value lever configuration for value calculations.

    Returns tenant-scoped lever configurations filtered by industry/company size.
    """
    tenant_id = context.tenant_id
    
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        # Query for value levers in Neo4j
        query = """
        MATCH (l:ValueLever {tenant_id: $tenant_id})
        """
        params = {"tenant_id": tenant_id}
        
        # Add filters if provided
        if request.industry:
            query += " WHERE l.industry = $industry"
            params["industry"] = request.industry
        elif request.company_size:
            query += " WHERE l.company_size = $company_size"
            params["company_size"] = request.company_size
        
        query += " RETURN l ORDER BY l.category, l.name"
        
        try:
            result = await neo4j.execute_query(query, params)
            levers = []
            for record in result:
                node = record.get("l")
                if node:
                    levers.append({
                        "id": node.get("lever_id"),
                        "name": node.get("name"),
                        "base_value": node.get("base_value"),
                        "min_value": node.get("min_value"),
                        "max_value": node.get("max_value"),
                        "unit": node.get("unit"),
                        "annual_impact": node.get("annual_impact"),
                        "confidence": node.get("confidence", 80),
                        "category": node.get("category", "General"),
                    })
            
            return LeverConfigResponse(
                levers=levers,
                metadata={
                    "industry": request.industry or "All",
                    "company_size": request.company_size or "All",
                    "version": "1.0",
                    "count": len(levers),
                }
            )
        except Exception as e:
            logger.error("Database error in levers query: %s", e)
            raise ServiceUnavailableError(message="Database error")


@router.post("/value-cases", response_model=ValueCaseResponse, status_code=201)
async def create_value_case(
    case_data: ValueCaseRequest,
    http_request: Request,
    context = Depends(require_tenant_context),
):
    """Create a new value case with scenarios and calculations."""
    tenant_id = context.tenant_id
    
    case_id = f"case_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        query = """
        CREATE (vc:ValueCase {
            case_id: $case_id,
            tenant_id: $tenant_id,
            account_id: $account_id,
            prospect_id: $prospect_id,
            levers: $levers,
            scenarios: $scenarios,
            metadata: $metadata,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN vc
        """
        
        params = {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "account_id": case_data.account_id,
            "prospect_id": case_data.prospect_id,
            "levers": case_data.levers,
            "scenarios": case_data.scenarios,
            "metadata": case_data.metadata,
        }
        
        try:
            await neo4j.execute_query(query, params)
            
            return ValueCaseResponse(
                case_id=case_id,
                account_id=case_data.account_id,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                levers=case_data.levers,
                scenarios=case_data.scenarios,
                metadata=case_data.metadata,
            )
        except Exception as e:
            logger.error("Database error creating value case: %s", e)
            raise ServiceUnavailableError(message="Database error")


@router.get("/value-cases/{case_id}", response_model=ValueCaseResponse)
async def get_value_case(
    case_id: str,
    http_request: Request,
    context = Depends(require_tenant_context),
):
    """Get a value case by ID."""
    tenant_id = context.tenant_id
    
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        query = """
        MATCH (vc:ValueCase {case_id: $case_id, tenant_id: $tenant_id})
        RETURN vc
        """
        
        params = {"case_id": case_id, "tenant_id": tenant_id}
        
        try:
            result = await neo4j.execute_query(query, params)
            if not result or not result[0]:
                raise NotFoundError(message = str(f"Value case {case_id} not found"))
            
            node = result[0].get("vc")
            
            return ValueCaseResponse(
                case_id=node.get("case_id"),
                account_id=node.get("account_id"),
                created_at=node.get("created_at"),
                updated_at=node.get("updated_at"),
                levers=node.get("levers", []),
                scenarios=node.get("scenarios", []),
                metadata=node.get("metadata", {}),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Database error retrieving value case %s: %s", case_id, e)
            raise ServiceUnavailableError(message="Database error")


@router.put("/value-cases/{case_id}", response_model=ValueCaseResponse)
async def update_value_case(
    case_id: str,
    case_data: ValueCaseRequest,
    http_request: Request,
    context = Depends(require_tenant_context),
):
    """Update an existing value case."""
    tenant_id = context.tenant_id
    
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        query = """
        MATCH (vc:ValueCase {case_id: $case_id, tenant_id: $tenant_id})
        SET vc.levers = $levers,
            vc.scenarios = $scenarios,
            vc.metadata = $metadata,
            vc.updated_at = datetime()
        RETURN vc
        """
        
        params = {
            "case_id": case_id,
            "tenant_id": tenant_id,
            "levers": case_data.levers,
            "scenarios": case_data.scenarios,
            "metadata": case_data.metadata,
        }
        
        try:
            result = await neo4j.execute_query(query, params)
            if not result or not result[0]:
                raise NotFoundError(message = str(f"Value case {case_id} not found"))
            
            node = result[0].get("vc")
            
            return ValueCaseResponse(
                case_id=node.get("case_id"),
                account_id=node.get("account_id"),
                created_at=node.get("created_at"),
                updated_at=node.get("updated_at"),
                levers=case_data.levers,
                scenarios=case_data.scenarios,
                metadata=case_data.metadata,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Database error updating value case %s: %s", case_id, e)
            raise ServiceUnavailableError(message="Database error")
