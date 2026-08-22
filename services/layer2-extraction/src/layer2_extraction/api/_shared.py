"""Shared leaf symbols for the Layer 2 API package.

This module is a dependency seam: it owns small, self-contained helpers and types
used by several API modules (``app_factory``, ``pipeline_runner``,
``ingestion_runner``, ``routes_extract``) that must not import one another at
module level. Keeping these symbols here breaks the package's import cycles while
preserving a single definition for each symbol.

This module MUST NOT import any sibling module under ``layer2_extraction.api`` —
it is a leaf used to break cycles, so it may only depend on code outside the
import cycle (models, shared value_fabric packages, stdlib).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.security.config import is_strict_environment

from layer2_extraction.models import ExtractionResult, Relationship

__all__ = [
    "ExtractionArtifacts",
    "_current_environment",
    "_is_strict_runtime",
    "_require_authenticated_tenant_id",
]


@dataclass
class ExtractionArtifacts:
    """Outputs from extraction pipeline used by ingestion step."""

    result: ExtractionResult
    relationships: list[Relationship]


def _current_environment() -> str | None:
    """Return the normalized runtime environment for auth fail-closed policy checks."""
    for key in ("LAYER2_ENV", "ENVIRONMENT", "APP_ENV"):
        value = os.getenv(key, "").strip()
        if value:
            return value.lower()
    return None


def _is_strict_runtime() -> bool:
    """Return whether Layer 2 must enforce strict startup safety checks."""
    environment = _current_environment()
    return is_strict_environment(environment or "unknown")


def _require_authenticated_tenant_id(tenant_id: Any, *, operation: str) -> str:
    """Require authenticated tenant context and fail closed when missing."""
    main_mod = sys.modules.get("layer2_extraction.api.main")
    if (
        main_mod
        and hasattr(main_mod, "_require_authenticated_tenant_id")
        and main_mod._require_authenticated_tenant_id
        is not _require_authenticated_tenant_id
    ):
        return main_mod._require_authenticated_tenant_id(tenant_id, operation=operation)

    if tenant_id is None:
        raise AuthorizationError(
            message="Request failed",
            details={
                "code": "tenant_context_required",
                "message": f"Authenticated tenant context is required for {operation}.",
            },
        )
    normalized = str(tenant_id).strip()
    if not normalized:
        raise AuthorizationError(
            message="Request failed",
            details={
                "code": "tenant_context_required",
                "message": f"Authenticated tenant context is required for {operation}.",
            },
        )
    return normalized
