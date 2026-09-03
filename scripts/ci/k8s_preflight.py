#!/usr/bin/env python3
"""Kubernetes preflight guardrails for CI/CD ephemeral deployments.

Checks:
1. Every workload in k8s/base has explicit rollout strategy.
2. Every workload container has readiness/liveness probes.
3. Every workload container has cpu/memory requests + limits.
4. All container and initContainer images are tag-pinned (no :latest).
5. Required non-optional secret refs exist in k8s/secrets.yml.template.
6. Layer 5 migration compatibility guardrails are present.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = ROOT / "k8s" / "base"
SECRETS_TEMPLATE = ROOT / "k8s" / "secrets.yml.template"
LAYER5_MIGRATIONS = ROOT / "services" / "layer5-ground-truth" / "src" / "layer5_ground_truth" / "migrations" / "versions"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}

# Explicit lifecycle classifications for layer-style service directories.
# Keep this list in sync with architecture docs (ADR-002).
SERVICE_LIFECYCLE_STATUS: dict[str, str] = {
    "layer1-ingestion": "production",
    "layer2-extraction": "production",
    "layer3-knowledge": "production",
    "layer4-agents": "production",
    "layer5-ground-truth": "production",
    "layer6-benchmarks": "production",
    "layer2-5-signal-refinery": "experimental",
    "layer7-billing": "internal",
}


@dataclass
class Violation:
    file: Path
    resource: str
    message: str

    def format(self) -> str:
        return f"{self.file.relative_to(ROOT)} :: {self.resource} :: {self.message}"


def load_yaml_documents(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    docs = [doc for doc in yaml.safe_load_all(content) if isinstance(doc, dict)]
    return docs


def walk_base_yaml_files() -> list[Path]:
    return sorted(BASE_DIR.glob("*.yml"))


def collect_template_secret_keys() -> dict[str, set[str]]:
    if not SECRETS_TEMPLATE.exists():
        return {}

    secret_keys: dict[str, set[str]] = {}
    for doc in load_yaml_documents(SECRETS_TEMPLATE):
        if doc.get("kind") != "Secret":
            continue
        name = doc.get("metadata", {}).get("name")
        if not name:
            continue
        keys = set((doc.get("data") or {}).keys()) | set((doc.get("stringData") or {}).keys())
        secret_keys[name] = keys
    return secret_keys


def image_is_pinned(image: str) -> bool:
    if "@sha256:" in image:
        return True
    if ":" not in image:
        return False
    tag = image.rsplit(":", 1)[1]
    return tag != "latest"


def check_workload(
    file_path: Path,
    doc: dict[str, Any],
    template_secrets: dict[str, set[str]],
) -> list[Violation]:
    violations: list[Violation] = []
    kind = doc.get("kind", "")
    metadata = doc.get("metadata", {})
    name = metadata.get("name", "<unnamed>")
    spec = doc.get("spec", {})
    resource = f"{kind}/{name}"

    # Rollout strategy checks
    if kind == "Deployment":
        strategy = spec.get("strategy")
        if not strategy:
            violations.append(Violation(file_path, resource, "missing spec.strategy"))
        else:
            if strategy.get("type") != "RollingUpdate":
                violations.append(Violation(file_path, resource, "spec.strategy.type must be RollingUpdate"))
            rolling = strategy.get("rollingUpdate") or {}
            if "maxUnavailable" not in rolling:
                violations.append(Violation(file_path, resource, "spec.strategy.rollingUpdate.maxUnavailable missing"))
            if "maxSurge" not in rolling:
                violations.append(Violation(file_path, resource, "spec.strategy.rollingUpdate.maxSurge missing"))
    if kind in {"StatefulSet", "DaemonSet"}:
        if not spec.get("updateStrategy"):
            violations.append(Violation(file_path, resource, "missing spec.updateStrategy"))

    pod_spec = ((spec.get("template") or {}).get("spec") or {})
    containers = pod_spec.get("containers") or []
    init_containers = pod_spec.get("initContainers") or []

    if not containers:
        violations.append(Violation(file_path, resource, "no containers found"))
        return violations

    # Liveness/Readiness/Resources on all runtime containers
    for container in containers:
        cname = container.get("name", "<unnamed>")
        cresource = f"{resource} container={cname}"
        if not container.get("livenessProbe"):
            violations.append(Violation(file_path, cresource, "missing livenessProbe"))
        if not container.get("readinessProbe"):
            violations.append(Violation(file_path, cresource, "missing readinessProbe"))

        resources = container.get("resources") or {}
        requests = resources.get("requests") or {}
        limits = resources.get("limits") or {}
        for req in ("cpu", "memory"):
            if req not in requests:
                violations.append(Violation(file_path, cresource, f"resources.requests.{req} missing"))
            if req not in limits:
                violations.append(Violation(file_path, cresource, f"resources.limits.{req} missing"))

    # Image tag pinning for runtime + init containers
    for container in [*containers, *init_containers]:
        cname = container.get("name", "<unnamed>")
        image = container.get("image", "")
        if not image:
            violations.append(Violation(file_path, f"{resource} container={cname}", "container image missing"))
            continue
        if not image_is_pinned(image):
            violations.append(
                Violation(
                    file_path,
                    f"{resource} container={cname}",
                    f"image must be pinned to non-latest tag or digest (found: {image})",
                )
            )

    # Secret reference compatibility
    for container in [*containers, *init_containers]:
        cname = container.get("name", "<unnamed>")
        env = container.get("env") or []
        for entry in env:
            value_from = entry.get("valueFrom") or {}
            ref = value_from.get("secretKeyRef") or {}
            if not ref:
                continue
            if ref.get("optional") is True:
                continue

            secret_name = ref.get("name")
            secret_key = ref.get("key")
            env_name = entry.get("name", "<unnamed-env>")
            if not secret_name or not secret_key:
                violations.append(
                    Violation(
                        file_path,
                        f"{resource} container={cname}",
                        f"{env_name} has incomplete secretKeyRef",
                    )
                )
                continue
            template_keys = template_secrets.get(secret_name)
            if template_keys is None:
                violations.append(
                    Violation(
                        file_path,
                        f"{resource} container={cname}",
                        f"{env_name} references missing secret in k8s/secrets.yml.template: {secret_name}",
                    )
                )
                continue
            if secret_key not in template_keys:
                violations.append(
                    Violation(
                        file_path,
                        f"{resource} container={cname}",
                        f"{env_name} references missing key in {secret_name}: {secret_key}",
                    )
                )

    return violations


def check_layer5_migration_guardrails(file_path: Path, doc: dict[str, Any]) -> list[Violation]:
    violations: list[Violation] = []
    if doc.get("kind") != "Deployment":
        return violations

    name = doc.get("metadata", {}).get("name")
    if name != "layer5-ground-truth":
        return violations

    spec = doc.get("spec", {})
    pod_spec = ((spec.get("template") or {}).get("spec") or {})
    init_containers = pod_spec.get("initContainers") or []
    migration = next((c for c in init_containers if c.get("name") == "migrate"), None)
    if not migration:
        violations.append(Violation(file_path, "Deployment/layer5-ground-truth", "missing migrate initContainer"))
        return violations

    cmd = " ".join(migration.get("command") or [])
    if "alembic" not in cmd or "upgrade" not in cmd or "head" not in cmd:
        violations.append(
            Violation(
                file_path,
                "Deployment/layer5-ground-truth",
                "migrate initContainer must run alembic upgrade head",
            )
        )

    if not LAYER5_MIGRATIONS.exists():
        violations.append(
            Violation(
                file_path,
                "Deployment/layer5-ground-truth",
                "services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions directory missing",
            )
        )
    else:
        version_files = list(LAYER5_MIGRATIONS.glob("*.py"))
        if not version_files:
            violations.append(
                Violation(
                    file_path,
                    "Deployment/layer5-ground-truth",
                    "no Alembic migration versions found",
                )
            )

    return violations


def check_layer_service_lifecycle_documentation(file_path: Path, doc: dict[str, Any]) -> list[Violation]:
    """Fail when a layer-style deployment is not explicitly lifecycle-classified."""
    if doc.get("kind") != "Deployment":
        return []

    name = (doc.get("metadata", {}) or {}).get("name")
    if not isinstance(name, str) or not name.startswith("layer"):
        return []

    if name not in SERVICE_LIFECYCLE_STATUS:
        allowed = ", ".join(sorted(SERVICE_LIFECYCLE_STATUS))
        return [
            Violation(
                file_path,
                f"Deployment/{name}",
                "undocumented layer service in deploy manifests; add explicit lifecycle classification "
                f"(experimental/internal/production). Known classified services: {allowed}",
            )
        ]

    status = SERVICE_LIFECYCLE_STATUS[name]
    if status not in {"experimental", "internal", "production"}:
        return [
            Violation(
                file_path,
                f"Deployment/{name}",
                f"invalid lifecycle status mapping: {status!r}",
            )
        ]

    return []


def main() -> int:
    files = walk_base_yaml_files()
    template_secrets = collect_template_secret_keys()
    violations: list[Violation] = []
    workload_count = 0

    for file_path in files:
        for doc in load_yaml_documents(file_path):
            kind = doc.get("kind")
            if kind not in WORKLOAD_KINDS:
                continue
            workload_count += 1
            violations.extend(check_workload(file_path, doc, template_secrets))
            violations.extend(check_layer5_migration_guardrails(file_path, doc))
            violations.extend(check_layer_service_lifecycle_documentation(file_path, doc))

    if workload_count == 0:
        print("FAIL No workloads found in k8s/base/*.yml")
        return 1

    if violations:
        print("FAIL Kubernetes preflight failed:")
        for violation in violations:
            print(f"  - {violation.format()}")
        return 1

    print(f"PASS Kubernetes preflight passed for {workload_count} workload(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
