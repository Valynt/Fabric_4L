"""Shared HTTP client with connection pool limits (P2-003)."""
from __future__ import annotations
import httpx
from contextlib import asynccontextmanager
from typing import Optional

DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0, read=10.0, write=10.0)

@asynccontextmanager
async def get_http_client(limits=None, timeout=None, base_url=None, headers=None):
    client = httpx.AsyncClient(limits=limits or DEFAULT_LIMITS, timeout=timeout or DEFAULT_TIMEOUT,
                               base_url=base_url, headers=headers)
    try:
        yield client
    finally:
        await client.aclose()

def make_http_client(limits=None, timeout=None, base_url=None, headers=None):
    return httpx.AsyncClient(limits=limits or DEFAULT_LIMITS, timeout=timeout or DEFAULT_TIMEOUT,
                             base_url=base_url, headers=headers)
