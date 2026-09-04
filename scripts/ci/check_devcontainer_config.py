#!/usr/bin/env python3
"""Validate the repository's canonical Dev Container and Compose topology."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DIGEST_REF = re.compile(r"@sha256:[0-9a-f]{64}$")

COMPOSE_RENDER_ENV_DEFAULTS = {
    "API_KEY_HMAC_SECRET": "devcontainer-contract-api-key-hmac-secret-32chars",
    "CLERK_AUTHORIZED_PARTIES": "http://localhost:3001",
    "CLERK_ISSUER": "http://localhost:3001",
    "CLERK_JWKS_URL": "http://localhost:3001/.well-known/jwks.json",
    "CLERK_SECRET_KEY": "devcontainer-contract-clerk-secret-key",
    "CORS_ORIGINS": "http://localhost:3001",
    "CREDENTIALS_MASTER_KEY": "devcontainer-contract-credentials-master-key-32chars",
    "DEFAULT_TENANT_ID": "00000000-0000-4000-8000-000000000001",
    "FABRIC_AUTH_PUBLIC_KEYS": "devcontainer-contract-fabric-auth-public-key",
    "FABRIC_AUTH_SIGNING_KEY": "devcontainer-contract-fabric-auth-signing-key",
    "FLOWER_PASSWORD": "devcontainer-contract-flower-password",
    "GRAFANA_ADMIN_PASSWORD": "devcontainer-contract-grafana-password",
    "JWT_SECRET": "devcontainer-contract-jwt-secret-minimum-32-characters",
    "LAYER4_DATABASE_URL": "postgresql+asyncpg://devcontainer:devcontainer@postgres:5432/layer4_agents",
    "NEO4J_PASSWORD": "devcontainer-contract-neo4j-password",
    "POSTGRES_PASSWORD": "devcontainer-contract-postgres-password",
    "POSTGRES_USER": "devcontainer_contract_user",
    "REDIS_PASSWORD": "devcontainer-contract-redis-password",
    "SECRET_KEY": "devcontainer-contract-secret-key-minimum-32-characters",
    "SERVICE_AUTH_SECRET": "devcontainer-contract-service-auth-secret-32chars",
}


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read valid JSON from {path}: {exc}")
        return {}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_static(root: Path) -> list[str]:
    errors: list[str] = []
    dc = root / ".devcontainer"
    compose_path = dc / "docker-compose.yml"
    compose = compose_path.read_text(encoding="utf-8") if compose_path.exists() else ""

    require(
        "/var/run/docker.sock" not in compose,
        "default topology must not mount the host Docker socket",
        errors,
    )

    required = [
        dc / "devcontainer.json",
        dc / "devcontainer-lock.json",
        dc / "Dockerfile",
        dc / "docker-compose.cloud.yml",
        dc / "docker-compose.local-socket.yml",
        dc / "post-create.sh",
        dc / "post-start.sh",
        dc / "dev-stack.sh",
        dc / "legacy-env.sh",
    ]
    for path in required:
        require(
            path.is_file(), f"missing required file: {path.relative_to(root)}", errors
        )
    if errors and not (dc / "devcontainer.json").exists():
        return errors

    config = load_json(dc / "devcontainer.json", errors)
    lock = load_json(dc / "devcontainer-lock.json", errors)
    require(
        config.get("dockerComposeFile") == ["docker-compose.yml"],
        "devcontainer.json must select only docker-compose.yml",
        errors,
    )
    require(config.get("service") == "dev", "Dev Container service must be dev", errors)
    require(
        config.get("workspaceFolder") == "/workspace/Fabric_4L",
        "workspaceFolder must be /workspace/Fabric_4L",
        errors,
    )
    require(config.get("remoteUser") == "vscode", "remoteUser must be vscode", errors)
    require(
        3001 in config.get("forwardPorts", []),
        "frontend port 3001 must be forwarded",
        errors,
    )
    require(
        5173 not in config.get("forwardPorts", []),
        "legacy frontend port 5173 must not be forwarded",
        errors,
    )

    features = config.get("features", {})
    require(bool(features), "Dev Container features must be declared", errors)
    for reference in features:
        require(
            bool(DIGEST_REF.search(reference)),
            f"feature is not digest pinned: {reference}",
            errors,
        )
    configured_feature_names = {reference.split("@", 1)[0] for reference in features}
    locked_features = lock.get("features", {})
    require(
        configured_feature_names == set(locked_features),
        "devcontainer-lock.json features must exactly match devcontainer.json",
        errors,
    )
    for name, metadata in locked_features.items():
        require(
            bool(DIGEST_REF.search(metadata.get("resolved", ""))),
            f"locked feature is not digest pinned: {name}",
            errors,
        )
        require(
            metadata.get("integrity", "").startswith("sha256:"),
            f"locked feature lacks integrity: {name}",
            errors,
        )

    feature_text = json.dumps(features)
    require('"version": "3.11"' in feature_text, "Python 3.11 must be pinned", errors)
    require(
        '"version": "22.22.2"' in feature_text, "Node.js 22.22.2 must be pinned", errors
    )
    require(
        '"pnpmVersion": "10.34.5"' in feature_text,
        "pnpm 10.34.5 must be pinned",
        errors,
    )

    dockerfile = (
        (dc / "Dockerfile").read_text(encoding="utf-8")
        if (dc / "Dockerfile").exists()
        else ""
    )
    from_lines = [
        line.split()[1] for line in dockerfile.splitlines() if line.startswith("FROM ")
    ]
    stage_names = {
        line.split()[line.split().index("AS") + 1]
        for line in dockerfile.splitlines()
        if line.startswith("FROM ") and "AS" in line.split()
    }
    external_images = [ref for ref in from_lines if ref not in stage_names]
    require(
        bool(external_images)
        and all(DIGEST_REF.search(ref) for ref in external_images),
        "every Dockerfile base image must be digest pinned",
        errors,
    )

    require(
        "user: vscode" in compose,
        "default services must run as non-root vscode",
        errors,
    )
    require(
        "no-new-privileges:true" in compose,
        "default services must enable no-new-privileges",
        errors,
    )
    require(
        "cap_drop:" in compose and "- ALL" in compose,
        "default services must drop Linux capabilities",
        errors,
    )
    require(
        "privileged:" not in compose,
        "default topology must not use privileged mode",
        errors,
    )
    require(
        "condition: service_healthy" in compose,
        "Dev Container dependencies must wait for health",
        errors,
    )
    require(
        "docker-data:" in compose and "dev-pnpm-store:" in compose,
        "Docker and dependency caches must use named volumes",
        errors,
    )
    require(
        "mem_limit:" in compose and "cpus:" in compose,
        "cloud containers must have CPU and memory bounds",
        errors,
    )
    require(
        "max-size:" in compose and "max-file:" in compose,
        "cloud containers must rotate logs",
        errors,
    )

    post_create = (
        (dc / "post-create.sh").read_text(encoding="utf-8")
        if (dc / "post-create.sh").exists()
        else ""
    )
    lifecycle = post_create + (
        (dc / "post-start.sh").read_text(encoding="utf-8")
        if (dc / "post-start.sh").exists()
        else ""
    )
    require(
        "pnpm install --frozen-lockfile" in post_create,
        "post-create must use the canonical frozen pnpm install",
        errors,
    )
    require("make setup" in post_create, "post-create must use make setup", errors)
    require(
        "|| true" not in lifecycle, "lifecycle scripts must not mask failures", errors
    )
    require(
        "cp .env.example .env" not in lifecycle,
        "lifecycle scripts must not create .env",
        errors,
    )
    require(
        "make migrate" not in lifecycle,
        "lifecycle scripts must not run migrations",
        errors,
    )
    require(
        not re.search(r"docker compose[^\n]*\bup\b", lifecycle),
        "lifecycle scripts must not start Compose stacks",
        errors,
    )

    cloud = (
        (dc / "docker-compose.cloud.yml").read_text(encoding="utf-8")
        if (dc / "docker-compose.cloud.yml").exists()
        else ""
    )
    for service in ("postgres", "redis", "neo4j"):
        block = re.search(
            rf"^  {service}:\n(?P<body>(?:    .*\n|\n)*)", cloud, re.MULTILINE
        )
        require(
            block is not None, f"cloud override must adjust canonical {service}", errors
        )
        if block:
            require(
                "image:" not in block.group("body")
                and "build:" not in block.group("body"),
                f"cloud override must not redefine {service}",
                errors,
            )
    require(
        cloud.count("condition: service_healthy") >= 3,
        "application services must use healthy data-service dependencies",
        errors,
    )

    tracked_secret_names = (".env", ".env.generated")
    for path in dc.rglob("*"):
        if path.is_file():
            require(
                path.name not in tracked_secret_names,
                f"secret environment file must not be committed: {path.relative_to(root)}",
                errors,
            )
    return errors


def run_external_validation(root: Path, errors: list[str]) -> None:
    devcontainer = shutil.which("devcontainer")
    docker = shutil.which("docker")
    if not devcontainer:
        errors.append(
            "Dev Container CLI is required (use --skip-cli-validation only for unit tests)"
        )
        return
    result = subprocess.run(
        [devcontainer, "read-configuration", "--workspace-folder", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        errors.append(
            f"Dev Container CLI validation failed:\n{result.stdout}{result.stderr}"
        )

    if not docker:
        errors.append("Docker Compose is required for configuration rendering")
        return
    combinations = {
        "devcontainer": ["-f", ".devcontainer/docker-compose.yml"],
        "devcontainer-local-socket": [
            "-f",
            ".devcontainer/docker-compose.yml",
            "-f",
            ".devcontainer/docker-compose.local-socket.yml",
        ],
        "cloud-production": [
            "-f",
            "infra/compose/docker-compose.prod.yml",
            "-f",
            ".devcontainer/docker-compose.cloud.yml",
        ],
        "cloud-full": [
            "-f",
            "infra/compose/docker-compose.full.yml",
            "-f",
            ".devcontainer/docker-compose.cloud.yml",
            "-f",
            ".devcontainer/docker-compose.cloud.full.yml",
        ],
    }
    render_env = os.environ.copy()
    for key, value in COMPOSE_RENDER_ENV_DEFAULTS.items():
        render_env.setdefault(key, value)
    for name, files in combinations.items():
        result = subprocess.run(
            [
                docker,
                "compose",
                "--project-directory",
                str(root / "infra/compose"),
                *files,
                "config",
                "--quiet",
            ],
            cwd=root,
            env=render_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.append(
                f"Compose render failed for {name}:\n{result.stdout}{result.stderr}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--skip-cli-validation", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    errors = validate_static(root)
    if not args.skip_cli_validation and not errors:
        run_external_validation(root, errors)
    if errors:
        print("Dev Container configuration contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Dev Container configuration contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
