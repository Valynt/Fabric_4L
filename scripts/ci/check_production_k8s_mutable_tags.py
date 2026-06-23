#!/usr/bin/env python3
"""Fail when production-facing Kubernetes manifests use :latest or :main.

Dev overlays may intentionally use mutable tags. Production inputs include the
shared base, canonical prod/staging env overlays, final prod/staging deployment
compositions, and legacy production overlays. The check is intentionally text-
based so it runs before rendering tools are installed.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = [
    ROOT / "k8s" / "base",
    ROOT / "k8s" / "envs" / "prod",
    ROOT / "k8s" / "envs" / "staging",
    ROOT / "k8s" / "overlays" / "production",
    ROOT / "k8s" / "overlays" / "staging",
]
SCAN_ROOTS.extend(sorted((ROOT / "k8s" / "deployments").glob("prod-*")))
SCAN_ROOTS.extend(sorted((ROOT / "k8s" / "deployments").glob("staging-*")))
SCAN_ROOTS.extend(sorted(ROOT.glob("k8s/*.yml")))
SCAN_ROOTS.extend(sorted(ROOT.glob("k8s/*.yaml")))

MUTABLE_IMAGE_RE = re.compile(r"^\s*image:\s*[^\s#'\"]+:(?:latest|main)(?:\s|$|['\"])")
MUTABLE_NEWTAG_RE = re.compile(r"^\s*newTag:\s*['\"]?(?:latest|main)['\"]?\s*(?:#.*)?$")


def yaml_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix in {".yaml", ".yml"} else []
    return sorted(p for p in path.rglob("*") if p.suffix in {".yaml", ".yml"})


def policy_wiring_violations() -> list[str]:
    violations: list[str] = []
    policy_kustomization = ROOT / "k8s" / "policy" / "kustomization.yaml"
    prod_kustomization = ROOT / "k8s" / "envs" / "prod" / "kustomization.yaml"
    if "kyverno-require-image-digests.yaml" not in policy_kustomization.read_text(encoding="utf-8"):
        violations.append("k8s/policy/kustomization.yaml must include kyverno-require-image-digests.yaml")
    if "../../policy" not in prod_kustomization.read_text(encoding="utf-8"):
        violations.append("k8s/envs/prod/kustomization.yaml must include ../../policy")
    return violations


def main() -> int:
    violations: list[str] = []
    seen: set[Path] = set()
    for root in SCAN_ROOTS:
        for path in yaml_files(root):
            if path in seen:
                continue
            seen.add(path)
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if MUTABLE_IMAGE_RE.search(line) or MUTABLE_NEWTAG_RE.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")

    wiring_violations = policy_wiring_violations()

    if violations or wiring_violations:
        if wiring_violations:
            print("Kyverno digest policy wiring is incomplete:", file=sys.stderr)
            for violation in wiring_violations:
                print(f"- {violation}", file=sys.stderr)
            print("", file=sys.stderr)

        print("Production-facing Kubernetes manifests must not use :latest or :main image tags.", file=sys.stderr)
        print("Mutable image tags are allowed only in dev-specific overlays such as k8s/envs/dev.", file=sys.stderr)
        print("Use image digests instead, for example repo@sha256:<digest> or a Kustomize digest field.", file=sys.stderr)
        print("", file=sys.stderr)
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1

    print("OK: no :latest or :main image tags in production-facing Kubernetes manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
