from __future__ import annotations

"""Layer 4 FastAPI application compatibility export.

The canonical Layer 4 application lives in :mod:`layer4_agents.api.main`.
This module exists so repository-level contract tests and legacy deployment
entrypoints can import ``layer4_agents.main`` without duplicating route,
authentication, tenant-isolation, or orchestration logic.
"""


from value_fabric.shared.security.config import validate_all_controls

validate_all_controls()

from .api.main import app

__all__ = ["app"]
