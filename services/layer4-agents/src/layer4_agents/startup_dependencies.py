from __future__ import annotations

import importlib.util
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PROD_ENVS = {"production", "prod", "staging", "stage"}


@dataclass(frozen=True)
class DependencySpec:
    module: str
    required_in_prod: bool
    remediation: str


DEPENDENCIES = (
    DependencySpec("weasyprint", required_in_prod=True, remediation="Install weasyprint and required system libs (pango/cairo)."),
)


def _environment() -> str:
    return (os.getenv("ENVIRONMENT") or "development").strip().lower()


def verify_startup_dependencies(*, environment: str | None = None) -> None:
    env = (environment or _environment()).strip().lower()
    prod_like = env in PROD_ENVS
    for dep in DEPENDENCIES:
        available = importlib.util.find_spec(dep.module) is not None
        if available:
            continue
        detail = f"missing module '{dep.module}'. Remediation: {dep.remediation}"
        if prod_like and dep.required_in_prod:
            logger.error("Startup dependency check failed in %s: %s", env, detail)
            raise RuntimeError(f"Required startup dependency unavailable in {env}: {detail}")
        logger.warning("Optional startup dependency unavailable in %s: %s", env, detail)
