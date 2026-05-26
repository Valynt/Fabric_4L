import logging

from src.observability import Layer4LogContext, Layer4LogContractLogger


def _assert_required_fields(record: logging.LogRecord) -> None:
    for field in ("workflow_id", "run_id", "tenant_id", "request_id"):
        assert hasattr(record, field)
        assert getattr(record, field)


def test_log_contract_success(caplog):
    logger = Layer4LogContractLogger(logging.getLogger("test.layer4.success"))
    with caplog.at_level(logging.INFO):
        logger.emit(
            event="workflow_success",
            context=Layer4LogContext(
                workflow_id="wf-1", run_id="run-1", tenant_id="tenant-1", request_id="req-1"
            ),
        )
    rec = caplog.records[-1]
    _assert_required_fields(rec)


def test_log_contract_retry_failure_resume_and_corruption(caplog):
    logger = Layer4LogContractLogger(logging.getLogger("test.layer4.multi"))
    with caplog.at_level(logging.INFO):
        logger.emit(
            event="workflow_retry",
            context=Layer4LogContext(
                workflow_id="wf-2", run_id="run-2", tenant_id="tenant-2", request_id="req-2"
            ),
            reason="timeout",
            level="warning",
        )
        logger.emit(
            event="workflow_failure",
            context=Layer4LogContext(
                workflow_id="wf-3", run_id="run-3", tenant_id="tenant-3", request_id="req-3"
            ),
            error_class="RuntimeError",
            level="error",
        )
        logger.emit(
            event="workflow_resume",
            context=Layer4LogContext(
                workflow_id="wf-4",
                run_id="run-4",
                tenant_id="tenant-4",
                request_id="req-4",
                checkpoint_id="chk-1",
            ),
        )
        logger.emit(
            event="checkpoint_corruption",
            context=Layer4LogContext(
                workflow_id="wf-5",
                run_id="run-5",
                tenant_id="tenant-5",
                request_id="req-5",
                checkpoint_id="chk-2",
            ),
            reason="replay_conflict",
            level="warning",
        )

    assert len(caplog.records) >= 4
    for rec in caplog.records[-4:]:
        _assert_required_fields(rec)
