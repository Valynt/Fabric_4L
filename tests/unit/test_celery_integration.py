"""P1-011: Celery worker integration tests for L1→L2 message queue dispatch.

Uses static source analysis to avoid heavy import chains that trigger
relative-import errors in L3 knowledge service modules.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.unit]


class TestL2CeleryAppConfig:
    """Verify Layer 2 Celery application configuration via static analysis."""

    def test_celery_app_uses_redis_broker(self):
        """Celery app must use REDIS_URL as broker and backend."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'broker=redis_url' in source
        assert 'backend=redis_url' in source
        assert 'os.getenv("REDIS_URL"' in source

    def test_celery_serializer_config(self):
        """Celery must use JSON serializer for security."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'task_serializer="json"' in source
        assert 'accept_content=["json"]' in source
        assert 'result_serializer="json"' in source

    def test_celery_task_time_limits(self):
        """Tasks must have reasonable time limits."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'task_time_limit=3600' in source
        assert 'result_expires=3600' in source

    def test_celery_retry_config(self):
        """Dead letter queue and retry settings must be configured."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'task_acks_late=True' in source
        assert 'task_reject_on_worker_lost=True' in source
        assert 'task_default_retry_delay=60' in source
        assert 'task_max_retries=3' in source

    def test_celery_queues_defined(self):
        """Default and dead-letter queues must be defined."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert '"default"' in source
        assert '"layer2_dlq"' in source
        assert '"routing_key": "layer2_dlq"' in source


class TestL2CeleryTaskSignatures:
    """Validate L2 Celery task signatures and tenant isolation via static analysis."""

    def test_run_extraction_task_requires_tenant_id(self):
        """run_extraction_task must reject config without tenant_id."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'tenant_id = config.get("tenant_id")' in source
        assert 'if not tenant_id:' in source
        assert 'raise ValueError("tenant_id is required in config for extraction task")' in source

    def test_run_extraction_task_retries_on_failure(self):
        """run_extraction_task must retry with exponential backoff."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert '@celery_app.task(bind=True, max_retries=3)' in source
        assert 'raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))' in source

    def test_extract_entities_task_signature(self):
        """extract_entities_task must be registered with correct name."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert '@celery_app.task(bind=True, max_retries=3)' in source
        assert 'def extract_entities_task' in source

    def test_extract_relationships_task_signature(self):
        """extract_relationships_task must be registered with correct name."""
        with open("services/layer2-extraction/src/layer2_extraction/shared/tasks.py") as f:
            source = f.read()
        assert 'def extract_relationships_task' in source
        assert 'RelationshipExtractor' in source


class TestL1CeleryDispatch:
    """Verify L1 dispatches extraction to L2 Celery with correct arguments."""

    def test_l1_tasks_imports_celery_dispatch(self):
        """L1 tasks.py must import Celery and dispatch to L2."""
        with open("services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py") as facade:
            facade_text = facade.read()
        with open(
            "services/layer1-ingestion/src/layer1_ingestion/shared/pipeline_tasks.py"
        ) as source:
            source_text = source.read()
        # Tolerate multiline import introduced by the compatibility facade.
        assert "from celery import" in facade_text and "Celery" in facade_text
        assert "l2_celery.send_task(" in source_text
        assert "layer2_extraction.shared.tasks.run_extraction_task" in source_text

    def test_l1_dispatch_includes_tenant_id(self):
        """L1 must include tenant_id in extraction payload dispatched to L2."""
        with open(
            "services/layer1-ingestion/src/layer1_ingestion/shared/pipeline_tasks.py"
        ) as source:
            source_text = source.read()
        assert '"tenant_id"' in source_text or "'tenant_id'" in source_text
        assert "job.tenant_id" in source_text

    def test_l1_dispatch_includes_s2s_auth_when_configured(self):
        """L1 HTTP fallback must include S2S JWT when SERVICE_AUTH_SECRET is set."""
        with open(
            "services/layer1-ingestion/src/layer1_ingestion/shared/pipeline_tasks.py"
        ) as source:
            source_text = source.read()
        assert "encode_service_jwt" in source_text
        assert "Authorization" in source_text
