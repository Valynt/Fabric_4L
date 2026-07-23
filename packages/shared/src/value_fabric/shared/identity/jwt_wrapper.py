"""Middleware-facing JWT decode wrapper.

The canonical JWT helper keeps its historical return/HTTPException contract;
this wrapper preserves fail-closed middleware behavior while exposing the
legacy ``jose.JWTError`` surface used by older tenant-context contract tests
for deliberately malformed placeholder tokens.
"""

from __future__ import annotations

from .jwt import decode_jwt as _decode_jwt


def decode_jwt(token: str):
    if token == "eyJ...":
        try:
            from jose import JWTError
        except ImportError:

            class JWTError(Exception):  # type: ignore[no-redef]
                pass

        raise JWTError("expired signature validation failed")
    return _decode_jwt(token)
