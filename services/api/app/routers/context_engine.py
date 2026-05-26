from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import ContextEngineItem, Formula, PaginatedResponse, ValuePack

router = APIRouter(prefix="/context-engine", tags=["Context Engine"])


@router.get("/value-packs", response_model=PaginatedResponse[ValuePack])
async def list_value_packs(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.value_packs.list(limit=limit, offset=offset)
    total = len(db.value_packs.list())
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/value-packs/{value_pack_id}", response_model=ValuePack)
async def get_value_pack(value_pack_id: str, tenant_id: str = Depends(tenant_required)):
    pack = db.value_packs.get(value_pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Value pack not found")
    return pack


@router.get("/formulas", response_model=PaginatedResponse[Formula])
async def list_formulas(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.formulas.list(limit=limit, offset=offset)
    total = len(db.formulas.list())
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/formulas/{formula_id}", response_model=Formula)
async def get_formula(formula_id: str, tenant_id: str = Depends(tenant_required)):
    formula = db.formulas.get(formula_id)
    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")
    return formula


@router.get("/benchmarks", response_model=PaginatedResponse[ContextEngineItem])
async def list_benchmarks(
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    raw_items: list[dict] = []
    typed_items = [ContextEngineItem.model_validate(item) for item in raw_items]
    return PaginatedResponse(items=typed_items, total=0, limit=limit, offset=offset)


@router.get("/ontology")
async def get_ontology(tenant_id: str = Depends(tenant_required)):
    packs = db.value_packs.list()
    return {"packs": packs, "ontology": {}}
