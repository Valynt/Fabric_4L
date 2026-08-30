"""Obligation handling for allowed decisions.

An authorization decision's obligations are mandatory downstream steps that
must be satisfied before the decision is honored (e.g. persist the audit record,
apply an external mask, enforce dual control). This module centralizes the
registry so enforcement points can declare and validate obligations exactly once.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .models import AuthzDecision, Obligation

# name -> async handler(request_context, decision). A handler returning False
# means the obligation could not be satisfied and the call must fail closed.
ObligationHandler = Callable[[Any, AuthzDecision], Awaitable[bool]]

_REGISTRY: dict[str, ObligationHandler] = {}


def register_obligation(kind: str, handler: ObligationHandler) -> None:
    _REGISTRY[kind] = handler


def get_obligation(kind: str) -> ObligationHandler | None:
    return _REGISTRY.get(kind)


def has_obligation(kind: str) -> bool:
    return kind in _REGISTRY


async def honor(decision: AuthzDecision, request_context: Any = None) -> bool:
    """Honor all obligations attached to an allowed decision.

    Returns True only if every obligation handler reports success. If any is
    missing or returns False, the decision is NOT honored (fail closed) and the
    protected write is refused.
    """
    if not decision.allowed:
        # Nothing to honor on a deny.
        return False
    for obligation in decision.obligations:
        handler = _REGISTRY.get(obligation.kind)
        if handler is None:
            # An unknown obligation must not silently pass.
            return False
        try:
            ok = await handler(request_context, decision)
        except Exception:
            return False
        if not ok:
            return False
    return True