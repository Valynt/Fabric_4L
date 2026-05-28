from __future__ import annotations

"""Contract test for FastAPI application metadata.

Ensures the approved service title rename does not regress.
"""


import pytest


@pytest.mark.unit
def test_fastapi_title_contains_orchestrator() -> None:
    """The Layer 4 FastAPI title must use 'Orchestrator' not 'Engine'."""
    from value_fabric.layer4.api.app_factory import create_app

    app = create_app()
    assert "Orchestrator" in app.title
    assert "Engine" not in app.title
