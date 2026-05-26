#!/usr/bin/env python3
"""Fail when deployable service count and Dockerfile-backed image definitions diverge."""

from __future__ import annotations

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]


def deployable_service_dirs() -> set[str]:
    services_dir = ROOT / "services"
    deployable = set()
    for pyproject in services_dir.glob("*/pyproject.toml"):
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
    compose = yaml.safe_load((ROOT / "docker-compose.full.yml").read_text())
    service_defs = compose.get("services", {})
    found = set()
    for svc in service_defs.values():
        build = svc.get("build") if isinstance(svc, dict) else None
        if isinstance(build, dict):
            ctx = str(build.get("context", ""))
            dockerfile = str(build.get("dockerfile", "Dockerfile"))
            if ctx.startswith("./services/"):
                found.add(ctx.removeprefix("./services/"))
                continue
            if "services/" in dockerfile:
                suffix = dockerfile.split("services/", 1)[1]
                found.add(suffix.split("/", 1)[0])
    return found


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
