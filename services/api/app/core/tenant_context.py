from fastapi import Depends, HTTPException, Request

from app.core.security import TokenPayload, require_authenticated
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_JWT,
    RequestContext,
    get_request_context,
    set_request_context,
)


def get_tenant_id() -> str:
    ctx = get_request_context()
    tenant_id = ctx.tenant_id if ctx is not None else None
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    return str(tenant_id)


class TenantRequired:
    """Resolve tenant_id from the authenticated JWT payload.

    The tenant is taken from the verified ``tenant_id`` claim in the JWT —
    not from a client-supplied header — so callers cannot spoof tenants.
    The ``X-Tenant-ID`` header is accepted only as a hint when it matches
    the JWT claim; mismatches are rejected.
    """

    async def __call__(
        self,
        request: Request,
        auth: TokenPayload = Depends(require_authenticated),
    ) -> str:
        set_request_context(None)
        jwt_tenant = auth.tenant_id.strip() if auth.tenant_id else ""
        if not jwt_tenant:
            raise HTTPException(status_code=401, detail="Tenant context required")

        # Optional header — must match the JWT claim if provided
        header_tenant = request.headers["X-Tenant-ID"] if "X-Tenant-ID" in request.headers else None
        if header_tenant and header_tenant != jwt_tenant:
            raise HTTPException(
                status_code=403,
                detail="X-Tenant-ID does not match authenticated tenant",
            )

        set_request_context(
            RequestContext(
                tenant_id=jwt_tenant,
                user_id=auth.sub,
                source=AUTH_SOURCE_JWT,
                auth_source=AUTH_SOURCE_JWT,
                raw={
                    "jti": auth.jti,
                    "account_id": auth.account_id,
                    "account_ids": auth.account_ids,
                },
            )
        )
        return jwt_tenant


tenant_required = TenantRequired()
