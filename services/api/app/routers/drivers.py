from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.tenant_enforcement import enforce_authenticated_tenant
from app.core.tenant_context import tenant_required
from app.models.schemas import PaginatedResponse, ValueDriver, ValueTreeCategories, ValueTreeResponse

router = APIRouter(prefix="/accounts/{account_id}", tags=["Driver Tree"])


@router.get("/drivers", response_model=PaginatedResponse[ValueDriver])
async def list_drivers(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.drivers.list(tenant_id=tenant_id, filter_fn=lambda d: d.account_id == account_id, limit=limit, offset=offset)
    total = db.drivers.count(tenant_id=tenant_id, filter_fn=lambda d: d.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/value-tree", response_model=ValueTreeResponse)
async def get_value_tree(account_id: str, tenant_id: str = Depends(tenant_required)):
    drivers = db.drivers.list(tenant_id=tenant_id, filter_fn=lambda d: d.account_id == account_id)
    return ValueTreeResponse(
        account_id=account_id,
        categories=ValueTreeCategories(
            revenue_uplift=[d for d in drivers if d.category == "revenue_uplift"],
            cost_savings=[d for d in drivers if d.category == "cost_savings"],
            risk_reduction=[d for d in drivers if d.category == "risk_reduction"],
        ),
    )


@router.post("/drivers/generate", response_model=ValueDriver, status_code=201)
async def generate_driver(
    account_id: str, driver: ValueDriver, tenant_id: str = Depends(tenant_required)
):
    enforce_authenticated_tenant(
        body_tenant_id=driver.tenant_id,
        authenticated_tenant_id=tenant_id,
        route="/v1/accounts/{account_id}/drivers/generate",
        operation="generate_driver",
    )
    driver.account_id = account_id
    driver.tenant_id = tenant_id
    db.drivers.insert(driver.id, driver)
    return driver


@router.patch("/drivers/{driver_id}", response_model=ValueDriver)
async def update_driver(
    driver_id: str,
    fields: dict[str, Any],
    tenant_id: str = Depends(tenant_required),
):
    drv = db.drivers.update(driver_id, tenant_id=tenant_id, **fields)
    if not drv:
        raise NotFoundError(message="Driver not found")
    return drv
