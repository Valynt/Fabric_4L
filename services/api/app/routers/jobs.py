from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from app.clients.layer4_client import Layer4Client
from app.core.security import require_bearer_declaration
from app.models.product import ProductJobResponse

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(require_bearer_declaration)],
)


def _get_layer4_client() -> Layer4Client:
    return Layer4Client()


@router.get("/{job_id}", response_model=ProductJobResponse)
async def get_job_status(
    job_id: str,
    ctx: RequestContext = Depends(require_authenticated),
    client: Layer4Client = Depends(_get_layer4_client),
):
    tenant_id = str(ctx.tenant_id)
    try:
        workflow = await client.get_workflow(tenant_id, job_id)
        result = await client.get_workflow_result(tenant_id, job_id)
    except HTTPException as exc:
        if exc.status_code in (403, 404):
            raise HTTPException(status_code=404, detail="Job not found") from exc
        raise

    status = workflow.get("status", "unknown").lower()
    product_code = workflow.get("metadata", {}).get("product_code") or "unknown"
    return ProductJobResponse(
        job_id=job_id,
        product_code=product_code,
        status=status,
        result=result.get("output") if result else None,
    )
