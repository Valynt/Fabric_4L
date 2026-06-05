from __future__ import annotations

"""WebSocket authentication utilities.

Canonical auth transport: Sec-WebSocket-Protocol bearer format.
  Protocol subprotocols: ['base64url.bearer.authorization', '<jwt>']
"""


import logging

logger = logging.getLogger(__name__)

# Canonical subprotocol identifier per RFC 6455 / IANA registry convention.
_BEARER_SUBPROTOCOL = "base64url.bearer.authorization"

try:
    from value_fabric.shared.identity.jwt import decode_jwt

    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False
    decode_jwt = None  # type: ignore[assignment]

_TOKEN_EXCEPTION_CODE_MAP: dict[str, str] = {
    "ExpiredSignatureError": "AUTH_TOKEN_EXPIRED",
    "InvalidTokenError": "AUTH_TOKEN_INVALID",
    "DecodeError": "AUTH_TOKEN_DECODE_FAILED",
    "InvalidSignatureError": "AUTH_TOKEN_SIGNATURE_INVALID",
}


class WebSocketAuthError(Exception):
    """Raised when WebSocket authentication fails."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def extract_token_from_protocol_header(protocol_header: str) -> str | None:
    """Parse the Sec-WebSocket-Protocol header for a bearer token.

    Expected format (two subprotocols, comma-separated):
        base64url.bearer.authorization, <jwt>

    Returns the raw JWT string, or None if the header is absent or
    does not follow the canonical format.
    """
    if not protocol_header:
        return None

    parts = [p.strip() for p in protocol_header.split(",")]
    if len(parts) >= 2 and parts[0].lower() == _BEARER_SUBPROTOCOL:
        token = parts[1]
        return token if token else None

    return None


def decode_ws_token(token: str | None) -> tuple[str, str]:
    """Decode a JWT and return (tenant_id, user_id).

    Args:
        token: Raw JWT string.

    Returns:
        Tuple of (tenant_id, user_id).

    Raises:
        WebSocketAuthError: On any auth failure (missing, invalid, expired).
    """
    if token is None or not token.strip():
        raise WebSocketAuthError("AUTH_TOKEN_MISSING")

    if not _JWT_AVAILABLE:
        raise WebSocketAuthError("AUTH_JWT_UNAVAILABLE")

    try:
        payload = decode_jwt(token)  # type: ignore[misc]
        if not payload:
            raise WebSocketAuthError("AUTH_INVALID_PAYLOAD")

        if isinstance(payload, dict):
            tenant_id = payload["tenant_id"] if "tenant_id" in payload else None
            user_id = (
                payload["sub"]
                if "sub" in payload
                else payload["user_id"] if "user_id" in payload else None
            )
        else:
            tenant_id = getattr(payload, "tenant_id", None)
            user_id = getattr(payload, "sub", None) or getattr(payload, "user_id", None)

        if not tenant_id or not isinstance(tenant_id, str):
            raise WebSocketAuthError("AUTH_TENANT_CLAIM_INVALID")
        if not user_id or not isinstance(user_id, str):
            raise WebSocketAuthError("AUTH_USER_CLAIM_INVALID")

        return tenant_id, user_id

    except WebSocketAuthError:
        raise
    except Exception as exc:
        error_code = _TOKEN_EXCEPTION_CODE_MAP.get(
            exc.__class__.__name__,
            "AUTH_TOKEN_DECODE_FAILED",
        )
        logger.warning(
            "WebSocket JWT decode failed: %s",
            error_code,
            extra={"auth_code": error_code},
        )
        raise WebSocketAuthError(error_code) from exc
