from __future__ import annotations

import hmac
import secrets

from fastapi import Cookie, Header
from value_fabric.shared.error_handling.exceptions import AuthorizationError

CSRF_COOKIE_NAME = "vf_csrf_token"
SESSION_COOKIE_NAME = "vf_session"


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_double_submit(
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    if not csrf_cookie or not csrf_header:
        raise AuthorizationError(message = "CSRF token missing")
    if not hmac.compare_digest(csrf_cookie, csrf_header):
        raise AuthorizationError(message = "CSRF token mismatch")
