from __future__ import annotations

from layer4_agents.observability import Layer4EventContext


def test_layer4_event_context_requires_observability_fields():
    ctx = Layer4EventContext(
        request_id="req",
        trace_id="trace",
        tenant_id="tenant",
        workflow_id="workflow",
        run_id="run",
        provider_name="provider",
    )
    assert ctx.request_id
    assert ctx.trace_id
    assert ctx.tenant_id
    assert ctx.workflow_id
    assert ctx.run_id
    assert ctx.provider_name
