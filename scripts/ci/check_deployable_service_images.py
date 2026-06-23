#!/usr/bin/env python3
"""Fail when deployable service count and Dockerfile-backed image definitions diverge."""

from __future__ import annotations

from pathlib import Path
import sys
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[2]


def is_deployable_service(pyproject: Path) -> bool:
    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    value_fabric = metadata.get("tool", {}).get("value_fabric", {})
    return value_fabric.get("deployable", True) is not False


def deployable_service_dirs() -> set[str]:
    services_dir = ROOT / "services"
    deployable = set()
    for pyproject in services_dir.glob("*/pyproject.toml"):
        if not is_deployable_service(pyproject):
            continue
        deployable.add(pyproject.parent.name)
    return deployable


def dockerfile_backed_service_dirs() -> set[str]:
    deployable = deployable_service_dirs()
    out = set()
    for service in deployable:
        if list((ROOT / "services" / service).glob("Dockerfile*")):
            out.add(service)
    return out


def compose_defined_services() -> set[str]:
    compose = yaml.safe_load((ROOT / "infra/compose/docker-compose.full.yml").read_text(encoding="utf-8")) or {}
    service_defs = compose.get("services", {}) if isinstance(compose, dict) else {}
    found = set()
    for svc in service_defs.values():
        build = svc.get("build") if isinstance(svc, dict) else None
        if isinstance(build, str):
            service = service_name_from_services_path(build)
            if service:
                found.add(service)
        if isinstance(build, dict):
            ctx = str(build.get("context", ""))
            dockerfile = str(build.get("dockerfile", "Dockerfile"))
            service = service_name_from_services_path(ctx)
            if service:
                found.add(service)
                continue
            service = service_name_from_services_path(dockerfile)
            if service:
                found.add(service)
    return found


def service_name_from_services_path(value: str) -> str | None:
    normalized = value.replace("\\", "/").lstrip("./")
    marker = "services/"
    if normalized.startswith(marker):
        suffix = normalized.removeprefix(marker)
    elif f"/{marker}" in normalized:
        suffix = normalized.split(f"/{marker}", 1)[1]
    else:
        return None
    service = suffix.split("/", 1)[0]
    return service or None


def main() -> int:
    deployable = deployable_service_dirs()
    dockerfile_backed = dockerfile_backed_service_dirs()
    composed = compose_defined_services()

    errors: list[str] = []
    if deployable != dockerfile_backed:
        errors.append(
            f"Dockerfile mismatch. missing={sorted(deployable - dockerfile_backed)}, extra={sorted(dockerfile_backed - deployable)}"
        )
    if deployable != composed:
        errors.append(
            f"Compose build mismatch. missing={sorted(deployable - composed)}, extra={sorted(composed - deployable)}"
        )

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print(f"OK: {len(deployable)} deployable services have Dockerfiles and compose build definitions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
