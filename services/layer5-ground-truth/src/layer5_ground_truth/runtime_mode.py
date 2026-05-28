"""Runtime mode helpers shared across config and auth policy checks."""

def normalize_environment(value: str | None) -> str:
    """Normalize an environment name for runtime policy decisions."""
    return (value or "development").strip().lower()


def is_production_like_mode(environment: str | None, app_env: str | None = None) -> bool:
    """Return True only for the exact 'production' environment.

    This changes the previous fail-safe policy to an explicit allowlist.
    Staging and unknown/custom environments are NOT treated as production-like.
    """
    effective_environment = normalize_environment(app_env or environment)
    return effective_environment == "production"

