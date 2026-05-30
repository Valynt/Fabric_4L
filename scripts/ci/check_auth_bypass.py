#!/usr/bin/env python3
"""Production auth bypass prevention gate.

Scans production-like deployment manifests for insecure authentication bypass
flags and weak defaults that could silently disable auth in staging/prod.
"""

from __future__ import annotations

from pathlib import Path
import sys

BYPASS_FLAGS = (
    "DEV_AUTH_BYPASS",
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "ALLOW_DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
)

WEAK_PATTERNS = (
    'VITE_ENABLE_MOCK_FALLBACK: "true"',
    "VITE_ENABLE_MOCK_FALLBACK: true",
    "dev-local-secret-do-not-use-in-production",
    "dev-local-service-auth-secret",
)

SCAN_ROOTS = (
    Path("k8s/envs/prod"),
    Path("k8s/envs/staging"),
    Path("k8s/deployments/prod-gateway-api"),
    Path("k8s/deployments/prod-istio"),
    Path("k8s/deployments/prod-nginx"),
)

EXPLICIT_FILES = (
    Path("docker-compose.live.yml"),
    Path("docker-compose.full.yml"),
    # docker-compose.release-smoke.yml is intentionally excluded from this gate.
    # It sets DEV_AUTH_BYPASS=true and ALLOW_INSECURE_DEV_AUTH_BYPASS set to true to
    # enable the CI smoke stack, which runs against real service contracts but is
    # never deployed to production or staging. The runtime enforces that these
    # flags are rejected when ENVIRONMENT is production-like
    # (assert_safe_jwt_and_bypass_configuration in auth_mode.py).
)


def yaml_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted([*root.rglob("*.yml"), *root.rglob("*.yaml")])


PY_SCAN_ROOTS = (
    Path("services"),
    Path("packages"),
    Path("apps"),
    Path("value_fabric"),
)

# Python source patterns that must never appear outside of docstrings/comments.
# DevAuthBypassMiddleware was removed (F-23) — re-introduction must be caught.
FORBIDDEN_PY_PATTERNS = (
    "DevAuthBypassMiddleware(",   # instantiation
    "add_middleware(DevAuthBypassMiddleware",  # registration
)


def py_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.py"))


def _is_code_line(line: str) -> bool:
    """Return True if the line is executable code (not a comment or docstring)."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#") and not stripped.startswith('"""') and not stripped.startswith("'''")


def main() -> int:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        files.extend(yaml_files(root))
    files.extend([p for p in EXPLICIT_FILES if p.exists()])

    errors: list[str] = []
    for path in sorted(set(files)):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            normalized = line.strip().lower()
            for flag in BYPASS_FLAGS:
                if flag in line and any(tok in normalized for tok in ("true", "i_understand_risk")):
                    errors.append(
                        f"{path}:{line_no} contains forbidden bypass flag assignment: {line.strip()}"
                    )
            for pattern in WEAK_PATTERNS:
                if pattern in line:
                    errors.append(f"{path}:{line_no} contains insecure pattern: {pattern}")

    # Scan Python source for re-introduction of removed bypass class (F-23).
    py_source_files: list[Path] = []
    for root in PY_SCAN_ROOTS:
        py_source_files.extend(py_files(root))

    for path in sorted(set(py_source_files)):
        if "__pycache__" in str(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(lines, start=1):
            if not _is_code_line(line):
                continue
            for pattern in FORBIDDEN_PY_PATTERNS:
                if pattern in line:
                    errors.append(
                        f"{path}:{line_no} re-introduces removed bypass class: {line.strip()}"
                    )

    if errors:
        print("ERROR: Production auth bypass check failed.\n")
        for error in errors:
            print(f" - {error}")
        print("\nRemove bypass flags and weak defaults from production/staging overlays and manifests.")
        return 1

    print("Production auth bypass check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
