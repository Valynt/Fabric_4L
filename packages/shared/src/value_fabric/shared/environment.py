"""Shared environment detection utilities.

Provides centralized logic for determining the current runtime environment
and whether production-grade security checks should be enforced.
"""

import os


PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging", "stage"}
DEV_ENVIRONMENTS = {"local", "dev", "development", "test", "testing", "ci"}


def get_current_environment(env_var_names: tuple[str, ...] = ("ENVIRONMENT", "APP_ENV")) -> str:
    """Return the normalized runtime environment.

    Args:
        env_var_names: Tuple of environment variable names to check, in order of precedence.

    Returns:
        Normalized environment name (lowercase, stripped).
    """
    for var_name in env_var_names:
        value = os.getenv(var_name, "").strip()
        if value:
            return value.lower()
    return "development"


def is_production_like_environment(environment: str | None = None) -> bool:
    """Check if the environment is production-like (requires strict security validation).

    Explicitly listed production environments are treated as production-like.
    Unknown/custom environments are also treated as production-like for security
    (fail-safe: better to be too strict than too permissive).
    Only known development environments are treated as non-production.

    Args:
        environment: Optional environment name. If not provided, detects from environment variables.

    Returns:
        True if the environment should enforce production-grade security checks.
    """
    env = (environment or get_current_environment()).strip().lower()
    return env in PRODUCTION_LIKE_ENVIRONMENTS or env not in DEV_ENVIRONMENTS


def get_service_environment(service_name: str) -> str:
    """Get the environment for a specific service, checking service-specific env vars first.

    Args:
        service_name: Name of the service (e.g., "layer2", "layer6").

    Returns:
        Normalized environment name.
    """
    service_env_var = f"{service_name.upper()}_ENV"
    return get_current_environment((service_env_var, "ENVIRONMENT", "APP_ENV"))
