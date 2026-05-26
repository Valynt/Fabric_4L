"""Production startup security configuration validation.

This module centralizes fail-fast checks for controls that protect tenant
isolation in production.  It is intentionally dependency-free so CI release
policy gates can execute it without live infrastructure.
"""
from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import parse_qsl, urlparse

logger = logging.getLogger(__name__)

DEFAULT_JWT_SECRETS = {
    "test-secret",
    "test-secret-key",
    "changeme",
    "change-me",
    "your-secret",
    "your-secret-key",
    "secret",
    "development-secret",
}

SUPERUSER_NAMES = {"postgres", "root", "admin", "superuser"}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def current_environment() -> str:
    return _env("ENVIRONMENT", _env("APP_ENV", "development")).lower()


def is_production() -> bool:
    return current_environment() in {"production", "prod"}


def is_staging() -> bool:
    return current_environment() in {"staging", "stage", "preprod", "pre-production"}


def is_test_runtime() -> bool:
    return current_environment() in {"test", "testing", "ci"}


def _split_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def validate_jwt_config() -> None:
    """Reject missing, weak, or default JWT secrets in production.

    Production JWT_SECRET values must be at least 32 characters. Known default
    values such as ``test-secret`` and ``changeme`` are rejected because they are
    brute-forceable and commonly leaked in examples.
    """
    jwt_secret = _env("JWT_SECRET")
    if is_test_runtime() and not jwt_secret:
        logger.info("JWT_SECRET is unset in test runtime; use test fixtures for deterministic secrets")
        return

    if not jwt_secret:
        raise ValueError("JWT_SECRET is required in all non-test runtimes")
    if len(jwt_secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters in all non-test runtimes")
    if jwt_secret.lower() in DEFAULT_JWT_SECRETS:
        raise ValueError("Reject default JWT_SECRET values in all non-test runtimes")
    if not is_test_runtime() and not _env("JWT_ISSUER"):
        raise ValueError("JWT_ISSUER is required in all non-test runtimes")
    if not is_test_runtime() and not _env("JWT_AUDIENCE"):
        raise ValueError("JWT_AUDIENCE is required in all non-test runtimes")


def validate_cors_config() -> None:
    origins = _split_origins(_env("CORS_ORIGINS", _env("ALLOWED_ORIGINS", "")))
    if not is_production():
        if any(origin == "*" for origin in origins):
            logger.warning("Wildcard CORS origin is allowed only outside production")
        return

    if not origins:
        raise ValueError("CORS_ORIGINS is required in production")
    if any(origin == "*" for origin in origins):
        raise ValueError("CORS wildcard origins are not allowed in production")
    insecure = [origin for origin in origins if origin.startswith("http://")]
    if insecure:
        raise ValueError("HTTP CORS origins are not allowed in production")


def _database_role(parsed) -> str:
    return (parsed.username or "").lower()


def _validate_database_tls_mode(database_url: str, *, source_variable: str) -> None:
    parsed = urlparse(database_url)
    query_params = {key.lower(): value for key, value in parse_qsl(parsed.query, keep_blank_values=True)}
    sslmode = (query_params.get("sslmode", "") or "").strip().lower()
    approved_modes = {"require", "verify-ca", "verify-full"}
    preferred_mode = "verify-full"

    if sslmode not in approved_modes:
        raise ValueError(
            f"Production {source_variable} must include sslmode=require or stronger "
            "(verify-ca/verify-full); verify-full is preferred"
        )

    if sslmode != preferred_mode:
        logger.info("Production %s uses sslmode=%s; sslmode=%s is preferred", source_variable, sslmode, preferred_mode)


def validate_database_config() -> None:
    database_url = _env("DATABASE_URL")
    if not database_url:
        if is_production():
            raise ValueError("DATABASE_URL is required in production")
        logger.warning("DATABASE_URL is not configured; development-only mode")
        return

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()
    if is_production():
        if scheme.startswith("sqlite"):
            raise ValueError("SQLite is not supported in production")
        if not scheme.startswith(("postgresql", "postgres")):
            raise ValueError("Production DATABASE_URL must use PostgreSQL for RLS")
        # Row-level security prerequisites: PostgreSQL and a non-superuser role.
        # A superuser bypasses RLS policies entirely; production deployments must
        # use an application role validated against pg_roles.rolsuper=false.
        if _database_role(parsed) in SUPERUSER_NAMES:
            raise ValueError("PostgreSQL superuser connections bypass RLS")
        _validate_database_tls_mode(database_url, source_variable="DATABASE_URL")

    sync_database_url = _env("DATABASE_URL_SYNC")
    if is_production() and sync_database_url:
        _validate_database_tls_mode(sync_database_url, source_variable="DATABASE_URL_SYNC")


def validate_rls_prerequisites() -> None:
    """Validate row_level_security / tenant_isolation prerequisites.

    The live database check for pg_roles.rolsuper belongs in deployment probes;
    this deterministic startup check enforces the static contract used by CI.
    """
    validate_database_config()


def validate_environment_config() -> None:
    if is_production() and _env("DEBUG").lower() in {"1", "true", "yes", "on"}:
        raise ValueError("DEBUG must not be enabled in production")


def validate_all_controls() -> None:
    controls_disabled = (
        is_production()
        and not _env("REDIS_URL")
        and not _env("AUDIT_SINK_URL")
        and not _env("JWT_SECRET")
        and _env("CORS_ORIGINS", _env("ALLOWED_ORIGINS", "")) == "*"
    )
    if controls_disabled:
        raise ValueError("All security controls are disabled in production")
    validate_environment_config()
    validate_jwt_config()
    validate_cors_config()
    validate_database_config()
    validate_rls_prerequisites()


def get_startup_summary() -> dict[str, Any]:
    env = current_environment()
    degraded_controls: list[str] = []
    redis_url = _env("REDIS_URL")
    audit_sink = _env("AUDIT_SINK_URL")

    if not redis_url:
        degraded_controls.extend(["redis", "rate_limiting"])
    if not audit_sink:
        degraded_controls.append("audit")

    database_url = _env("DATABASE_URL")
    parsed = urlparse(database_url) if database_url else None
    rls_enabled = bool(parsed and parsed.scheme.lower().startswith(("postgresql", "postgres")))

    origins = _split_origins(_env("CORS_ORIGINS", _env("ALLOWED_ORIGINS", "")))
    cors_mode = "permissive" if not origins or "*" in origins else "restricted"
    return {
        "environment": env,
        "production": is_production(),
        "mode": "production" if is_production() else "development" if env == "development" else env,
        "degraded_controls": degraded_controls,
        "redis_enabled": bool(redis_url),
        "audit_enabled": bool(audit_sink),
        "cors_mode": cors_mode,
        "jwt_validation": "strict" if _env("JWT_SECRET") and is_production() else "disabled" if not _env("JWT_SECRET") else "configured",
        "warnings": [] if is_production() else ["WARNING"],
        "active_controls": {
            "authentication": "jwt_required" if _env("JWT_SECRET") else "missing_secret",
            "rate_limiting": "redis" if redis_url else "degraded_without_redis",
            "audit": "configured" if audit_sink else "degraded_without_sink",
            "tenant_isolation": "rls" if rls_enabled else "unverified",
        },
        "tenant_isolation": {
            "mode": "row_level_security" if rls_enabled else "unverified",
            "rls_enabled": rls_enabled,
            "row_level_security": rls_enabled,
            "superuser_check": "static_url_role_check",
        },
        "database": {
            "configured": bool(database_url),
            "engine": parsed.scheme if parsed else None,
        },
    }
