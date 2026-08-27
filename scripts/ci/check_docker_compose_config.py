#!/usr/bin/env python3
"""Fail-closed Docker Compose static contract validation.

This gate validates compose syntax through Docker Compose v2 and then checks
repo-local contracts that `docker compose config` does not catch reliably:
build contexts, Dockerfile paths, bind-mount sources, healthcheck coverage,
production-like port exposure, placeholder secrets, runtime hardening, and
runtime dependency declarations.
It intentionally does not start containers.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

TARGET_COMPOSE_FILES = (
    "infra/compose/docker-compose.dev.yml",
    "infra/compose/docker-compose.live.yml",
    "infra/compose/docker-compose.release-smoke.yml",
    "infra/compose/docker-compose.full.yml",
    "infra/compose/docker-compose.prod.yml",
    "infra/compose/docker-compose.observability.yml",
    "infra/compose/docker-compose.monitoring.yml",
    "infra/compose/docker-compose.ha.yml",
    "infra/compose/docker-compose.db-readiness.yml",
    "infra/compose/docker-compose.backend-integrated.yml",
)

SAFE_REQUIRED_ENV_DEFAULTS = {
    "NEO4J_PASSWORD": "compose-contract-neo4j-password",
    "MINIO_ROOT_USER": "composecontract",
    "MINIO_ROOT_PASSWORD": "compose-contract-minio-password",
    "JWT_SECRET": "compose-contract-jwt-secret-minimum-32-characters",
    "SECRET_KEY": "compose-contract-secret-key-minimum-32-characters",
    "CORS_ORIGINS": "http://localhost:3001",
    "CLERK_ISSUER": "https://compose-contract.clerk.example.com",
    "CLERK_AUTHORIZED_PARTIES": "http://localhost:3001",
    "CLERK_JWKS_URL": "https://compose-contract.clerk.example.com/.well-known/jwks.json",
    "CLERK_SECRET_KEY": "compose-contract-clerk-secret-key",
    "FABRIC_AUTH_SIGNING_KEY": "compose-contract-fabric-auth-signing-key",
    "FABRIC_AUTH_PUBLIC_KEYS": "compose-contract-fabric-auth-public-key",
    "FLOWER_PASSWORD": "compose-contract-flower-password",
    "GRAFANA_ADMIN_PASSWORD": "compose-contract-grafana-password",
    "REDIS_PASSWORD": "compose-contract-redis-password",
    "POSTGRES_USER": "compose_contract_user",
    "POSTGRES_PASSWORD": "compose-contract-postgres-password",
    "API_KEY_HMAC_SECRET": "compose-contract-api-key-hmac-secret-32chars",
    "SERVICE_AUTH_SECRET": "compose-contract-service-auth-secret-32chars",
    "CREDENTIALS_MASTER_KEY": "compose-contract-credentials-master-key-32chars",
    "DEFAULT_TENANT_ID": "00000000-0000-4000-8000-000000000001",
    "LAYER4_DATABASE_URL": "postgresql+asyncpg://compose_contract_user:compose-contract-postgres-password@postgres:5432/layer4_agents",
}

ONE_SHOT_SERVICE_PATTERNS = (
    "init",
    "migrate",
    "migration",
    "seed",
    "runner",
    "test",
)

SKIPPED_BIND_SOURCES = {
    "/var/run/docker.sock",
    "/var/lib/docker/containers",
}

FULL_COMPOSE_FILE = "docker-compose.full.yml"

FULL_COMPOSE_ALLOWED_PORT_SERVICES = {
    # DAST scans all layer API ports from the host; keep the list minimal and
    # aligned with the endpoints exercised in .github/workflows/security-gates.yml.
    "api-gateway",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "layer6-benchmarks",
}

FULL_COMPOSE_HARDENING_EXEMPT_SERVICES = {
    "neo4j",
    "layer5-migrate",
    "alertmanager",
    "grafana",
    "jaeger",
    "redis",
    "vault",
    "postgres",
}

FULL_COMPOSE_REQUIRED_ENV_KEYS = {
    "JWT_SECRET",
    "NEO4J_PASSWORD",
    "REDIS_PASSWORD",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "FLOWER_PASSWORD",
    "GRAFANA_ADMIN_PASSWORD",
    "API_KEY_HMAC_SECRET",
    "SERVICE_AUTH_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "DEFAULT_TENANT_ID",
}

FRONTEND_REQUIRED_ENV_KEYS = {
    "VITE_API_BASE",
    "VITE_L1_PREFIX",
    "VITE_L2_PREFIX",
    "VITE_L2_5_PREFIX",
    "VITE_L3_PREFIX",
    "VITE_L4_PREFIX",
    "VITE_L5_PREFIX",
    "VITE_L6_PREFIX",
    "VITE_L7_PREFIX",
    "VITE_ENABLE_CRM_SYNC",
    "VITE_CRM_PROVIDER",
    "VITE_CRM_API_PROXY",
    "VITE_ENABLE_C1_REPORTS",
    "VITE_USE_MOCKS",
}

PYTHONPATH_BUILT_IN_PATHS = {"/app", "/app/src", "/app/.venv"}

LIVE_COMPOSE_FILE = "docker-compose.live.yml"

LIVE_COMPOSE_FORBIDDEN_TEXT = {
    "POSTGRES_HOST_AUTH_METHOD: trust": "live compose must not use trust database authentication",
    "minioadmin": "live compose must not hardcode MinIO default credentials",
    "live-local-secret-do-not-use-in-production": "live compose must not provide fallback JWT secrets",
    "live-local-service-auth-secret-do-not-use-in-production": "live compose must not provide fallback service auth secrets",
    "live-local-api-key-hmac-secret-do-not-use-in-production": "live compose must not provide fallback API key HMAC secrets",
    "postgres:postgres@": "live compose database URLs must not hardcode postgres credentials",
    "devpassword": "live compose must not hardcode Neo4j development credentials",
}

PLACEHOLDER_SECRET_PATTERNS = (
    "do-not-use-in-production",
    "non_deployable",
    "non-deployable",
    "changeme",
    "change_me",
    "devpassword",
    "placeholder",
    "todo",
    "postgres:postgres@",
)

SENSITIVE_ENV_NAME_RE = re.compile(r"(SECRET|PASSWORD|TOKEN|PRIVATE|API_KEY|HMAC)", re.IGNORECASE)

# Auth environment variables whose defaults must live in .env.generated, not in compose files.
AUTH_ENV_KEYS = {
    "AUTH_PROVIDER",
    "VITE_AUTH_PROVIDER",
    "CLERK_ISSUER",
    "CLERK_JWT_AUDIENCE",
    "CLERK_AUTHORIZED_PARTIES",
    "CLERK_JWKS_URL",
    "CLERK_PINNED_JWT_PEM",
    "CLERK_SECRET_KEY",
    "CLERK_WEBHOOK_SIGNING_SECRET",
    "CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE",
    "CLERK_PUBLISHABLE_KEY",
    "VITE_CLERK_PUBLISHABLE_KEY",
    "VITE_CLERK_SIGN_IN_URL",
    "VITE_CLERK_SIGN_UP_URL",
    "VITE_CLERK_AFTER_SIGN_IN_URL",
    "VITE_CLERK_AFTER_SIGN_UP_URL",
    "VITE_CLERK_JWT_TEMPLATE",
    "JWT_ALGORITHM",
    "ALGORITHM",
    "CORS_ORIGINS",
    "FABRIC_AUTH_SIGNING_KEY",
    "FABRIC_AUTH_SIGNING_KID",
    "FABRIC_AUTH_PUBLIC_KEYS",
    "FABRIC_AUTH_VERIFYING_PUBLIC_KEY",
    "FABRIC_AUTH_ISSUER",
    "FABRIC_AUTH_AUDIENCE",
    "FABRIC_AUTH_ENVELOPE_TTL_SECONDS",
    "KEYCLOAK_URL",
    "KEYCLOAK_REALM",
    "KEYCLOAK_ADMIN_USER",
    "KEYCLOAK_ADMIN_PASSWORD",
    "KEYCLOAK_FRONTEND_CLIENT_SECRET",
    "KEYCLOAK_API_CLIENT_SECRET",
    "OIDC_ISSUER",
    "OIDC_AUDIENCE",
    "OIDC_JWKS_URL",
    "OIDC_JWKS_JSON",
    "JWT_SECRET",
    "SERVICE_AUTH_SECRET",
    "API_KEY_HMAC_SECRET",
    "CREDENTIALS_MASTER_KEY",
    "AUTH_BYPASS_ENABLED",
    "ALLOW_DEV_AUTH_BYPASS",
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
}


@dataclass(frozen=True)
class ComposeFailure:
    compose_file: str
    service: str
    message: str

    def format(self) -> str:
        prefix = f"{self.compose_file}"
        if self.service:
            prefix += f"::{self.service}"
        return f"{prefix}: {self.message}"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run_command(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    stdout_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    if stdout_path:
        with stdout_path.open("w", encoding="utf-8") as stdout_file:
            result = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                text=True,
                stdout=stdout_file,
                stderr=subprocess.PIPE,
                check=False,
            )
    else:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        command = " ".join(args)
        fail(f"command failed ({command}): {stderr}")
    return result


def docker_env() -> dict[str, str]:
    env = os.environ.copy()
    for key, value in SAFE_REQUIRED_ENV_DEFAULTS.items():
        env.setdefault(key, value)
    return env


def require_docker_compose() -> None:
    run_command(["docker", "--version"])
    run_command(["docker", "compose", "version"])


def load_compose(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail(f"{path.name} must parse as a YAML mapping")
    if not isinstance(data.get("services"), dict):
        fail(f"{path.name} must define a services mapping")
    return data


def has_unresolved_env_reference(value: str) -> bool:
    return "${" in value or "$" in value


def looks_like_path(source: str) -> bool:
    normalized = source.replace("\\", "/")
    return normalized.startswith((".", "/", "~")) or bool(
        re.match(r"^[A-Za-z]:/", normalized)
    )


def resolve_repo_path(
    source: str,
    repo_root: Path = REPO_ROOT,
    base_dir: Path | None = None,
) -> Path | None:
    if has_unresolved_env_reference(source):
        return None
    if source in SKIPPED_BIND_SOURCES:
        return None
    normalized = source.replace("\\", "/")
    if normalized.startswith(("/", "~")) or re.match(r"^[A-Za-z]:/", normalized):
        return None
    return ((base_dir or repo_root) / Path(source)).resolve()


def split_short_volume(volume: str) -> tuple[str | None, str | None]:
    if ":" not in volume:
        return None, volume
    parts = volume.split(":")
    if re.match(r"^[A-Za-z]$", parts[0]) and len(parts) > 2:
        source = ":".join(parts[:2])
        target = parts[2]
        return source, target
    return parts[0], parts[1] if len(parts) > 1 else None


def iter_bind_sources(
    service: dict[str, Any], declared_volumes: set[str]
) -> list[str]:
    sources: list[str] = []
    for volume in service.get("volumes") or []:
        if isinstance(volume, str):
            source, _target = split_short_volume(volume)
            if source is None:
                continue
            if source in declared_volumes or not looks_like_path(source):
                continue
            sources.append(source)
        elif isinstance(volume, dict):
            volume_type = volume.get("type")
            source = volume.get("source") or volume.get("src")
            if not source:
                continue
            if volume_type and volume_type != "bind":
                continue
            if source in declared_volumes or not looks_like_path(str(source)):
                continue
            sources.append(str(source))
    return sources


def iter_volume_targets(service: dict[str, Any]) -> list[str]:
    """Return all container-side target paths from volume mounts."""
    targets: list[str] = []
    for volume in service.get("volumes") or []:
        if isinstance(volume, str):
            _source, target = split_short_volume(volume)
            if target is not None:
                targets.append(target)
        elif isinstance(volume, dict):
            target = volume.get("target") or volume.get("dst")
            if target:
                targets.append(str(target))
    return targets


def target_covers_path(target: str, path: str) -> bool:
    """Check if a volume target path covers (is prefix of or equal to) path."""
    target_parts = target.rstrip("/").split("/")
    path_parts = path.rstrip("/").split("/")
    if len(target_parts) > len(path_parts):
        return False
    return path_parts[: len(target_parts)] == target_parts


def resolve_build_paths(
    service: dict[str, Any],
    repo_root: Path = REPO_ROOT,
    base_dir: Path | None = None,
) -> tuple[Path, Path] | None:
    build = service.get("build")
    if not build:
        return None
    if isinstance(build, str):
        context_value = build
        dockerfile_value = "Dockerfile"
    elif isinstance(build, dict):
        context_value = str(build.get("context", "."))
        dockerfile_value = str(build.get("dockerfile", "Dockerfile"))
    else:
        return None

    context_path = Path(context_value)
    if not context_path.is_absolute():
        context_path = (base_dir or repo_root) / context_path
    context_path = context_path.resolve()

    dockerfile_path = Path(dockerfile_value)
    if not dockerfile_path.is_absolute():
        if dockerfile_value.startswith("."):
            dockerfile_path = context_path / dockerfile_path
        else:
            dockerfile_path = context_path / dockerfile_path
    return context_path, dockerfile_path.resolve()


def dockerfile_has_healthcheck(dockerfile_path: Path) -> bool:
    if not dockerfile_path.exists() or not dockerfile_path.is_file():
        return False
    for line in dockerfile_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip().upper()
        if stripped.startswith("HEALTHCHECK") and "HEALTHCHECK NONE" not in stripped:
            return True
    return False


def service_profiles(service: dict[str, Any]) -> set[str]:
    profiles = service.get("profiles") or []
    if isinstance(profiles, str):
        return {profiles}
    if isinstance(profiles, list):
        return {str(profile) for profile in profiles}
    return set()


def is_dev_profile_service(service: dict[str, Any]) -> bool:
    return "dev" in {profile.lower() for profile in service_profiles(service)}


def is_one_shot_service(service_name: str, service: dict[str, Any]) -> bool:
    name = service_name.lower()
    if any(pattern in name for pattern in ONE_SHOT_SERVICE_PATTERNS):
        return True
    restart = str(service.get("restart", "")).strip().lower()
    normalized_profiles = {profile.strip().lower() for profile in service_profiles(service)}
    if "backup" in normalized_profiles and restart in {"no", "none", "false"}:
        return True
    command = service.get("command", "")
    command_text = " ".join(command) if isinstance(command, list) else str(command)
    return restart in {"no", "none", "false"} and any(
        token in command_text.lower() for token in ("alembic", "seed", "pytest", "pnpm run seed")
    )


def service_has_extends_healthcheck(
    service: Mapping[str, object],
    compose_file: Path,
    visited: set[tuple[Path, str]] | None = None,
) -> bool:
    """Check if a service inherits a healthcheck via Docker Compose `extends`."""
    extends = service.get("extends")
    if not isinstance(extends, Mapping):
        return False

    extends_file = extends.get("file")
    extends_service = extends.get("service")
    if not isinstance(extends_file, str) or not extends_file.strip():
        return False
    if not isinstance(extends_service, str) or not extends_service.strip():
        return False

    base_path = (compose_file.parent / extends_file).resolve()
    inheritance_key = (base_path, extends_service)
    visited = set() if visited is None else visited
    if inheritance_key in visited:
        return False
    visited.add(inheritance_key)

    try:
        base_data = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False

    if not isinstance(base_data, Mapping):
        return False

    base_services = base_data.get("services") or {}
    if not isinstance(base_services, Mapping):
        return False

    base_service = base_services.get(extends_service)
    if not isinstance(base_service, Mapping):
        return False

    if "healthcheck" in base_service:
        return True

    # Recursively follow chained extends
    return service_has_extends_healthcheck(base_service, base_path, visited)


def iter_environment_entries(service: dict[str, Any]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    environment = service.get("environment") or []
    if isinstance(environment, dict):
        for key, value in environment.items():
            entries.append((str(key), "" if value is None else str(value)))
    elif isinstance(environment, list):
        for item in environment:
            if not isinstance(item, str) or "=" not in item:
                continue
            key, value = item.split("=", 1)
            entries.append((key, value))
    return entries


def is_required_env_reference(value: str) -> bool:
    return bool(re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*(?::?\?)[^}]*\}", value))


def has_optional_env_default(value: str) -> bool:
    return bool(re.search(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-", value))


def has_unguarded_required_env_reference(value: str, required_key: str) -> bool:
    for match in re.finditer(r"\$\{([A-Za-z_][A-Za-z0-9_]*)([^}]*)\}", value):
        key, suffix = match.groups()
        if key == required_key and not suffix.startswith((":?", "?")):
            return True
    return False


def has_malformed_env_interpolation(value: str) -> bool:
    """Catch common compose typos that leave literal brace characters in env values.

    Handles nested interpolation such as ${VAR:-${DEFAULT}} by counting balanced
    braces rather than using a flat regex that cannot see past the first closing
    brace of an inner reference.
    """
    stripped = value.strip()
    if not stripped:
        return False
    cleaned_chars: list[str] = []
    i = 0
    n = len(stripped)
    while i < n:
        if stripped[i] == "$" and i + 1 < n and stripped[i + 1] == "{":
            j = i + 2
            depth = 1
            while j < n and depth > 0:
                if stripped[j] == "{":
                    depth += 1
                elif stripped[j] == "}":
                    depth -= 1
                j += 1
            if depth == 0:
                content = stripped[i + 2 : j - 1]
                # Valid reference: identifier optionally followed by a modifier.
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*([:?$#=+-].*)?$", content, re.DOTALL):
                    i = j
                    continue
        cleaned_chars.append(stripped[i])
        i += 1
    cleaned = "".join(cleaned_chars)
    return "}" in cleaned or "${" in cleaned


def contains_placeholder_secret(value: str) -> bool:
    normalized = value.lower()
    return any(pattern in normalized for pattern in PLACEHOLDER_SECRET_PATTERNS)


def is_default_sensitive_literal(key: str, value: str) -> bool:
    if not SENSITIVE_ENV_NAME_RE.search(key):
        return False
    return value.lower() in {"admin", "password", "postgres", "root", "changeme"}


def service_depends_on(service: dict[str, Any], dependency_name: str) -> bool:
    depends_on = service.get("depends_on") or {}
    if isinstance(depends_on, dict):
        return dependency_name in depends_on
    if isinstance(depends_on, list):
        return dependency_name in depends_on
    return False


def service_references_redis(service: dict[str, Any]) -> bool:
    for key, value in iter_environment_entries(service):
        joined = f"{key}={value}".lower()
        if "redis://" in joined or "@redis:" in joined or "redis:" in joined:
            return True
    return False


def service_has_cap_drop_all(service: dict[str, Any]) -> bool:
    cap_drop = service.get("cap_drop") or []
    if isinstance(cap_drop, str):
        cap_drop = [cap_drop]
    return any(str(cap).upper() == "ALL" for cap in cap_drop)


def service_has_no_new_privileges(service: dict[str, Any]) -> bool:
    security_opt = service.get("security_opt") or []
    if isinstance(security_opt, str):
        security_opt = [security_opt]
    return any(str(option) == "no-new-privileges:true" for option in security_opt)


def validate_full_compose_hardening(
    compose_file: Path,
    services: dict[str, Any],
) -> list[ComposeFailure]:
    if compose_file.name != FULL_COMPOSE_FILE:
        return []

    failures: list[ComposeFailure] = []
    for service_name, service in services.items():
        if not isinstance(service, dict):
            continue

        if service.get("ports") and service_name not in FULL_COMPOSE_ALLOWED_PORT_SERVICES:
            failures.append(
                ComposeFailure(
                    compose_file.name,
                    service_name,
                    "host-published ports are not allowed in production-like full compose",
                )
            )

        if not is_dev_profile_service(service):
            for key, value in iter_environment_entries(service):
                if key in FULL_COMPOSE_REQUIRED_ENV_KEYS and not is_required_env_reference(value):
                    failures.append(
                        ComposeFailure(
                            compose_file.name,
                            service_name,
                            f"{key} must use required env interpolation",
                        )
                    )
                if key in FULL_COMPOSE_REQUIRED_ENV_KEYS and has_optional_env_default(value):
                    failures.append(
                        ComposeFailure(
                            compose_file.name,
                            service_name,
                            f"{key} must not use an optional default",
                        )
                    )
                for required_key in FULL_COMPOSE_REQUIRED_ENV_KEYS:
                    if has_unguarded_required_env_reference(value, required_key):
                        failures.append(
                            ComposeFailure(
                                compose_file.name,
                                service_name,
                                f"{required_key} reference must use required env interpolation",
                            )
                        )
                if (
                    (SENSITIVE_ENV_NAME_RE.search(key) or "://" in value)
                    and contains_placeholder_secret(value)
                ) or is_default_sensitive_literal(key, value):
                    failures.append(
                        ComposeFailure(
                            compose_file.name,
                            service_name,
                            f"{key} contains a production-forbidden placeholder value",
                        )
                    )

        if service_name != "redis" and service_references_redis(service) and not service_depends_on(
            service, "redis"
        ):
            failures.append(
                ComposeFailure(
                    compose_file.name,
                    service_name,
                    "references Redis at runtime but does not declare depends_on.redis",
                )
            )

        has_build = "build" in service
        if (
            has_build
            and service_name not in FULL_COMPOSE_HARDENING_EXEMPT_SERVICES
            and not is_one_shot_service(service_name, service)
        ):
            if not service_has_cap_drop_all(service):
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        "custom long-running service must drop all Linux capabilities",
                    )
                )
            if not service_has_no_new_privileges(service):
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        "custom long-running service must set no-new-privileges",
                    )
                )
            if service.get("read_only") is not True:
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        "custom long-running service must use read_only: true",
                    )
                )

    return failures


def validate_live_compose_security(compose_file: Path) -> list[ComposeFailure]:
    if compose_file.name != LIVE_COMPOSE_FILE:
        return []

    text = compose_file.read_text(encoding="utf-8")
    failures: list[ComposeFailure] = []
    for forbidden, message in LIVE_COMPOSE_FORBIDDEN_TEXT.items():
        if forbidden in text:
            failures.append(ComposeFailure(compose_file.name, "", message))
    return failures


def validate_auth_env_defaults(compose_file: Path, services: dict[str, Any]) -> list[ComposeFailure]:
    """Ensure auth env variables do not redefine inline defaults in compose files.

    The canonical auth contract lives in .env.generated; compose files may reference
    variables but must not supply their own defaults.
    """
    failures: list[ComposeFailure] = []
    for service_name, service in services.items():
        if not isinstance(service, dict):
            continue
        for key, value in iter_environment_entries(service):
            if key in AUTH_ENV_KEYS and has_optional_env_default(value):
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        f"{key} must not redefine an inline default in compose; use .env.generated as the auth contract",
                    )
                )
    return failures


def validate_env_interpolation_syntax(compose_file: Path, services: dict[str, Any]) -> list[ComposeFailure]:
    failures: list[ComposeFailure] = []
    for service_name, service in services.items():
        if not isinstance(service, dict):
            continue
        for key, value in iter_environment_entries(service):
            if has_malformed_env_interpolation(value):
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        f"{key} has malformed env interpolation syntax",
                    )
                )
    return failures


def validate_pythonpath_mounts(
    compose_file: Path,
    services: dict[str, Any],
) -> list[ComposeFailure]:
    """Ensure every PYTHONPATH entry under /app is backed by a volume mount or built-in path."""
    failures: list[ComposeFailure] = []
    for service_name, service in services.items():
        if not isinstance(service, dict):
            continue
        pythonpath = None
        for key, value in iter_environment_entries(service):
            if key == "PYTHONPATH":
                pythonpath = value
                break
        if not pythonpath:
            continue
        targets = iter_volume_targets(service)
        for entry in pythonpath.split(":"):
            entry = entry.strip()
            if not entry:
                continue
            if entry in PYTHONPATH_BUILT_IN_PATHS:
                continue
            if not entry.startswith("/app"):
                continue
            if any(target_covers_path(t, entry) for t in targets):
                continue
            failures.append(
                ComposeFailure(
                    compose_file.name,
                    service_name,
                    f"PYTHONPATH entry '{entry}' is not backed by a volume mount",
                )
            )
    return failures


def validate_frontend_env_completeness(
    compose_file: Path,
    services: dict[str, Any],
) -> list[ComposeFailure]:
    """Ensure docker-compose.dev.yml frontend service declares all required env vars."""
    if compose_file.name != "docker-compose.dev.yml":
        return []

    frontend_service = services.get("frontend")
    if not isinstance(frontend_service, dict):
        return []

    declared_keys = {key for key, _value in iter_environment_entries(frontend_service)}
    failures: list[ComposeFailure] = []
    for required in FRONTEND_REQUIRED_ENV_KEYS:
        if required not in declared_keys:
            failures.append(
                ComposeFailure(
                    compose_file.name,
                    "frontend",
                    f"required frontend env variable '{required}' is missing from the service environment block",
                )
            )
    return failures


def validate_compose_contract(compose_file: Path, repo_root: Path = REPO_ROOT) -> list[ComposeFailure]:
    data = load_compose(compose_file)
    declared_volumes = set((data.get("volumes") or {}).keys())
    compose_base_dir = compose_file.parent
    failures: list[ComposeFailure] = []

    services = data["services"]
    failures.extend(validate_full_compose_hardening(compose_file, services))
    failures.extend(validate_live_compose_security(compose_file))
    failures.extend(validate_auth_env_defaults(compose_file, services))
    failures.extend(validate_env_interpolation_syntax(compose_file, services))
    failures.extend(validate_pythonpath_mounts(compose_file, services))
    failures.extend(validate_frontend_env_completeness(compose_file, services))
    for service_name, service in services.items():
        if not isinstance(service, dict):
            failures.append(
                ComposeFailure(compose_file.name, service_name, "service definition must be a mapping")
            )
            continue

        build_paths = resolve_build_paths(service, repo_root, compose_base_dir)
        dockerfile_path: Path | None = None
        if build_paths:
            context_path, dockerfile_path = build_paths
            if not context_path.exists() or not context_path.is_dir():
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        f"build context does not exist: {context_path}",
                    )
                )
            if not dockerfile_path.exists() or not dockerfile_path.is_file():
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        f"Dockerfile does not exist: {dockerfile_path}",
                    )
                )

        for source in iter_bind_sources(service, declared_volumes):
            resolved = resolve_repo_path(source, repo_root, compose_base_dir)
            if resolved is None:
                continue
            if not resolved.exists():
                failures.append(
                    ComposeFailure(
                        compose_file.name,
                        service_name,
                        f"bind-mount source does not exist: {source}",
                    )
                )

        has_healthcheck = "healthcheck" in service
        if not has_healthcheck and dockerfile_path:
            has_healthcheck = dockerfile_has_healthcheck(dockerfile_path)
        if not has_healthcheck:
            has_healthcheck = service_has_extends_healthcheck(service, compose_file)
        if not has_healthcheck and not is_one_shot_service(service_name, service):
            failures.append(
                ComposeFailure(
                    compose_file.name,
                    service_name,
                    "long-running service has no compose healthcheck or Dockerfile HEALTHCHECK",
                )
            )

    return failures


def validate_all(artifact_dir: Path, compose_files: tuple[str, ...] = TARGET_COMPOSE_FILES) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    env = docker_env()
    require_docker_compose()

    failures: list[ComposeFailure] = []
    for compose_name in compose_files:
        compose_path = REPO_ROOT / compose_name
        if not compose_path.exists():
            failures.append(ComposeFailure(compose_name, "", "compose file is missing"))
            continue
        run_command(["docker", "compose", "-f", compose_name, "config", "--quiet"], env=env)
        artifact_path = artifact_dir / f"{compose_path.stem}.resolved.yml"
        run_command(["docker", "compose", "-f", compose_name, "config"], env=env, stdout_path=artifact_path)
        failures.extend(validate_compose_contract(compose_path))

    if failures:
        for failure in failures:
            print(failure.format(), file=sys.stderr)
        raise SystemExit(1)

    print(f"Docker Compose config contract passed for {len(compose_files)} compose files.")
    print(f"Resolved configs written to {artifact_dir}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/docker-compose-config",
        help="Directory for resolved compose config artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    validate_all((REPO_ROOT / args.artifact_dir).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
