"""Canonical backend-issued authorization snapshot endpoint."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import AuthDirectory, get_auth_directory
from app.core.clerk_auth import require_clerk_authenticated
from app.services.authorization_snapshot import build_authorization_snapshot

router = APIRouter(prefix="/auth/authorization-snapshot", tags=["Authorization"])


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TenantSnapshot(_ContractModel):
    id: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=128)


class TenantScope(_ContractModel):
    kind: Literal["tenant"]


class AccountScopeRequest(_ContractModel):
    kind: Literal["account"]
    accountId: str = Field(min_length=1, max_length=128)


class EntitlementSnapshot(_ContractModel):
    key: str = Field(min_length=1, max_length=256)
    expiresAt: str | None = None


class AuthorizationSnapshotResponse(_ContractModel):
    principalId: str = Field(min_length=1, max_length=128)
    sessionDiscriminator: str = Field(min_length=1, max_length=256)
    tenant: TenantSnapshot
    accountScope: Annotated[TenantScope | AccountScopeRequest, Field(discriminator="kind")]
    roles: list[Literal["member", "analyst", "account_admin", "tenant_admin", "platform_admin"]] = (
        Field(min_length=1)
    )
    permissions: list[str]
    entitlements: list[EntitlementSnapshot]
    source: Literal["backend"]
    issuedAt: str
    expiresAt: str


@router.get("", response_model=AuthorizationSnapshotResponse, response_model_by_alias=True)
@router.get(
    "/",
    response_model=AuthorizationSnapshotResponse,
    response_model_by_alias=True,
    include_in_schema=False,
)
async def get_authorization_snapshot(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> AuthorizationSnapshotResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return AuthorizationSnapshotResponse.model_validate(
        build_authorization_snapshot(auth=auth, request=request, directory=directory)
    )
