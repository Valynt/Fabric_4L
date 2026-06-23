# P1: W3C TraceContext propagation
# Replaces custom X-Request-ID with standard traceparent/tracestate headers
"""
W3C Trace Context implementation for cross-service trace propagation.

Replaces custom X-Request-ID / X-Correlation-ID with standard headers:
- traceparent: version-trace_id-parent_id-flags
- tracestate: vendor-specific context
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# W3C traceparent regex: 00-<32 hex>-<16 hex>-<2 hex>
TRACEPARENT_REGEX = re.compile(
    r"^(?P<version>[0-9a-f]{2})-"
    r"(?P<trace_id>[0-9a-f]{32})-"
    r"(?P<parent_id>[0-9a-f]{16})-"
    r"(?P<flags>[0-9a-f]{2})$"
)

VERSION = "00"
FLAGS_SAMPLED = "01"
FLAGS_UNSAMPLED = "00"


@dataclass(frozen=True)
class TraceContext:
    """Parsed W3C TraceContext."""
    trace_id: str
    parent_id: str
    flags: str
    version: str = VERSION

    @property
    def is_sampled(self) -> bool:
        return self.flags == FLAGS_SAMPLED

    def to_traceparent(self) -> str:
        return f"{self.version}-{self.trace_id}-{self.parent_id}-{self.flags}"

    def to_tracestate(self) -> str:
        return f"fabric={self.parent_id}-{self.flags}"

    @classmethod
    def from_traceparent(cls, header: str) -> Optional["TraceContext"]:
        match = TRACEPARENT_REGEX.match(header)
        if not match:
            return None
        return cls(
            trace_id=match.group("trace_id"),
            parent_id=match.group("parent_id"),
            flags=match.group("flags"),
            version=match.group("version"),
        )

    @classmethod
    def generate_new(cls) -> "TraceContext":
        """Generate a new root trace context."""
        import secrets
        trace_id = secrets.token_hex(16)
        parent_id = secrets.token_hex(8)
        return cls(trace_id=trace_id, parent_id=parent_id, flags=FLAGS_SAMPLED)


def inject_trace_context(headers: dict, context: TraceContext) -> None:
    """Inject W3C headers into request/response headers dict."""
    headers["traceparent"] = context.to_traceparent()
    headers["tracestate"] = context.to_tracestate()


def extract_trace_context(headers: dict) -> Optional[TraceContext]:
    """Extract W3C TraceContext from headers (case-insensitive)."""
    for key, value in headers.items():
        if key.lower() == "traceparent":
            return TraceContext.from_traceparent(value)
    return None
