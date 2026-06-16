"""Architecture sentinel: Clerk SDK and config must not leak into L1\u2013L6.

The Phase 1 Clerk + Fabric4L integration places Clerk verification at the
``services/api`` gateway only. Downstream layers (L1\u2013L6) must trust only
the Fabric4L-signed internal AuthContext envelope; they MUST NOT import
the Clerk SDK or read ``CLERK_*`` configuration.

If you are seeing this test fail because you genuinely need a Clerk hook
in a downstream layer, write an ADR first \u2014 do not weaken this test.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source directories whose Python files must not reference Clerk.
# Includes services (L1-L6) and shared packages because shared code
# transitively reaches every layer.
LAYER_SOURCE_DIRS: tuple[Path, ...] = (
    REPO_ROOT / "services" / "layer1-ingestion" / "src",
    REPO_ROOT / "services" / "layer2-extraction" / "src",
    REPO_ROOT / "services" / "layer2-5-signal-refinery" / "src",
    REPO_ROOT / "services" / "layer3-knowledge" / "src",
    REPO_ROOT / "services" / "layer4-agents" / "src",
    REPO_ROOT / "services" / "layer5-ground-truth" / "src",
    REPO_ROOT / "services" / "layer6-benchmarks" / "src",
    REPO_ROOT / "packages" / "shared" / "src",
)

# Patterns that indicate Clerk leakage.
FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bimport\s+clerk\b"),
    re.compile(r"\bfrom\s+clerk[\.\s]"),
    re.compile(r"\bimport\s+svix\b"),
    re.compile(r"\bfrom\s+svix[\.\s]"),
    re.compile(r"\bCLERK_SECRET_KEY\b"),
    re.compile(r"\bCLERK_JWT_KEY\b"),
    re.compile(r"\bCLERK_WEBHOOK_SECRET\b"),
    re.compile(r"\bCLERK_ISSUER\b"),
    re.compile(r"\bCLERK_JWT_AUDIENCE\b"),
    re.compile(r"\bCLERK_AUTHORIZED_PARTIES\b"),
)

EXEMPT_FILE_NAMES: frozenset[str] = frozenset(
    {
        # DEBT: packages/shared/src/value_fabric/shared/identity/jwt.py
        # reads CLERK_JWT_AUDIENCE / CLERK_ISSUER / CLERK_JWT_ISSUER /
        # CLERK_JWKS_URL as
        # OIDC fallbacks. This should be refactored so callers pass OIDC
        # config explicitly instead of the shared module reading Clerk env.
        "jwt.py",
    }
)


def _iter_python_sources() -> list[Path]:
    files: list[Path] = []
    for root in LAYER_SOURCE_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            if any(part in {"__pycache__", "tests"} for part in path.parts):
                continue
            files.append(path)
    return files


def test_no_clerk_sdk_or_config_in_downstream_layers():
    """Fail loudly if any L1\u2013L6 source file references Clerk."""
    offenses: list[str] = []
    for path in _iter_python_sources():
        if path.name in EXEMPT_FILE_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                offenses.append(
                    f"{path.relative_to(REPO_ROOT)}:{line_no} \u2192 {pattern.pattern!r}"
                )

    assert not offenses, (
        "Clerk references found in downstream layers (L1\u2013L6). "
        "All Clerk integration must live in services/api only.\n"
        + "\n".join(offenses)
    )
