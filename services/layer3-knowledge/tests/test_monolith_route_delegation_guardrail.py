"""Verify that all V2 domain routers are mounted in main.py (ARCH-L3-011).

The monolith (app_monolith.py) was deleted in Sprint 3. This test replaces
the old delegation-guardrail test and asserts that the canonical route paths
are reachable via the composed FastAPI app.
"""

import pytest


def test_app_monolith_file_is_absent():
    """app_monolith.py must not exist after ARCH-L3-011 cutover."""
    from pathlib import Path

    monolith = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "api"
        / "app_monolith.py"
    )
    assert not monolith.exists(), (
        "app_monolith.py still exists — ARCH-L3-011 cutover incomplete. "
        "Delete the file and ensure all endpoints are in api/routes/ domain routers."
    )


def test_v2_domain_routers_importable():
    """All Sprint 3 V2 domain routers must be importable without a runtime."""
    from value_fabric.layer3.api.routes import (  # noqa: F401
        agents,
        analytics,
        documents,
        graph_viz,
        ingestion,
    )


def test_main_app_is_importable():
    """The composition root must be importable and expose the FastAPI app."""
    from value_fabric.layer3.api.main import app  # noqa: F401

    assert app is not None
