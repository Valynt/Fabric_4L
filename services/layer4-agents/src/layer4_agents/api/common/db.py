from __future__ import annotations

"""Shared DB dependency helpers for API routes."""
import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ...database import _clear_local_tenant_context, get_db_from_context, get_session_factory

get_route_db = get_db_from_context


async def get_webhook_db() -> AsyncGenerator[AsyncSession, None]:
    """DB dependency for unauthenticated webhooks.

    Webhooks cannot carry a JWT tenant context, so tenant isolation is enforced
    at the application layer by the service layer using explicit tenant filters.
    The session is explicitly marked as bypass so RLS-aware session helpers
    fail closed if later reused without tenant context.
    """
    factory = get_session_factory()
    async with factory() as session:
        await _clear_local_tenant_context(session)
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise
