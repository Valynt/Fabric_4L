from __future__ import annotations

"""C1 streaming proxy route.

Proxies requests to the Thesys C1 API via ThesysProvider with request
authentication, tenant attribution, prompt injection scanning, and error handling.
The frontend sends ``POST /v1/c1/stream`` with the chat messages
and business-case context; this route forwards them and relays the SSE response
back to the browser.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...services.thesys_provider import ThesysProvider

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class C1Message(BaseModel):
    """Single message in the C1 conversation."""

    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message text content")


class C1StreamRequest(BaseModel):
    """Request body accepted by ``POST /v1/c1/stream``."""

    messages: list[C1Message] = Field(..., min_length=1)
    business_case_id: str = Field(..., min_length=1)
    business_case_data: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Streaming proxy
# ---------------------------------------------------------------------------


@router.post("/c1/stream")
async def stream_c1(
    request: C1StreamRequest,
    ctx: RequestContext = Depends(require_authenticated),
) -> StreamingResponse:
    """Proxy a streaming request to the Thesys C1 API via ThesysProvider.

    The server attaches the ``THESYS_API_KEY`` so the secret is never
    exposed to the browser. The response is forwarded as-is in SSE
    format (``text/event-stream``).
    """
    provider = ThesysProvider()
    if not provider.is_available():
        raise ServiceUnavailableError(message="Thesys C1 integration is not configured. Set THESYS_API_KEY.")

    messages_data = [m.model_dump() for m in request.messages]
    metadata = {
        "business_case_id": request.business_case_id,
        **(request.business_case_data or {}),
    }

    return StreamingResponse(
        provider.stream_c1_chunks(
            messages=messages_data,
            metadata=metadata,
            tenant_id=getattr(ctx, "tenant_id", None) or "unknown",
            user_id=getattr(ctx, "user_id", None) or "unknown",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
