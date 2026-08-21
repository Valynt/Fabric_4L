#!/usr/bin/env python3
"""Guard: Infisical secret paths must use the canonical by-layer taxonomy.

Fabric_4L standardizes on a single by-layer Infisical path schema
(/shared, /infra, /layerN-*, /apps/web, /monitoring, /ci). The legacy
by-consumer schema (/app, /auth, /database, /integrations, /llm, /storage)
is retired. This guard fails any new occurrence of a legacy Infisical path in
active code, config, agent skills, or docs.

Detection keys on Infisical-specific markers so unrelated uses of these words
(e.g. PYTHONPATH: /app container paths, frontend routes, hostnames) are not
flagged:
  --path=/legacy        (infisical CLI)
  secretPath: /legacy   (InfisicalSecret CRDs / API payloads)
  secretsPath: /legacy  (Infisical API payloads)
  "path": "/legacy"     (.infisical.json secretPaths blocks)
  Infisical path: /legacy (.env.example-style annotations)
  fix_path_for_git_bash('/legacy') and '/legacy' in infisical command examples

Migration/archive contexts are allowlisted via SKIP_PREFIXES.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Legacy by-consumer Infisical roots that are retired in favor of by-layer.
LEGACY_PATHS = (
    "app",
    "auth",
    "database",
    "integrations",
    "llm",
    "storage",
)

# Each entry is a (marker, regex) pair. The regex captures the Infisical
# path token that immediately follows the marker. We then check whether that
# token starts with a legacy root.
MARKER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("--path=", re.compile(r"--path=(/{1,2}[A-Za-z0-9_\-/]+)")),
    ("--path ", re.compile(r"--path\s+(/{1,2}[A-Za-z0-9_\-/]+)")),
    (
        "secretPath",
        re.compile(r"secretPath[\"']?\s*[:=]\s*[\"']?(/{1,2}[A-Za-z0-9_\-/]+)"),
    ),
    (
        "secretsPath",
        re.compile(r"secretsPath[\"']?\s*[:=]\s*[\"']?(/{1,2}[A-Za-z0-9_\-/]+)"),
    ),
    # .infisical.json secretPaths block: legacy root appears as a JSON KEY
    # inside the object, e.g. {"secretPaths":{"llm":{"dev":"/llm"}}} or
    # "secretPaths": { "/app": { ... } }. The path token is the key, not a
    # value, so the value-oriented secretPath/secretsPath regexes above do
    # not match. The key may be quoted-with-slash ("/llm"), quoted-bare
    # ("llm"), or bare (llm); capture with/without leading slash and let
    # _starts_with_legacy_root normalise.
    (
        "secretPaths block key",
        re.compile(
            r"secretPaths[\"']?\s*[:=]\s*[\"']?\s*\{\s*[\"']?/*([A-Za-z0-9_\-]+)"
        ),
    ),
    ("Infisical path:", re.compile(r"Infisical path:\s*(/{1,2}[A-Za-z0-9_\-/]+)")),
    (
        "fix_path_for_git_bash(",
        re.compile(r"fix_path_for_git_bash\(\s*[\"'](/{1,2}[A-Za-z0-9_\-/]+)"),
    ),
]


def _strip_double_slash(token: str) -> str:
    # Git Bash double-slash form //path → /path
    if token.startswith("//"):
        return "/" + token[2:]
    return token


def _starts_with_legacy_root(path: str) -> bool:
    """True if the path is a legacy root or has a legacy first segment.

    Accepts both leading-slash forms (``/llm``) and bare-key forms
    (``llm``) because the ``secretPaths`` block stores the root as a JSON
    key that may be quoted without a slash.
    """
    # Normalise to a single leading slash so both "llm" and "/llm" match.
    p = _strip_double_slash(path).strip("'\"")
    if not p.startswith("/"):
        p = "/" + p
    for legacy in LEGACY_PATHS:
        root = "/" + legacy
        if p == root or p.startswith(root + "/"):
            return True
    return False


def is_legacy_infisical_ref(line: str) -> bool:
    """True if the line contains a legacy path under an Infisical marker.

    We only flag paths that appear in an Infisical-specific context
    (--path=, secretPath, secretsPath, Infisical path:, fix_path_for_git_bash)
    so unrelated uses of these words (HTTP route paths like /auth/clerk/tenant,
    ASGI scope "path" keys, container PYTHONPATH=/app) are not flagged.
    """
    for _marker, rx in MARKER_PATTERNS:
        for m in rx.finditer(line):
            if _starts_with_legacy_root(m.group(1)):
                return True
    return False


SCAN_DIRS = (
    "services",
    "scripts",
    "tests",
    ".devin",
    "docs",
    "k8s",
    "config",
    "contracts",
)
# Root-level files that are active secret-path sources but live outside the
# SCAN_DIRS (which are all directories). These are scanned in addition to the
# directory walk so drift cannot return through a root runtime/config entry.
ROOT_FILES = (
    ".infisical.json",
    ".env.example",
    "package.json",
)
SKIP_PREFIXES = (
    "docs/archive/",
    "docs/_SOURCE OF TRUTH/",
    ".venv/",
    "node_modules/",
    "apps/web/node_modules/",
)
# Self-allowlist: this guard + its own test must reference the legacy names.
SKIP_FILES = {
    "scripts/ci/check_infisical_path_schema.py",
    "tests/ci/test_check_infisical_path_schema.py",
}

# Paths under these dirs are treated as historical/migration contexts.
ARCHIVAL_PREFIXES = (
    "docs/archive/",
    "archive/",
    "docs/_SOURCE OF TRUTH/",
)


def should_scan(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    return not (
        any(rel.startswith(s) for s in SKIP_PREFIXES)
        or rel in SKIP_FILES
        or path.is_dir()
        or "__pycache__" in path.parts
        or path.suffix == ".pyc"
    )


def is_archival(rel: str) -> bool:
    return any(rel.startswith(p) for p in ARCHIVAL_PREFIXES)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    violations: list[tuple[str, int, str]] = []
    for d in SCAN_DIRS:
        base = root / d
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if not should_scan(f, root):
                continue
            rel = f.relative_to(root).as_posix()
            if is_archival(rel):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                if is_legacy_infisical_ref(line):
                    violations.append((rel, i, line.strip()))

    # Also scan root-level files that are active secret-path sources but live
    # outside the SCAN_DIRS (which are all directories). .env.example is the
    # mapping source of truth and package.json carries the runtime infisical
    # commands, so both must be covered to actually prevent drift.
    for name in ROOT_FILES:
        f = root / name
        if f.exists() and should_scan(f, root):
            rel = f.relative_to(root).as_posix()
            if is_archival(rel):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(text.splitlines(), 1):
                if is_legacy_infisical_ref(line):
                    violations.append((rel, i, line.strip()))

    if violations:
        print("❌ Legacy Infisical secret paths detected (use by-layer paths instead):")
        print("   Canonical paths: /shared /infra /layerN-* /apps/web /monitoring /ci")
        for rel, i, line in violations:
            print(f"   - {rel}:{i}: {line}")
        return 1

    print("✅ PASS: no legacy Infisical secret paths found in active code/config/docs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
