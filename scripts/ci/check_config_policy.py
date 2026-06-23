#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_policy(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)



K8S_PRODUCTION_TARGETS = (
    "k8s/base",
    "k8s/overlays/staging",
    "k8s/overlays/production",
)
BYPASS_FLAGS = ("DEV_AUTH_BYPASS", "ALLOW_INSECURE_DEV_AUTH_BYPASS", "ALLOW_DEV_AUTH_BYPASS", "AUTH_BYPASS_ENABLED")


def _scan_k8s_manifests_for_bypass_flags(violations: list[str]) -> int:
    scanned = 0
    for target in K8S_PRODUCTION_TARGETS:
        root = ROOT / target
        if not root.exists():
            continue
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in {".yml", ".yaml"}:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            scanned += 1
            rel = file_path.relative_to(ROOT).as_posix()
            for idx, line in enumerate(text.splitlines(), start=1):
                for flag in BYPASS_FLAGS:
                    if flag in line:
                        violations.append(
                            f"{rel}:{idx} base/staging/production Kubernetes manifests must not reference `{flag}`"
                        )
    return scanned


def main() -> int:
    p = argparse.ArgumentParser(description="Enforce repository config policy for dev-only insecure flags")
    p.add_argument("--policy", default="contracts/config-policy/config_policy.yml")
    args = p.parse_args()

    policy = load_policy(ROOT / args.policy)
    scan_patterns: list[str] = policy["scan_paths"]
    scoped_markers = [m.lower() for m in policy.get("required_scope_markers", [])]

    violations: list[str] = []
    scanned = 0

    files: list[Path] = []
    for pattern in scan_patterns:
        files.extend(ROOT.glob(pattern))

    for file_path in sorted(set(files)):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(ROOT).as_posix()
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        scanned += 1

        for rule in policy["rules"]:
            flag = rule["flag"]
            allowlist = rule.get("dev_only_allowlist", [])
            if matches_any(rel, allowlist):
                continue

            regex = re.compile(rf"{re.escape(flag)}\s*[:=]\s*[\"']?(true|1|yes)[\"']?", re.IGNORECASE)
            for m in regex.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                line = text.splitlines()[line_no-1].lstrip()
                if line.startswith("#"):
                    continue
                violations.append(
                    f"{rel}:{line_no} disallowed `{flag}=true` outside approved dev-only locations"
                )

        for scoped in policy.get("scoped_allowances", []):
            flag = scoped["flag"]
            if not matches_any(rel, scoped.get("paths", [])):
                continue
            regex = re.compile(rf"{re.escape(flag)}\s*[:=]\s*[\"']?(true|1|yes)[\"']?", re.IGNORECASE)
            if regex.search(text) and not any(marker in lower for marker in scoped_markers):
                violations.append(
                    f"{rel}: `{flag}=true` requires explicit environment scoping marker: {policy['required_scope_markers']}"
                )

    k8s_scanned = _scan_k8s_manifests_for_bypass_flags(violations)
    print(f"Scanned files: {scanned} (policy files) + {k8s_scanned} (k8s manifests)")
    if violations:
        print("FAIL: config policy violations detected")
        for v in violations:
            print(f"- {v}")
        return 1

    print("PASS: no config policy violations found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
