from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Product Portfolio API routes for the Knowledge Graph.

Provides CRUD operations for Products and Features, capability linking,
signal-to-product matching, and portfolio analytics.

All endpoints require authentication via GovernanceMiddleware.
Tenant identity is extracted from the verified JWT/API-key context,
never from raw headers (V-001, V-002 remediation).
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from value_fabric.shared.security.dil_auth import get_verified_tenant_id

from ...api.dependencies import get_neo4j_driver

router = APIRouter(prefix="/products", tags=["products"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ProductCreateRequest(BaseModel):
    """Request body for creating a product."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1, max_length=4096)
    category: str | None = Field(None, max_length=128)
    sku: str | None = Field(None, max_length=64)
    pricing_model: str | None = Field(None, max_length=64)
    target_personas: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductUpdateRequest(BaseModel):
    """Request body for updating a product."""

    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = Field(None, min_length=1, max_length=4096)
    category: str | None = Field(None, max_length=128)
    sku: str | None = Field(None, max_length=64)
    pricing_model: str | None = Field(None, max_length=64)
    target_personas: list[str] | None = None
    industries: list[str] | None = None


class FeatureCreateRequest(BaseModel):
    """Request body for adding a feature to a product."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1, max_length=4096)
    feature_type: str = Field("core", pattern="^(core|addon|premium)$")
    maturity: str = Field("ga", pattern="^(beta|ga|deprecated)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityLinkRequest(BaseModel):
    """Request body for linking a product to a capability."""

    capability_id: str = Field(..., min_length=1)
    strength: float = Field(1.0, ge=0.0, le=1.0)


class ProductResponse(BaseModel):
    """Standard product response."""

    id: str
    name: str
    description: str | None = None
    category: str | None = None
    sku: str | None = None
    pricing_model: str | None = None
    target_personas: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    features: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class ProductListResponse(BaseModel):
    """Paginated product list response."""

    products: list[dict[str, Any]]
    total: int
    skip: int
    limit: int


class SignalMatchResponse(BaseModel):
    """Signal-to-product match result."""

    product: dict[str, Any]
    total_score: float
    signal_count: int
    top_matches: list[dict[str, Any]]


class PortfolioSummaryResponse(BaseModel):
    """Portfolio analytics summary."""

    total_products: int
    total_features: int
    total_capabilities: int
    categories: list[str]
    avg_features_per_product: float
    avg_capabilities_per_product: float


class CapabilityCoverageItem(BaseModel):
    """Single capability coverage entry."""

    capability: dict[str, Any]
    products: list[dict[str, Any]]
    signal_demand: int
    status: str  # "covered" or "gap"


# ---------------------------------------------------------------------------
# Helper to get ProductService
# ---------------------------------------------------------------------------

async def get_product_service(driver=Depends(get_neo4j_driver)):
    """Dependency injection for ProductService."""
    from services.product_service import ProductService

    return ProductService(driver)


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201)
async def create_product(
    body: ProductCreateRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Create a new product in the knowledge graph."""
    from services.product_service import ProductCreate

    product = ProductCreate(
        name=body.name,
        description=body.description,
        category=body.category,
        sku=body.sku,
        pricing_model=body.pricing_model,
        target_personas=body.target_personas,
        industries=body.industries,
        metadata=body.metadata,
    )
    result = await service.create_product(tenant_id, product)
    return result


@router.get("", response_model=ProductListResponse)
async def list_products(
    category: str | None = Query(None),
    industry: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """List products with optional filtering."""
    return await service.list_products(
        tenant_id, category=category, industry=industry, skip=skip, limit=limit
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Get a product by ID with its features and capabilities."""
    result = await service.get_product(tenant_id, product_id)
    if not result:
        raise NotFoundError(message = "Product not found")
    return result


@router.patch("/{product_id}", response_model=dict)
async def update_product(
    product_id: str,
    body: ProductUpdateRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Update a product's properties."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise ValidationError(message = "No fields to update")
    result = await service.update_product(tenant_id, product_id, updates)
    if not result:
        raise NotFoundError(message = "Product not found")
    return result


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Delete a product and its orphaned features."""
    deleted = await service.delete_product(tenant_id, product_id)
    if not deleted:
        raise NotFoundError(message = "Product not found")


# ---------------------------------------------------------------------------
# Feature Management
# ---------------------------------------------------------------------------

@router.post("/{product_id}/features", response_model=dict, status_code=201)
async def add_feature(
    product_id: str,
    body: FeatureCreateRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Add a feature to a product."""
    from services.product_service import FeatureCreate

    feature = FeatureCreate(
        name=body.name,
        description=body.description,
        feature_type=body.feature_type,
        maturity=body.maturity,
        metadata=body.metadata,
    )
    result = await service.add_feature(tenant_id, product_id, feature)
    if not result:
        raise NotFoundError(message = "Product not found")
    return result


@router.delete("/{product_id}/features/{feature_id}", status_code=204)
async def remove_feature(
    product_id: str,
    feature_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Remove a feature from a product."""
    removed = await service.remove_feature(tenant_id, product_id, feature_id)
    if not removed:
        raise NotFoundError(message = "Feature or product not found")


# ---------------------------------------------------------------------------
# Capability Linking
# ---------------------------------------------------------------------------

@router.post("/{product_id}/capabilities", response_model=dict, status_code=201)
async def link_capability(
    product_id: str,
    body: CapabilityLinkRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Link a product to a capability with a strength score."""
    result = await service.link_capability(
        tenant_id, product_id, body.capability_id, body.strength
    )
    if not result:
        raise NotFoundError(message = "Product or capability not found")
    return result


@router.delete("/{product_id}/capabilities/{capability_id}", status_code=204)
async def unlink_capability(
    product_id: str,
    capability_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Remove a product-capability link."""
    removed = await service.unlink_capability(tenant_id, product_id, capability_id)
    if not removed:
        raise NotFoundError(message = "Link not found")


# ---------------------------------------------------------------------------
# Signal-to-Product Matching
# ---------------------------------------------------------------------------

@router.get("/matching/signals", response_model=list[SignalMatchResponse])
async def match_signals(
    account_id: str | None = Query(None),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Match pain signals to products via shared capabilities.

    Returns products ranked by match score, with the top matching
    signals and capabilities for each product.
    """
    return await service.match_signals_to_products(
        tenant_id, account_id=account_id, min_confidence=min_confidence
    )


# ---------------------------------------------------------------------------
# Portfolio Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics/summary", response_model=PortfolioSummaryResponse)
async def portfolio_summary(
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Get a summary of the product portfolio."""
    return await service.get_portfolio_summary(tenant_id)


@router.get("/analytics/coverage", response_model=list[CapabilityCoverageItem])
async def capability_coverage(
    tenant_id: str = Depends(get_verified_tenant_id),
    service=Depends(get_product_service),
):
    """Show capability coverage: which are addressed by products, which are gaps."""
    return await service.get_capability_coverage(tenant_id)
