from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError, AuthorizationError, NotFoundError, RateLimitError, ValidationError
"""OIDC SSO routes for tenant authentication with PKCE support (P0-10).

GET  /auth/oidc/{tenant_slug}/login    — initiate OIDC flow with PKCE
GET  /auth/oidc/callback               — handle IdP callback; sets httpOnly cookie
GET  /auth/oidc/{tenant_slug}/metadata — return non-sensitive IdP config
POST /auth/refresh                     — rotate session cookie; returns updated metadata
POST /auth/logout                      — expire session cookie
"""


import base64
import hashlib
import logging
import os
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.jwt import encode_jwt
from value_fabric.shared.identity.oidc import OIDCClient, map_role_from_claims
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig
from value_fabric.shared.identity.permissions import Role
from value_fabric.shared.identity.providers import resolve_client_secret, resolve_oidc_config
from value_fabric.shared.models.typed_dict import TypedDictModel

from ....api.security.csrf import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    issue_csrf_token,
    validate_double_submit,
)

# SECURITY: OIDC login/callback endpoints are pre-authentication flows.
# The user does not yet have a JWT, so get_db (no tenant context) is
# intentional here. Authentication is via OIDC provider + PKCE.
from ....database import get_db_from_context
from ....tenants.models.tenant import Tenant
from ....tenants.models.user import User


class oidc_loginResult(TypedDictModel):
    authorization_url: Any
    state: Any

class oidc_callbackResult(TypedDictModel):
    """Non-secret session metadata returned after a successful OIDC callback.

    The access token is delivered exclusively via the httpOnly ``vf_session``
    cookie set on this response.  It is intentionally absent from this body so
    that JavaScript cannot read it.
    """
    email: Any
    expires_in: int
    role: Any
    token_type: str
    user_id: Any


class refresh_result(TypedDictModel):
    """Non-secret metadata returned after a successful token refresh."""
    email: Any
    expires_in: int
    role: Any
    token_type: str
    user_id: Any

class oidc_metadataResult(TypedDictModel):
    auto_provision_users: Any
    claim_mapping_keys: list[Any]
    default_role: Any
    enabled: Any
    issuer_url: Any
    provider_name: Any
    scopes: Any

router = APIRouter(prefix="/auth/oidc", tags=["OIDC SSO"])

AUTH_PREAUTH_WINDOW_SECONDS = 60
AUTH_PREAUTH_MAX_ATTEMPTS = 5
_auth_preauth_buckets: dict[str, tuple[float, int]] = {}

_DEFAULT_REDIRECT_URI = os.getenv(
    "OIDC_DEFAULT_REDIRECT_URI", "https://localhost:3000/auth/callback"
)


def _generate_state() -> str:
    return secrets.token_urlsafe(32)


def _generate_nonce() -> str:
    return secrets.token_urlsafe(32)


def _resolve_client_ip(request: Request) -> str:
    """Return the direct peer address for anonymous auth throttling.

    Do not trust forwarded headers here. Proxy-origin normalization belongs at
    the edge; using the socket peer keeps this route-level limiter conservative.
    """
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_preauth_rate_limit(request: Request, endpoint: str, discriminator: str | None = None) -> None:
    """Fail closed on repeated anonymous OIDC login/callback abuse."""
    now = time.time()
    client_ip = _resolve_client_ip(request)
    suffix = discriminator or "anonymous"
    key = f"auth:{endpoint}:{client_ip}:{suffix}"
    window_start, count = _auth_preauth_buckets.get(key, (now, 0))

    if now - window_start >= AUTH_PREAUTH_WINDOW_SECONDS:
        window_start = now
        count = 0

    if count >= AUTH_PREAUTH_MAX_ATTEMPTS:
        retry_after = max(1, int(AUTH_PREAUTH_WINDOW_SECONDS - (now - window_start)))
        raise RateLimitError(message = "Too many authentication attempts")

    _auth_preauth_buckets[key] = (window_start, count + 1)


# P0-10: PKCE helper functions
def _generate_code_verifier() -> str:
    """Generate PKCE code_verifier (43-128 chars, base64url)."""
    # RFC 7636: code_verifier is 43-128 chars of [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")


def _generate_code_challenge(code_verifier: str) -> str:
    """Generate PKCE code_challenge from code_verifier using S256 method."""
    # RFC 7636: code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


async def _get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def _get_user_by_email(db: AsyncSession, tenant_id: UUID, email: str) -> User | None:
    result = await db.execute(select(User).where(User.tenant_id == tenant_id, User.email == email))
    return result.scalar_one_or_none()


async def _get_client_secret(config: OIDCProviderConfig) -> str:
    """Resolve the OIDC client secret from config reference.

    Supports:
    - Provider-specific generation (Apple JWT)
    - Vault references: "vault:secret/data/path#key"
    - Environment variable references: "ENV_VAR_NAME"
    - Direct values (fallback)

    Raises:
        ValueError: If client secret cannot be resolved
    """
    # Provider-specific secret generation (e.g., Apple JWT)
    provider = (config.provider_name or "oidc").strip().lower()
    if provider == "apple":
        try:
            secret = await resolve_client_secret(config)
            if secret:
                return secret
        except ValueError:
            pass  # Fall through to standard resolution for better error messages

    # First try client_secret_ref if provided
    if config.client_secret_ref:
        # Handle Vault references
        if config.client_secret_ref.startswith("vault:"):
            from value_fabric.shared.identity.vault_check import resolve_vault_secret

            secret = await resolve_vault_secret(config.client_secret_ref)
            if secret:
                return secret
            raise ValueError(f"Failed to resolve Vault secret: {config.client_secret_ref}")
        else:
            # Treat as environment variable name
            secret = os.getenv(config.client_secret_ref)
            if secret:
                return secret
            raise ValueError(f"Environment variable not set: {config.client_secret_ref}")

    # Try fallback env var pattern
    fallback_key = f"OIDC_CLIENT_SECRET_{config.provider_name.upper()}"
    secret = os.getenv(fallback_key)
    if secret:
        return secret

    # Try direct client_secret field
    if config.client_secret:
        return config.client_secret

    raise ValueError(
        f"No client secret found. Set {fallback_key} environment variable "
        f"or configure client_secret_ref in tenant settings."
    )


@router.get("/{tenant_slug}/login")
async def oidc_login(
    request: Request,
    tenant_slug: str,
    redirect_uri: str | None = Query(None),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, str]:
    """Initiate OIDC login for a tenant.

    Stores state/nonce in ``oidc_sessions`` and returns the IdP authorize URL.
    """
    _check_preauth_rate_limit(request, "login", tenant_slug)

    tenant = await _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise NotFoundError(message = "Tenant not found")

    raw_config = OIDCProviderConfig.from_settings(tenant.settings or {})
    if raw_config is None or not raw_config.enabled:
        raise ValidationError(message = "OIDC is not enabled for this tenant")

    # Apply provider-specific presets (Google/Apple endpoints, scopes, etc.)
    oidc_config = resolve_oidc_config(raw_config)

    oidc_client = OIDCClient()
    try:
        metadata = await oidc_client.discover(oidc_config.issuer_url)
    except Exception as exc:
        logger.warning("OIDC provider discovery failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="Failed to discover OIDC provider"
        ) from exc

    state = _generate_state()
    nonce = _generate_nonce()
    # P0-10: Generate PKCE parameters
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    final_redirect = redirect_uri or _DEFAULT_REDIRECT_URI

    # Store session with PKCE code_verifier
    from sqlalchemy import text

    await db.execute(
        text(
            """
            INSERT INTO oidc_sessions (tenant_id, state, nonce, code_verifier, redirect_uri, expires_at, use_pkce)
            VALUES (:tenant_id, :state, :nonce, :code_verifier, :redirect_uri, :expires_at, :use_pkce)
            """
        ),
        {
            "tenant_id": tenant.id,
            "state": state,
            "nonce": nonce,
            "code_verifier": code_verifier,
            "redirect_uri": final_redirect,
            "expires_at": datetime.now(UTC) + timedelta(minutes=10),
            "use_pkce": True,
        },
    )

    # P0-10: Build authorize URL with PKCE code_challenge
    auth_url = oidc_client.build_authorize_url(
        metadata=metadata,
        client_id=oidc_config.client_id,
        redirect_uri=final_redirect,
        state=state,
        nonce=nonce,
        scopes=oidc_config.scopes,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    return oidc_loginResult.model_validate({"authorization_url": auth_url, "state": state})


@router.get("/callback")
async def oidc_callback(
    request: Request,
    response: Response,
    state: str = Query(...),
    code: str = Query(...),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Handle OIDC callback from the identity provider.

    Validates state, exchanges code for tokens, verifies id_token,
    maps claims to VF role, auto-provisions the user if enabled,
    and returns an internal JWT access_token.
    """
    from sqlalchemy import text

    _check_preauth_rate_limit(request, "callback", state)

    # Look up and validate session (P0-10: include code_verifier for PKCE)
    result = await db.execute(
        text(
            """
            SELECT tenant_id, nonce, code_verifier, redirect_uri, expires_at
            FROM oidc_sessions WHERE state = :state
            """
        ),
        {"state": state},
    )
    row = result.mappings().one_or_none()
    if row is None:
        emit_audit_event(
            AuditAction.OIDC_LOGIN_FAILED,
            resource_type="OIDCSession",
            outcome=AuditOutcome.FAILURE,
            details={"reason": "invalid_state"},
        )
        raise ValidationError(message = "Invalid or expired state parameter")

    if row["expires_at"] < datetime.now(UTC):
        await db.execute(text("DELETE FROM oidc_sessions WHERE state = :state"), {"state": state})
        emit_audit_event(
            AuditAction.OIDC_LOGIN_FAILED,
            tenant_id=row["tenant_id"],
            resource_type="OIDCSession",
            outcome=AuditOutcome.FAILURE,
            details={"reason": "expired_state"},
        )
        raise ValidationError(message = "OIDC session expired")

    tenant_id: UUID = row["tenant_id"]
    nonce: str = row["nonce"]
    code_verifier: str | None = row.get("code_verifier")
    redirect_uri: str = row["redirect_uri"]

    # Clean up session
    await db.execute(text("DELETE FROM oidc_sessions WHERE state = :state"), {"state": state})

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError(message = "Tenant not found")

    raw_config = OIDCProviderConfig.from_settings(tenant.settings or {})
    if raw_config is None or not raw_config.enabled:
        raise ValidationError(message = "OIDC is not enabled for this tenant")

    # Apply provider-specific presets (Google/Apple endpoints, scopes, etc.)
    oidc_config = resolve_oidc_config(raw_config)

    client_secret = await _get_client_secret(oidc_config)
    oidc_client = OIDCClient()

    try:
        metadata = await oidc_client.discover(oidc_config.issuer_url)
        # P0-10: Pass code_verifier for PKCE verification
        token_response = await oidc_client.exchange_code(
            token_endpoint=metadata["token_endpoint"],
            code=code,
            redirect_uri=redirect_uri,
            client_id=oidc_config.client_id,
            client_secret=client_secret,
            code_verifier=code_verifier,  # PKCE parameter
        )
        id_token = token_response.get("id_token")
        if not id_token:
            raise HTTPException(status_code=502, detail="No id_token in token response")

        claims = await oidc_client.verify_id_token(
            id_token=id_token,
            issuer_url=oidc_config.issuer_url,
            client_id=oidc_config.client_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        emit_audit_event(
            AuditAction.OIDC_LOGIN_FAILED,
            tenant_id=tenant_id,
            resource_type="OIDCSession",
            outcome=AuditOutcome.FAILURE,
            details={"reason": "token_exchange_failed", "error_code": "OIDC_TOKEN_EXCHANGE_ERROR", "error": "OIDC token verification failed"},
        )
        logger.warning("OIDC token verification failed: %s", exc)
        raise HTTPException(
            status_code=502, detail="OIDC token verification failed"
        ) from exc

    # Validate nonce — always required; a missing nonce is treated as a mismatch.
    # Constant-time comparison prevents timing-based oracle attacks.
    import hmac

    token_nonce = claims.get("nonce") or ""
    if not hmac.compare_digest(str(token_nonce), str(nonce)):
        emit_audit_event(
            AuditAction.OIDC_LOGIN_FAILED,
            tenant_id=tenant_id,
            resource_type="OIDCSession",
            outcome=AuditOutcome.FAILURE,
            details={"reason": "nonce_mismatch"},
        )
        raise ValidationError(message = "OIDC nonce mismatch")

    # Map claims to role
    email = claims.get("email", "")
    mapped_role = map_role_from_claims(
        claims,
        claim_mapping=oidc_config.claim_mapping,
        default_role=oidc_config.default_role,
    )

    # Ensure mapped role is valid
    try:
        role_enum = Role(mapped_role)
    except ValueError:
        role_enum = (
            Role(oidc_config.default_role)
            if oidc_config.default_role in Role._value2member_map_
            else Role.READ_ONLY
        )
        mapped_role = role_enum.value

    # Find or auto-provision user
    user = await _get_user_by_email(db, tenant_id, email)
    if user is None:
        if oidc_config.auto_provision_users:
            user = User(
                tenant_id=tenant_id,
                email=email,
                role=mapped_role,
                status="active",
                display_name=claims.get("name") or claims.get("preferred_username"),
                hashed_password=None,
            )
            db.add(user)
            await db.flush()
        else:
            emit_audit_event(
                AuditAction.OIDC_LOGIN_FAILED,
                tenant_id=tenant_id,
                resource_type="User",
                outcome=AuditOutcome.FAILURE,
                details={"reason": "user_not_found", "email": email},
            )
            raise AuthorizationError(message = "User not found and auto-provisioning is disabled")
    else:
        # Update role if claim mapping changed (optional behaviour)
        if user.role != mapped_role:
            user.role = mapped_role
        user.last_login_at = datetime.now(UTC)


    # Issue internal JWT
    access_token = encode_jwt(
        tenant_id=tenant_id,
        user_id=str(user.id),
        roles=[user.role],
        extra_claims={"jti": secrets.token_urlsafe(16)},
        expires_in_seconds=3600,
    )
    csrf_token = issue_csrf_token()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=3600,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="strict",
        max_age=3600,
        path="/",
    )

    emit_audit_event(
        AuditAction.OIDC_LOGIN,
        tenant_id=tenant_id,
        user_id=str(user.id),
        resource_type="User",
        resource_id=str(user.id),
        outcome=AuditOutcome.SUCCESS,
        details={"provider": oidc_config.provider_name, "email": email},
    )

    # Token is delivered via the httpOnly cookie set above.
    # The JSON body contains only non-secret metadata for UI rendering.
    return oidc_callbackResult.model_validate({
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": str(user.id),
        "email": email,
        "role": user.role,
    })


@router.get("/{tenant_slug}/metadata")
async def oidc_metadata(
    tenant_slug: str,
    db: AsyncSession = Depends(get_db_from_context),
) -> dict[str, Any]:
    """Return non-sensitive OIDC configuration for a tenant."""
    tenant = await _get_tenant_by_slug(db, tenant_slug)
    if tenant is None:
        raise NotFoundError(message = "Tenant not found")

    raw_config = OIDCProviderConfig.from_settings(tenant.settings or {})
    if raw_config is None:
        raise ValidationError(message = "OIDC is not configured for this tenant")

    # Apply provider-specific presets so metadata reflects resolved values
    oidc_config = resolve_oidc_config(raw_config)

    return oidc_metadataResult.model_validate({
        "provider_name": oidc_config.provider_name,
        "issuer_url": oidc_config.issuer_url,
        "scopes": oidc_config.scopes,
        "claim_mapping_keys": list(oidc_config.claim_mapping.keys()),
        "default_role": oidc_config.default_role,
        "auto_provision_users": oidc_config.auto_provision_users,
        "enabled": oidc_config.enabled,
    })



# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def auth_refresh(
    response: Response,
    vf_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    _csrf_ok: None = Depends(validate_double_submit),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    """Rotate the session cookie and return updated non-secret metadata.

    Verifies the existing ``vf_session`` httpOnly cookie, issues a fresh JWT
    with a new expiry, and replaces the cookie.  Returns the same non-secret
    metadata shape as the OIDC callback so the frontend can update its
    sessionStorage.

    Returns 401 if the cookie is absent, expired, or invalid.
    """
    from fastapi import HTTPException
    from value_fabric.shared.identity.jwt import decode_jwt, encode_jwt

    if not vf_session:
        raise AuthenticationError(message = "No active session")

    claims = decode_jwt(vf_session)
    if claims is None:
        raise AuthenticationError(message = "Invalid or expired session")

    # Re-fetch user to pick up any role changes since last login
    from uuid import UUID

    from sqlalchemy import select

    try:
        tenant_id = UUID(str(claims.tenant_id))
        user_id = UUID(str(claims.sub))
    except (ValueError, TypeError):
        raise AuthenticationError(message = "Invalid session claims")

    user_result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None or user.status != "active":
        raise AuthenticationError(message = "User not found or inactive")

    new_token = encode_jwt(
        tenant_id=tenant_id,
        user_id=str(user.id),
        roles=[user.role],
        extra_claims={"jti": secrets.token_urlsafe(16)},
        expires_in_seconds=3600,
    )
    csrf_token = issue_csrf_token()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=new_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=3600,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="strict",
        max_age=3600,
        path="/",
    )

    return refresh_result.model_validate({
        "token_type": "Bearer",
        "expires_in": 3600,
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role,
    })


@router.post("/logout")
async def auth_logout(
    response: Response,
    _csrf_ok: None = Depends(validate_double_submit),
) -> dict:
    """Expire the session and CSRF cookies.

    Sets both cookies to Max-Age=0 so the browser removes them immediately.
    Safe to call even when no session exists.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=0,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value="",
        httponly=False,
        secure=True,
        samesite="strict",
        max_age=0,
        path="/",
    )
    return {"detail": "Logged out"}
