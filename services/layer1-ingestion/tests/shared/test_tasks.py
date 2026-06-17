"""Unit tests for Layer 1 Celery task wrappers."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from layer1_ingestion.shared.tasks import (
    ai_extraction_stage,
    browser_crawl_stage,
    compliance_check_stage,
    crawl_url_with_routing,
)

# Map each Celery entrypoint to the private async helper it wraps.
# Helpers use the _a* naming convention for async implementations.
_TASK_HELPERS = {
    compliance_check_stage: "_acompliance_check_stage",
    browser_crawl_stage: "_abrowser_crawl_stage",
    ai_extraction_stage: "_ai_extraction_stage",
    crawl_url_with_routing: "_acrawl_url_with_routing",
}


@pytest.mark.parametrize(
    "task,args",
    [
        (compliance_check_stage, (uuid.uuid4(), str(uuid.uuid4()))),
        (browser_crawl_stage, ({"job_id": str(uuid.uuid4())}, str(uuid.uuid4()))),
        (ai_extraction_stage, ({"job_id": str(uuid.uuid4())}, str(uuid.uuid4()))),
        (crawl_url_with_routing, (str(uuid.uuid4()), "https://example.com", str(uuid.uuid4()))),
    ],
)
def test_async_celery_entrypoints_run_async_impl(task, args):
    """Synchronous Celery wrappers must return the async helper's dict result."""
    expected = {"success": True, "job_id": str(uuid.uuid4())}
    helper_name = _TASK_HELPERS[task]

    with patch(
        f"layer1_ingestion.shared.tasks.{helper_name}",
        new=AsyncMock(return_value=expected),
    ) as mock_inner:
        # Bound Celery tasks receive ``self`` automatically; do not pass a mock.
        result = task(*args)

    assert result == expected
    assert isinstance(result, dict)
    # The value returned to Celery must be JSON-serializable (not a coroutine).
    assert json.loads(json.dumps(result)) == expected
    mock_inner.assert_awaited_once()
