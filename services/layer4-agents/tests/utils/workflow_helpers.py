"""Test helpers for workflow setup."""

from datetime import UTC, datetime


TEST_WORKFLOW_TYPE = "roi_calculator"


def setup_workflow_metadata(controller, workflow_id: str, workflow_type: str = TEST_WORKFLOW_TYPE):
    """Helper to set up workflow metadata for testing.

    This encapsulates the implementation detail of _workflow_metadata access,
    making tests more maintainable if the internal structure changes.
    """
    controller._workflow_metadata[workflow_id] = {
        "workflow_type": workflow_type,
        "started_at": datetime.now(UTC).isoformat(),
    }
