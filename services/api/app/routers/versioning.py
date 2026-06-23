from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from value_fabric.shared.error_handling.exceptions import NotFoundError

from app.core.database import db
from app.core.tenant_context import tenant_required
from app.models.schemas import AccountVersionSnapshot, PaginatedResponse, SnapshotDiffResponse

router = APIRouter(prefix="/accounts/{account_id}", tags=["Versioning"])


@router.post("/snapshots", response_model=AccountVersionSnapshot, status_code=201)
async def create_snapshot(
    account_id: str,
    snapshot: AccountVersionSnapshot,
    tenant_id: str = Depends(tenant_required),
):
    snapshot.account_id = account_id
    snapshot.tenant_id = tenant_id
    db.snapshots.insert(snapshot.id, snapshot)
    return snapshot


@router.get("/snapshots", response_model=PaginatedResponse[AccountVersionSnapshot])
async def list_snapshots(
    account_id: str,
    tenant_id: str = Depends(tenant_required),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    items = db.snapshots.list(
        tenant_id=tenant_id,
        filter_fn=lambda s: s.account_id == account_id,
        limit=limit,
        offset=offset,
    )
    total = db.snapshots.count(tenant_id=tenant_id, filter_fn=lambda s: s.account_id == account_id)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/snapshots/{snapshot_id}", response_model=AccountVersionSnapshot)
async def get_snapshot(
    account_id: str,
    snapshot_id: str,
    tenant_id: str = Depends(tenant_required),
):
    snapshot = db.snapshots.get(snapshot_id, tenant_id=tenant_id)
    if not snapshot or snapshot.account_id != account_id:
        raise NotFoundError(message="Snapshot not found")
    return snapshot


@router.post("/snapshots/{snapshot_id}/diff", response_model=SnapshotDiffResponse)
async def diff_snapshots(
    account_id: str,
    snapshot_id: str,
    compare_to_id: str,
    tenant_id: str = Depends(tenant_required),
):
    base = db.snapshots.get(snapshot_id, tenant_id=tenant_id)
    compare = db.snapshots.get(compare_to_id, tenant_id=tenant_id)
    if not base or base.account_id != account_id:
        raise NotFoundError(message="Base snapshot not found")
    if not compare or compare.account_id != account_id:
        raise NotFoundError(message="Compare snapshot not found")

    # Simple field-level diff on scalar properties
    changes: list[dict[str, Any]] = []
    if base.label != compare.label:
        changes.append({"field": "label", "from": base.label, "to": compare.label})
    if len(base.signals) != len(compare.signals):
        changes.append({"field": "signals", "from": len(base.signals), "to": len(compare.signals)})
    if len(base.drivers) != len(compare.drivers):
        changes.append({"field": "drivers", "from": len(base.drivers), "to": len(compare.drivers)})
    if len(base.roi_calculations) != len(compare.roi_calculations):
        changes.append({"field": "roi_calculations", "from": len(base.roi_calculations), "to": len(compare.roi_calculations)})

    return {
        "base_snapshot_id": snapshot_id,
        "compare_snapshot_id": compare_to_id,
        "changes": changes,
        "created_at_base": base.created_at,
        "created_at_compare": compare.created_at,
    }


@router.post("/snapshots/{snapshot_id}/restore", response_model=AccountVersionSnapshot)
async def restore_snapshot(
    account_id: str,
    snapshot_id: str,
    tenant_id: str = Depends(tenant_required),
):
    snapshot = db.snapshots.get(snapshot_id, tenant_id=tenant_id)
    if not snapshot or snapshot.account_id != account_id:
        raise NotFoundError(message="Snapshot not found")

    # Create a new snapshot representing the restored state
    restored = AccountVersionSnapshot(
        id=snapshot.id + "_restored",
        account_id=account_id,
        tenant_id=tenant_id,
        created_by="system",
        snapshot_type="manual",
        signals=snapshot.signals,
        drivers=snapshot.drivers,
        roi_calculations=snapshot.roi_calculations,
        business_case_ids=snapshot.business_case_ids,
        label=f"Restored from {snapshot_id}",
    )
    db.snapshots.insert(restored.id, restored)
    return restored
