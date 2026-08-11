"""Guard: L1 Celery tasks that exhaust retries are routed to the layer1_dlq
dead-letter queue and durably recorded (P0-02 / V1-QUEUE-001; refs #1258).

The layer1_dlq queue was declared in Celery config (task_queues) but nothing
routed to it: the Redis transport has no broker-side dead-lettering, so a task
failing its final retry vanished with only a log line. Now a task_failure
signal handler republishes exhausted tasks to layer1_dlq, and the DLQ consumer
persists a JobError (TASK_DEAD_LETTERED, retryable=False) when the failure
envelope carries tenant_id + job_id.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.celery, pytest.mark.reliability, pytest.mark.p0, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
L1_TASKS = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py"
L1_DLQ = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/shared/dlq.py"
L1_METRICS = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/metrics/prometheus_metrics.py"


def _load_dlq_module():
    # Load dlq.py directly by path: it is deliberately hermetic (stdlib only)
    # so the routing policy is testable without the Celery/HTTP/Playwright
    # service stack that tasks.py pulls in.
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("l1_dlq_under_test", L1_DLQ)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestDlqRoutingWiring:
    def test_dlq_queue_declared_and_consumer_bound(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert '"layer1_dlq"' in text, "layer1_dlq queue must remain declared in task_queues"
        assert "queue=DLQ_QUEUE_NAME" in text, "DLQ consumer must be bound to the DLQ queue"
        assert "max_retries=0" in text, "DLQ consumer must never requeue"

    def test_task_failure_signal_connected(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert "from celery.signals import task_failure" in text
        assert "@task_failure.connect" in text

    def test_exhausted_tasks_republished_to_dlq(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert "celery_app.send_task(DLQ_TASK_NAME, args=[envelope], queue=DLQ_QUEUE_NAME)" in text
        # routing decision delegated to the hermetic policy helper
        assert "should_route_to_dlq(retries, max_retries)" in text

    def test_dlq_consumer_persists_joberror(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        assert 'error_code="TASK_DEAD_LETTERED"' in text
        assert "retryable=False" in text
        assert 'stage="DEAD_LETTER"' in text

    def test_dlq_error_payload_is_sanitized(self) -> None:
        text = L1_TASKS.read_text(encoding="utf-8")
        # The persisted DLQ error must go through sanitize_log_error: raw
        # str(exception) can carry secrets into the JobError row, while
        # type-only names discard the diagnostic context operators need.
        assert "error=sanitize_log_error(exception) if exception else None" in text

    def test_task_dead_letter_metric_exists(self) -> None:
        text = L1_METRICS.read_text(encoding="utf-8")
        # Pre-declared P0 DLQ counter, previously never incremented
        assert "dlq_tasks_total" in text
        assert "def increment_task_dead_lettered" in text
        assert 'dlq_tasks_total"].labels(task_name=' in text


class TestDlqPolicyBehavioral:
    def test_should_route_only_when_retries_exhausted(self) -> None:
        dlq = _load_dlq_module()
        assert dlq.should_route_to_dlq(retries=0, max_retries=3) is False
        assert dlq.should_route_to_dlq(retries=2, max_retries=3) is False
        assert dlq.should_route_to_dlq(retries=3, max_retries=3) is True
        assert dlq.should_route_to_dlq(retries=4, max_retries=3) is True
        # max_retries=0: first failure routes immediately
        assert dlq.should_route_to_dlq(retries=0, max_retries=0) is True
        # max_retries=None means retry forever — never dead-letter
        assert dlq.should_route_to_dlq(retries=99, max_retries=None) is False

    def test_extract_failure_context_positional_and_kwargs(self) -> None:
        dlq = _load_dlq_module()
        # pipeline stage task shape: (prev_result_dict, tenant_id)
        tenant_id, job_id = dlq.extract_failure_context(
            ({"job_id": "job-1", "success": True}, "tenant-1"), {}
        )
        assert (tenant_id, job_id) == ("tenant-1", "job-1")
        # orchestrator shape: (job_id, tenant_id)
        tenant_id, job_id = dlq.extract_failure_context(("job-9", "tenant-9"), {})
        assert (tenant_id, job_id) == ("tenant-9", "job-9")
        # kwargs always win
        tenant_id, job_id = dlq.extract_failure_context((), {"tenant_id": "t", "job_id": "j"})
        assert (tenant_id, job_id) == ("t", "j")
        # unknown shape: no fabrication — consumer falls back to log-only
        tenant_id, job_id = dlq.extract_failure_context((123,), {})
        assert (tenant_id, job_id) == (None, None)

    def test_build_envelope_is_bounded_and_typed(self) -> None:
        dlq = _load_dlq_module()
        env = dlq.build_dlq_envelope(
            task_name="layer1_ingestion.shared.tasks.storage_stage",
            task_id="abc-123",
            tenant_id="tenant-1",
            job_id="job-1",
            error="x" * 5000,
            retries=3,
            max_retries=3,
        )
        assert env["original_task"] == "layer1_ingestion.shared.tasks.storage_stage"
        assert env["original_task_id"] == "abc-123"
        assert env["retries_exhausted"] == 3
        assert env["max_retries"] == 3
        assert env["tenant_id"] == "tenant-1"
        assert env["job_id"] == "job-1"
        assert len(env["error"]) <= 500
        assert env["dead_lettered_at"]  # ISO timestamp present

    def test_build_envelope_empty_error_normalizes_to_none(self) -> None:
        dlq = _load_dlq_module()
        env = dlq.build_dlq_envelope(
            task_name="t",
            task_id=None,
            tenant_id=None,
            job_id=None,
            error=None,
            retries=0,
            max_retries=0,
        )
        assert env["error"] is None
        assert env["tenant_id"] is None
        assert env["job_id"] is None

    def test_sanitized_error_envelope_contract(self) -> None:
        # Behavioral contract for the signal handler's error payload:
        # sanitize_log_error(exception) -> build_dlq_envelope(error=...).
        from value_fabric.shared.error_handling import sanitize_log_error

        dlq = _load_dlq_module()

        # Secret-bearing exception: redacted before it can reach the
        # persisted JobError row.
        env = dlq.build_dlq_envelope(
            task_name="t",
            task_id="id-1",
            tenant_id="tenant-1",
            job_id="job-1",
            error=sanitize_log_error(ValueError("api_key=abc123 secret")),
            retries=3,
            max_retries=3,
        )
        assert env["error"] == "[REDACTED: contains api_key]"

        # Ordinary exception: type name AND message survive (repr), so the
        # dead-letter record keeps its debugging context.
        env = dlq.build_dlq_envelope(
            task_name="t",
            task_id="id-2",
            tenant_id="tenant-1",
            job_id="job-1",
            error=sanitize_log_error(RuntimeError("connection refused")),
            retries=3,
            max_retries=3,
        )
        assert env["error"] == "RuntimeError('connection refused')"
        assert "RuntimeError" in env["error"]
        assert "connection refused" in env["error"]
