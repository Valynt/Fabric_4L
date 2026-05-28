from __future__ import annotations

"""Observability schema invariants for value_fabric.layer4."""


import logging

from value_fabric.layer4.observability import Layer4EventContext, Layer4LifecycleLogger


def test_layer4_lifecycle_schema_fields_present(caplog: object) -> None:
    logger = logging.getLogger("test.layer4.lifecycle")
    wrapper = Layer4LifecycleLogger(logger)
    ctx = Layer4EventContext(
        request_id="req-1",
        trace_id="trace-1",
        tenant_id="tenant-1",
        workflow_id="wf-1",
        run_id="run-1",
        provider_name="langgraph",
        checkpoint_id="cp-1",
    )
    stages = [
        "start", "checkpoint", "resume", "tool-call",
        "tool-result", "failure", "cancel", "completion",
    ]

    with caplog.at_level(logging.INFO):
        for stage in stages:
            wrapper.emit(
                stage=stage,
                context=ctx,
                error_class="RuntimeError" if stage == "failure" else None,
                error_code="E_FAIL" if stage == "failure" else None,
            )

    for rec in caplog.records:
        for field in [
            "request_id", "trace_id", "tenant_id",
            "workflow_id", "run_id", "provider_name",
        ]:
            assert hasattr(rec, field)
        if rec.event_stage == "checkpoint":
            assert rec.checkpoint_id == "cp-1"
        if rec.event_stage == "failure":
            assert rec.error_class == "RuntimeError"
            assert rec.error_code == "E_FAIL"
