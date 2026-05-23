from fastapi import HTTPException

from value_fabric.layer1.api.main import _UnavailableTask, _build_task_unavailable_detail
from value_fabric.shared.error_handling.handlers import http_exception_handler


class _ReqState:
    trace_id = "req_test123"


class _RequestStub:
    state = _ReqState()
    headers = {}


def test_unavailable_task_detail_uses_stable_code_message() -> None:
    detail = _build_task_unavailable_detail()

    assert detail == {
        "code": "SERVICE_UNAVAILABLE",
        "message": (
            "Background processing is temporarily unavailable. "
            "Please retry shortly or contact support if the issue persists."
        ),
    }


def test_unavailable_task_delay_does_not_expose_import_trace() -> None:
    task = _UnavailableTask("process_scraping_job", ImportError("No module named celery.app.trace"))

    try:
        task.delay("job-123")
    except HTTPException as exc:
        assert exc.status_code == 503
        assert isinstance(exc.detail, dict)
        assert "celery.app.trace" not in str(exc.detail)
        assert "ImportError" not in str(exc.detail)
    else:
        raise AssertionError("Expected HTTPException")


def test_shared_http_exception_handler_returns_consistent_envelope_shape() -> None:
    exc = HTTPException(status_code=503, detail=_build_task_unavailable_detail())

    response = __import__("asyncio").run(http_exception_handler(_RequestStub(), exc))
    payload = response.body.decode("utf-8")

    assert '"code":"SERVICE_UNAVAILABLE"' in payload
    assert '"message":"Background processing is temporarily unavailable.' in payload
    assert "celery.app.trace" not in payload
    assert "ImportError" not in payload
