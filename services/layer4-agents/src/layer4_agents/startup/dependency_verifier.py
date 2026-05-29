from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging", "stage"}


@dataclass(frozen=True)
class DependencyRule:
    module: str
    required_in_prod: bool
    remediation: str


def current_environment() -> str:
    return (
        os.getenv("ENVIRONMENT")
        or os.getenv("APP_ENV")
        or os.getenv("LAYER4_ENV")
        or "development"
    ).strip().lower()


def verify_startup_dependencies(rules: list[DependencyRule], *, environment: str | None = None) -> None:
    env = environment or current_environment()
    prod_like = env in PRODUCTION_LIKE_ENVIRONMENTS
    missing_required: list[str] = []

    for rule in rules:
        try:
            importlib.import_module(rule.module)
        except ImportError:
            message = (
                f"Missing module '{rule.module}'. Remediation: {rule.remediation}. "
                f"required_in_prod={rule.required_in_prod} env={env}"
            )
            if prod_like and rule.required_in_prod:
                missing_required.append(message)
            else:
                logger.warning(message)

    if missing_required:
        raise RuntimeError("Layer 4 startup dependency verification failed:\n" + "\n".join(missing_required))


LAYER4_STARTUP_DEPENDENCIES = [
    DependencyRule(
        module="value_fabric.shared.identity",
        required_in_prod=True,
        remediation="Install value_fabric shared identity package for auth and tenant isolation",
    ),
    DependencyRule(
        module="value_fabric.shared.audit",
        required_in_prod=False,
        remediation="Install value_fabric shared audit package to emit audit trails",
    ),
    DependencyRule(
        module="value_fabric.shared.secrets",
        required_in_prod=True,
        remediation="Install shared package and ensure service runs with repository /shared path",
    ),
]


def verify_layer4_startup_dependencies(*, environment: str | None = None) -> None:
    verify_startup_dependencies(LAYER4_STARTUP_DEPENDENCIES, environment=environment)
