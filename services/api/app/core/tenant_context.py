from contextvars import ContextVar

from fastapi import Depends, HTTPException, Request

from app.core.security import TokenPayload, require_authenticated

TenantContext: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def get_tenant_id() -> str:
    tenant_id = TenantContext.get()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")
    return tenant_id


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
        jwt_tenant = auth.tenant_id

        # Optional header — must match the JWT claim if provided
        header_tenant = request.headers["X-Tenant-ID"] if "X-Tenant-ID" in request.headers else None
        if header_tenant and header_tenant != jwt_tenant:
            raise HTTPException(
                status_code=403,
                detail="X-Tenant-ID does not match authenticated tenant",
            )

        TenantContext.set(jwt_tenant)
        return jwt_tenant


tenant_required = TenantRequired()
