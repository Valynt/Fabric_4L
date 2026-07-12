from value_fabric.shared.observability.trace_context import (
    canonical_trace_headers,
    resolve_trace_context,
)


def test_correlation_trace_header_contract():
    correlation_id = 'trace-123'
    ctx = resolve_trace_context({'X-Correlation-ID': correlation_id})
    outbound = canonical_trace_headers(ctx.trace_id)
    assert ctx.trace_id == correlation_id
    assert outbound.get('X-Request-ID') == correlation_id
