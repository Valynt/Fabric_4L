import base64
import binascii
import hashlib
import logging
import secrets
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.database import db
from app.models.schemas import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brute-force / account lockout constants (F-05)
# ---------------------------------------------------------------------------
_MAX_FAILED_ATTEMPTS = 10       # lock after this many consecutive failures
_LOCKOUT_DURATION_MINUTES = 15

# ---------------------------------------------------------------------------
# Password security policy
# ---------------------------------------------------------------------------
# bcrypt has a 72-byte password limit. We explicitly reject passwords longer
# than this limit to prevent silent truncation vulnerabilities.
MAX_BCRYPT_PASSWORD_BYTES = 72

# Use bcrypt in production, but allow fallback to a test-only scheme in test environments
# Lazy initialization to allow env var to be set before first use
_pwd_context: CryptContext | None = None
_pwd_context_lock = threading.Lock()

def get_pwd_context() -> CryptContext:
    """Get the password hashing context with thread-safe lazy initialization.
    
    In production-like environments, bcrypt is always used. In test environments,
    USE_BCRYPT=false can be set to use sha256_crypt for faster test execution.
    
    Raises:
        RuntimeError: If USE_BCRYPT=false is set in a production-like environment.
    """
    global _pwd_context
    if _pwd_context is None:
        with _pwd_context_lock:
            if _pwd_context is None:  # Double-checked locking
                import os as _os
                _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"

                # Production guard: prevent USE_BCRYPT=false in production-like environments
                env = _os.getenv("ENVIRONMENT", "development").lower()
                production_like_envs = {"production", "prod", "staging", "stage", "preprod", "pre-production"}
                if env in production_like_envs and not _use_bcrypt:
                    raise RuntimeError(
                        "USE_BCRYPT=false is not allowed in production-like environments. "
                        "This would disable secure password hashing and expose the application to "
                        "password cracking attacks. Set USE_BCRYPT=true or unset the variable."
                    )

                _pwd_context = CryptContext(
                    schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"],
                    deprecated="auto"
                )
    return _pwd_context

# Backward compatibility: pwd_context as a callable
pwd_context = get_pwd_context

_bearer_scheme = HTTPBearer(auto_error=False)

_SESSION_COOKIE = "vf_session"
_DEFAULT_JWT_ISSUER = "value-fabric-internal"
_DEFAULT_JWT_AUDIENCE = "value-fabric-services"
_AUTH_REQUIRED = "authentication_required"
class PasswordTooLongError(ValueError):
    """Raised when a password exceeds the bcrypt 72-byte limit."""
    def __init__(self, length: int, max_length: int = MAX_BCRYPT_PASSWORD_BYTES):
        super().__init__(
            f"Password exceeds {max_length} byte limit (got {length} bytes). "
            f"Passwords longer than {max_length} bytes cannot be securely hashed with bcrypt."
        )
        self.length = length
        self.max_length = max_length



class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    jti: str
    exp: datetime | None = None
    iat: datetime | None = None
    nbf: datetime | None = None
    iss: str
    aud: str | list[str]
    impersonated_by: str | None = None
    impersonation_session_id: str | None = None
    impersonation_reason: str | None = None
    account_id: str | None = None
    account_ids: list[str] = Field(default_factory=list)




def _revocation_key(tenant_id: str, jti: str) -> str:
    return f"auth:revoked:{tenant_id}:{jti}"


def revoke_token(*, tenant_id: str, jti: str, fingerprint_hash: str, expires_at_ts: int) -> None:
    """Add a token to the revocation denylist with TTL.

    Uses Redis when available; falls back to in-memory only in dev/test.
    """
    key = _revocation_key(tenant_id, jti)
    try:
        from app.core.redis_client import get_redis_client
        r = get_redis_client()
        if r is not None:
            ttl = max(0, expires_at_ts - int(datetime.now(UTC).timestamp()))
            if ttl > 0:
                r.setex(key, ttl, fingerprint_hash)
            return
    except Exception as exc:
        logger.warning("Redis revoke_token failed, falling back to memory: %s", exc)

    # Fallback in-memory (dev/test only)
    _REVOKED_TOKEN_STORE[key] = (fingerprint_hash, expires_at_ts)


def is_token_revoked(tenant_id: str, jti: str, fingerprint_hash: str) -> bool:
    """Check if a token is in the revocation denylist.

    Uses Redis when available; falls back to in-memory only in dev/test.
    """
    key = _revocation_key(tenant_id, jti)
    try:
        from app.core.redis_client import get_redis_client
        r = get_redis_client()
        if r is not None:
            stored = r.get(key)
            if stored is None:
                return False
            if isinstance(stored, bytes):
                stored = stored.decode("utf-8")
            return stored == fingerprint_hash
    except Exception as exc:
        logger.warning("Redis is_token_revoked failed, falling back to memory: %s", exc)

    # Fallback in-memory (dev/test only)
    record = _REVOKED_TOKEN_STORE.get(key)
    if record is None:
        return False
    now_ts = int(datetime.now(UTC).timestamp())
    if record[1] <= now_ts:
        _REVOKED_TOKEN_STORE.pop(key, None)
        return False
    return record[0] == fingerprint_hash


# Dev/test fallback store (never used in production when Redis is configured)
_REVOKED_TOKEN_STORE: dict[str, tuple[str, int]] = {}


def _auth_error(status_code: int, *, error_code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": _AUTH_REQUIRED,
            "error_code": error_code,
            "message": message,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


# Top-20 most common passwords — checked server-side to prevent trivially weak credentials.
# NIST 800-63B §5.1.1 requires checking against known-compromised passwords.
_COMMON_PASSWORDS: frozenset[str] = frozenset({
    "password", "password1", "password12", "password123", "password1234",
    "password12345", "password123456", "password1234567", "password12345678",
    "123456", "12345678", "123456789", "1234567890", "12345678901",
    "qwerty", "qwerty123", "qwerty1234", "abc123", "letmein", "monkey",
    "dragon", "master", "sunshine", "princess", "welcome", "shadow",
    "superman", "michael", "football", "iloveyou", "admin", "login",
    "passw0rd", "p@ssword", "p@ssw0rd", "trustno1", "hello", "charlie",
    "changeme", "changeme1", "changeme123", "iloveyou1", "iloveyou123",
})

_MIN_PASSWORD_LENGTH = 12


def validate_password_strength(password: str) -> None:
    """Enforce minimum password requirements server-side.

    Raises ValueError with a stable error code on failure so callers can
    return HTTP 422 with a consistent WEAK_PASSWORD code.

    Requirements (NIST 800-63B §5.1.1 baseline):
    - Minimum 12 characters
    - Not in the common-password blocklist
    """
    if len(password) < _MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"WEAK_PASSWORD: password must be at least {_MIN_PASSWORD_LENGTH} characters"
        )
    if password.lower() in _COMMON_PASSWORDS:
        raise ValueError(
            "WEAK_PASSWORD: password is too common — choose a less predictable password"
        )


def is_account_locked(user: "User") -> bool:
    """Return True if the account is currently locked due to failed login attempts."""
    if user.locked_until is None:
        return False
    try:
        locked_until = datetime.fromisoformat(user.locked_until)
        return datetime.now(UTC) < locked_until
    except (ValueError, TypeError):
        return False


def record_failed_login(user: "User") -> "User":
    """Increment failed attempt counter and lock the account if threshold is reached.

    Returns an updated User instance (caller must persist it).
    """
    new_attempts = user.failed_login_attempts + 1
    locked_until = None
    if new_attempts >= _MAX_FAILED_ATTEMPTS:
        locked_until = (datetime.now(UTC) + timedelta(minutes=_LOCKOUT_DURATION_MINUTES)).isoformat()
    return user.model_copy(update={
        "failed_login_attempts": new_attempts,
        "locked_until": locked_until,
    })


def record_successful_login(user: "User") -> "User":
    """Reset failed attempt counter and lockout on successful authentication.

    Returns an updated User instance (caller must persist it).
    """
    return user.model_copy(update={
        "failed_login_attempts": 0,
        "locked_until": None,
    })


def verify_password(plain: str, hashed: str) -> bool:
    # sha256$ prefixed hashes are insecure legacy values — reject them unconditionally.
    # Any account with such a hash must go through password reset before logging in.
    if hashed.startswith("sha256$"):
        return False
    try:
        return get_pwd_context().verify(plain, hashed)
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a password using the configured password hashing scheme.
    
    Enforces the bcrypt 72-byte password limit when bcrypt is enabled.
    Raises PasswordTooLongError if the password exceeds the limit.
    
    Args:
        password: The plain-text password to hash.
        
    Returns:
        The hashed password.
        
    Raises:
        PasswordTooLongError: If the password exceeds MAX_BCRYPT_PASSWORD_BYTES.
    """
    # Enforce bcrypt 72-byte limit when bcrypt is the active scheme
    import os as _os
    _use_bcrypt = _os.getenv("USE_BCRYPT", "true").lower() == "true"
    if _use_bcrypt:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
            raise PasswordTooLongError(len(password_bytes))

    return get_pwd_context().hash(password)


def create_access_token(
    subject: str,
    tenant_id: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    issued_at = datetime.now(UTC)
    if expires_delta:
        expire = issued_at + expires_delta
    else:
        expire = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    iat_ts = int(issued_at.timestamp())
    token_jti = secrets.token_urlsafe(16)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "jti": token_jti,
        "iat": iat_ts,
        "nbf": iat_ts,
        "exp": int(expire.timestamp()),
        "iss": settings.jwt_issuer or _DEFAULT_JWT_ISSUER,
        "aud": settings.jwt_audience or _DEFAULT_JWT_AUDIENCE,
    }
    if extra_claims:
        payload.update(extra_claims)
    return pyjwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


class TokenExpiredError(ValueError):
    """Raised when a JWT has expired. Translated to HTTP 401 by require_authenticated."""


def _is_canonical_base64url_segment(segment: str) -> bool:
    """Reject non-canonical JWT segments before cryptographic verification.

    Some base64url decoders ignore unused trailing bits in unpadded encodings,
    which can make a mutated compact-JWS segment decode to the same bytes.  The
    API treats such alternate encodings as malformed so tampering is fail-closed
    and auditable before business routing occurs.
    """
    if not segment or "=" in segment:
        return False
    try:
        padded = segment + "=" * (-len(segment) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError, ValueError):
        return False
    canonical = base64.urlsafe_b64encode(decoded).decode("ascii").rstrip("=")
    return canonical == segment


def _has_canonical_compact_jws_encoding(token: str) -> bool:
    segments = token.split(".")
    return len(segments) == 3 and all(
        _is_canonical_base64url_segment(segment) for segment in segments
    )


def decode_token(token: str) -> TokenPayload | None:
    """Decode and validate a JWT.

    Returns a TokenPayload on success, None for invalid/malformed tokens.
    Raises TokenExpiredError for expired tokens so callers can surface a
    distinct error message without coupling this function to HTTP concerns.
    """
    settings = get_settings()
    if not _has_canonical_compact_jws_encoding(token):
        return None
    try:
        header = pyjwt.get_unverified_header(token)
        header_alg = header.get("alg")
        if not isinstance(header_alg, str) or not header_alg.strip():
            return None
        if header_alg.upper() != settings.algorithm.upper():
            return None
        # PyJWT option keys differ from python-jose:
        #   require=[...] replaces require_sub/require_exp/etc.
        #   verify_* options are set via options dict
        data = pyjwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": ["sub", "exp", "iat", "nbf"],
                "verify_aud": True,
                "verify_iss": True,
                "verify_iat": True,
                "verify_nbf": True,
                "verify_exp": True,
            },
        )
        if not isinstance(data.get("sub"), str) or not data["sub"].strip():
            return None
        tenant_id = data["tenant_id"] if "tenant_id" in data else None
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            return None
        jti = data.get("jti")
        if not isinstance(jti, str) or not jti.strip():
            return None
        if not isinstance(data.get("iss"), str) or not data["iss"].strip():
            return None
        if data.get("aud") in (None, "", []):
            return None
        return TokenPayload(
            sub=data["sub"].strip(),
            tenant_id=tenant_id.strip(),
            jti=jti.strip(),
            exp=data.get("exp"),
            iat=data.get("iat"),
            nbf=data.get("nbf"),
            iss=data["iss"],
            aud=data["aud"],
            account_id=data.get("account_id"),
            account_ids=[str(v) for v in data.get("account_ids", []) if isinstance(v, str)],
            impersonated_by=data.get("impersonated_by"),
            impersonation_session_id=data.get("impersonation_session_id"),
            impersonation_reason=data.get("impersonation_reason"),
        )
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except InvalidTokenError:
        return None


def _extract_token(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None,
    cookie: str | None,
) -> str | None:
    """Return the raw JWT from Bearer header or session cookie, in that order."""
    if bearer and bearer.credentials:
        return bearer.credentials
    if cookie:
        return cookie
    return None


def require_authenticated(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    vf_session: str | None = Cookie(default=None, alias=_SESSION_COOKIE),
) -> TokenPayload:
    """FastAPI dependency: require a valid JWT from Bearer header or session cookie.

    Raises HTTP 401 if no token is present or the token is invalid/expired.
    """
    raw = _extract_token(request, bearer, vf_session)
    if not raw:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_REQUIRED",
            message="Authentication required.",
        )
    try:
        payload = decode_token(raw)
    except TokenExpiredError:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_EXPIRED",
            message="Token has expired.",
        )
    if payload is None:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_INVALID_TOKEN",
            message="Invalid token.",
        )
    token_fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if is_token_revoked(payload.tenant_id, payload.jti, token_fingerprint):
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_TOKEN_REVOKED",
            message="Token has been revoked.",
        )
    return payload


async def get_current_user(
    auth: TokenPayload = Depends(require_authenticated),
) -> User:
    """Resolve the authenticated user from the database using the JWT payload."""
    user = db.users.get(auth.sub, tenant_id=auth.tenant_id)
    if user is None:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_USER_NOT_FOUND",
            message="Authenticated user was not found.",
        )
    # Reject deactivated users even if they hold a valid JWT (F-09).
    # Deactivation must take effect immediately — not at token expiry.
    if user.status == "deactivated":
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_ACCOUNT_DEACTIVATED",
            message="This account has been deactivated.",
        )
    return user
