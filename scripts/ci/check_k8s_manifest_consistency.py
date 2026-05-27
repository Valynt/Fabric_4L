#!/usr/bin/env python3
"""CI guard: detect Kubernetes config drift across base/overlays/service manifests.

Checks each workload (Deployment/StatefulSet/DaemonSet) across:
- k8s/base
- k8s/overlays/**
- k8s/deployments/**

For the same workload name, this script validates:
1) Required env var keys are not dropped in production manifests.
2) Probe/resource/securityContext structures are consistent per container.

Intended usage:
    python scripts/ci/check_k8s_manifest_consistency.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
K8S_ROOT = ROOT / "k8s"
SCAN_ROOTS = [
    ROOT / "k8s" / "base",
    ROOT / "k8s" / "overlays",
    ROOT / "k8s" / "deployments",
]
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


@dataclass
class ServiceSnapshot:
    path: Path
    source: str
    service: str
    kind: str
    container: str
    required_env: set[str]
    probes: dict[str, Any]
    resources: dict[str, Any]
    pod_security: dict[str, Any]
    container_security: dict[str, Any]


@dataclass
class Violation:
    service: str
    container: str
    message: str
    paths: tuple[Path, ...]

    def format(self) -> str:
        rel = ", ".join(str(p.relative_to(ROOT)) for p in self.paths)
        return f"{self.service}/{self.container}: {self.message} [{rel}]"


def yaml_files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted([*root.rglob("*.yml"), *root.rglob("*.yaml")])


def load_docs(path: Path) -> list[dict[str, Any]]:
    docs = [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(doc, dict)]
    return docs


def classify_source(path: Path) -> str:
    rel = path.relative_to(ROOT)
    if rel.parts[:2] == ("k8s", "base"):
        return "base"
    if rel.parts[:2] == ("k8s", "overlays"):
        if len(rel.parts) >= 3 and rel.parts[2] == "production":
            return "overlay-prod"
        return "overlay"
    if rel.parts[:2] == ("k8s", "deployments"):
        if "prod" in rel.parts[2]:
            return "deployment-prod"
        return "deployment"
    return "other"


def canonical(obj: Any) -> str:
    return json.dumps(obj or {}, sort_keys=True, separators=(",", ":"))


def collect_required_env(container: dict[str, Any]) -> set[str]:
    required: set[str] = set()
    for entry in container.get("env") or []:
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        value_from = entry.get("valueFrom") or {}
        secret_ref = value_from.get("secretKeyRef") or {}
        config_ref = value_from.get("configMapKeyRef") or {}
        field_ref = value_from.get("fieldRef") or {}

        if secret_ref:
            if secret_ref.get("optional") is not True:
                required.add(name)
            continue
        if config_ref:
            if config_ref.get("optional") is not True:
                required.add(name)
            continue
        if field_ref:
            required.add(name)
            continue
        if "value" in entry:
            required.add(name)
    return required


def extract_snapshots(path: Path) -> list[ServiceSnapshot]:
    snapshots: list[ServiceSnapshot] = []
    source = classify_source(path)
    for doc in load_docs(path):
        kind = doc.get("kind")
        if kind not in WORKLOAD_KINDS:
            continue
        name = (doc.get("metadata") or {}).get("name")
        if not name:
            continue
        pod_spec = (((doc.get("spec") or {}).get("template") or {}).get("spec") or {})
        pod_security = pod_spec.get("securityContext") or {}
        for container in pod_spec.get("containers") or []:
            cname = container.get("name", "<unnamed>")
            probes = {
                "livenessProbe": container.get("livenessProbe") or {},
                "readinessProbe": container.get("readinessProbe") or {},
                "startupProbe": container.get("startupProbe") or {},
            }
            snapshots.append(
                ServiceSnapshot(
                    path=path,
                    source=source,
                    service=name,
                    kind=kind,
                    container=cname,
                    required_env=collect_required_env(container),
                    probes=probes,
                    resources=container.get("resources") or {},
                    pod_security=pod_security,
                    container_security=container.get("securityContext") or {},
                )
            )
    return snapshots


def compare_consistency(group: list[ServiceSnapshot]) -> list[Violation]:
    violations: list[Violation] = []
    by_container: dict[str, list[ServiceSnapshot]] = {}
    for snap in group:
        by_container.setdefault(snap.container, []).append(snap)

    for cname, snaps in by_container.items():
        base = snaps[0]
        for other in snaps[1:]:
            if canonical(base.probes) != canonical(other.probes):
                violations.append(
                    Violation(base.service, cname, "probe settings drift between manifests", (base.path, other.path))
                )
            if canonical(base.resources) != canonical(other.resources):
                violations.append(
                    Violation(base.service, cname, "resources settings drift between manifests", (base.path, other.path))
                )
            if canonical(base.container_security) != canonical(other.container_security):
                violations.append(
                    Violation(
                        base.service,
                        cname,
                        "container securityContext drift between manifests",
                        (base.path, other.path),
                    )
                )
            if canonical(base.pod_security) != canonical(other.pod_security):
                violations.append(
                    Violation(base.service, cname, "pod securityContext drift between manifests", (base.path, other.path))
                )

        base_required = set().union(*(s.required_env for s in snaps if s.source == "base"))
        prod_required = set().union(*(s.required_env for s in snaps if s.source in {"overlay-prod", "deployment-prod"}))
        if base_required:
            missing_prod = sorted(base_required - prod_required)
            if missing_prod:
                evidence = tuple(s.path for s in snaps)
                violations.append(
                    Violation(
                        base.service,
                        cname,
                        "production manifests missing required env keys: " + ", ".join(missing_prod),
                        evidence,
                    )
                )

    return violations


def main() -> int:
    snapshots: list[ServiceSnapshot] = []
    for root in SCAN_ROOTS:
        for path in yaml_files_under(root):
            snapshots.extend(extract_snapshots(path))

    by_service: dict[str, list[ServiceSnapshot]] = {}
    for snap in snapshots:
        by_service.setdefault(snap.service, []).append(snap)

    violations: list[Violation] = []
    for service, group in sorted(by_service.items()):
        if len(group) < 2:
            continue
        violations.extend(compare_consistency(group))

    if violations:
        print("FAIL: kubernetes manifest consistency checks failed:", file=sys.stderr)
        for violation in violations:
            print(f" - {violation.format()}", file=sys.stderr)
        return 1

    print("OK: kubernetes manifest consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
