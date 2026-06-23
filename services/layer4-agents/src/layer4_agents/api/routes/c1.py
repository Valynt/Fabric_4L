from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

"""C1 streaming proxy route.

Proxies requests to the Thesys C1 API so the API key never leaves the
server.  The frontend sends ``POST /v1/c1/stream`` with the chat messages
and business-case context; this route forwards them to the Thesys embed
endpoint and relays the SSE response back to the browser.
"""


import json
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration – loaded once at import time
# ---------------------------------------------------------------------------

THESYS_API_KEY: str = os.getenv("THESYS_API_KEY", "")
THESYS_BASE_URL: str = os.getenv("THESYS_BASE_URL", "https://api.thesys.dev/v1/embed")

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
    _ctx: RequestContext = Depends(require_authenticated),
) -> StreamingResponse:
    """Proxy a streaming request to the Thesys C1 API.

    The server attaches the ``THESYS_API_KEY`` so the secret is never
    exposed to the browser.  The response is forwarded as-is in SSE
    format (``text/event-stream``).
    """
    if not THESYS_API_KEY:
        raise ServiceUnavailableError(message = "Thesys C1 integration is not configured. Set THESYS_API_KEY.")

    payload = {
        "messages": [m.model_dump() for m in request.messages],
        "stream": True,
        "metadata": {
            "business_case_id": request.business_case_id,
            **(request.business_case_data or {}),
        },
    }

    async def _relay() -> Any:
        """Stream chunks from Thesys and re-emit as SSE."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    THESYS_BASE_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {THESYS_API_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as upstream:
                    if upstream.status_code != 200:
                        body = await upstream.aread()
                        error_msg = body.decode("utf-8", errors="replace")
                        logger.warning(
                            "Thesys API returned %s: %s",
                            upstream.status_code,
                            error_msg[:500],
                        )
                        yield f"data: {json.dumps({'type': 'error', 'error': f'Thesys API error ({upstream.status_code})'})}\n\n"
                        return

                    async for line in upstream.aiter_lines():
                        if not line.strip():
                            continue
                        # Forward the SSE line as-is
                        yield f"{line}\n\n"

            # Signal stream completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except httpx.ConnectError:
            logger.exception("Failed to connect to Thesys API at %s", THESYS_BASE_URL)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Unable to reach Thesys API'})}\n\n"
        except httpx.TimeoutException:
            logger.exception("Thesys API request timed out")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Thesys API request timed out'})}\n\n"
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected error while streaming from Thesys API")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Internal streaming error'})}\n\n"

    return StreamingResponse(
        _relay(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
