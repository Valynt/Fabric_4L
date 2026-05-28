from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass

CANONICAL_TRACE_HEADER = "X-Request-ID"
TRACE_HEADER_ALIASES: tuple[str, ...] = (
    "X-Correlation-ID",
    "X-Trace-ID",
    "X-Trace-Id",
)
ALL_TRACE_HEADERS: tuple[str, ...] = (CANONICAL_TRACE_HEADER, *TRACE_HEADER_ALIASES)
MAX_TRACE_ID_LENGTH = 64
_VALID_TRACE_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]+$")


@dataclass(frozen=True)
class CanonicalTraceContext:
    trace_id: str
    source_header: str | None


def sanitize_trace_id(value: str | None, *, generator: Callable | None = None) -> str:
    if not value:
        return _new_trace_id(generator)
    trimmed = value[:MAX_TRACE_ID_LENGTH]
    if not _VALID_TRACE_PATTERN.match(trimmed):
        return _new_trace_id(generator)
    return trimmed


def resolve_trace_context(headers, *, generator: Callable | None = None) -> CanonicalTraceContext:
    for header in ALL_TRACE_HEADERS:
        incoming = headers.get(header)
        if incoming:
            return CanonicalTraceContext(trace_id=sanitize_trace_id(incoming, generator=generator), source_header=header)
    return CanonicalTraceContext(trace_id=_new_trace_id(generator), source_header=None)


def canonical_trace_headers(trace_id: str) -> dict[str, str]:
    return {header: trace_id for header in ALL_TRACE_HEADERS}


def _new_trace_id(generator: Callable | None) -> str:
    if generator is not None:
        generated = str(generator())
        # If generator already includes req_ prefix, use as-is
        if generated.startswith("req_"):
            return generated
        return f"req_{generated[:16]}"
    return f"req_{uuid.uuid4().hex[:16]}"
