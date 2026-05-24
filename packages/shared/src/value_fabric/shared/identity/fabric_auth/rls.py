"""Row-level security helpers driven by the verified AuthContext.

Phase 1 supports PostgreSQL RLS via ``set_config('app.tenant_id', ..., true)``.
The session-scoped GUC is read by the layer's RLS policies; the value is
sourced *only* from the verified envelope, never from a header or body.
"""
from __future__ import annotations

import logging
from typing import Any

from .context import AuthContext

logger = logging.getLogger(__name__)

TENANT_GUC = "app.tenant_id"
USER_GUC = "app.user_id"


def apply_tenant_rls(session: Any, auth: AuthContext) -> None:
    """Set ``app.tenant_id`` / ``app.user_id`` on a SQLAlchemy session.

    The function is intentionally tolerant about session shape so it
    can be reused across services that wrap SQLAlchemy differently.
    Pass either a ``Session`` or any object exposing ``execute(text(...))``.

    Raises:
        TypeError: if ``session`` does not expose ``execute``.
    """
    execute = getattr(session, "execute", None)
    if execute is None or not callable(execute):
        raise TypeError("session must expose a callable execute(...)")

    try:
        from sqlalchemy import text  # local import; not all callers use SQLA
    except ImportError:  # pragma: no cover - exercised only in non-SQLA envs
        logger.warning("apply_tenant_rls: SQLAlchemy not installed; skipping")
        return

    # ``true`` makes the setting transaction-local in PG; safe per request.
    execute(
        text("SELECT set_config(:k, :v, true)"),
        {"k": TENANT_GUC, "v": auth.tenant_id},
    )
    execute(
        text("SELECT set_config(:k, :v, true)"),
        {"k": USER_GUC, "v": auth.user_id},
    )
