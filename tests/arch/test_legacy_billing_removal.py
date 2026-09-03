"""COMPAT-BILL-001 ratchets: the legacy `services/billing/` package must stay gone.

Governance warning R3 flagged two parallel billing services encoding the same
money-domain knowledge. Resolution: the legacy `services/billing/` package had
zero production consumers and was deleted on 2026-08-27 (see the
compatibility-debt-registry entry COMPAT-BILL-001). The phase-1
`services/layer7-billing/` stub (which duplicated the same money-domain
surface) was removed 2026-09-01 as part of the billing deduplication effort.
Billing ownership today is a single canonical owner:

- `services/layer4-agents/.../billing_service.py` — Stripe customer/
  subscription/usage/webhook membership domain
- `services/layer4-agents/.../api/routes/billing*.py` — billing API routes

These tests ratchet the removal so neither the parallel package nor the stub
service can be reintroduced and so no code can begin importing a top-level
`billing` or `layer7_billing` runtime package.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

LEGACY_BILLING_DIR = REPO_ROOT / "services" / "billing"
LAYER7_BILLING_DIR = REPO_ROOT / "services" / "layer7-billing"

SKIP_DIR_NAMES = {".venv", "venv", "__pycache__", "migrations", "node_modules"}

# Deploy-surface files that must not reference the legacy billing package.
DEPLOY_SURFACE_FILES = [
    "Makefile",
    "scripts/ci/build-reproducibility-check.sh",
    "infra/compose/docker-compose.dev.yml",
    "infra/compose/docker-compose.full.yml",
]


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*.py")
        if not any(part in SKIP_DIR_NAMES for part in path.relative_to(REPO_ROOT).parts)
    ]


def _import_roots(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        # Skip files that cannot be parsed (e.g. newer-Python syntax or BOM
        # issues introduced upstream); this ratchet only guards `billing`.
        return []
    roots: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend((node.lineno, alias.name.split(".", 1)[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.append((node.lineno, node.module.split(".", 1)[0]))
    return roots


def test_legacy_billing_package_is_not_reintroduced() -> None:
    assert not LEGACY_BILLING_DIR.exists(), (
        "COMPAT-BILL-001: legacy services/billing/ package was removed 2026-08-27 and must "
        "not be reintroduced; canonical ownership is the layer4-agents billing runtime "
        "(services/layer4-agents/src/layer4_agents/services/billing_service.py)"
    )


def test_layer7_billing_service_is_not_reintroduced() -> None:
    assert not LAYER7_BILLING_DIR.exists(), (
        "R3 billing dedup: services/layer7-billing/ was removed 2026-09-01 and must not be "
        "reintroduced; billing ownership is a single canonical owner in layer4-agents"
    )


def test_no_code_imports_legacy_top_level_billing_package() -> None:
    violations: list[str] = []
    scan_roots = [
        REPO_ROOT / "services",
        REPO_ROOT / "packages",
        REPO_ROOT / "tests",
        REPO_ROOT / "scripts",
    ]
    for root in scan_roots:
        for path in _python_files(root):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            for line_number, imported_root in _import_roots(path):
                if imported_root == "billing":
                    violations.append(
                        f"{rel_path}:{line_number} imports top-level 'billing'; "
                        "use services/layer4-agents/src/layer4_agents/services/billing_service.py "
                        "instead (COMPAT-BILL-001)"
                    )
                if imported_root == "layer7_billing":
                    violations.append(
                        f"{rel_path}:{line_number} imports removed 'layer7_billing'; "
                        "use services/layer4-agents/src/layer4_agents/services/billing_service.py "
                        "instead (R3 billing dedup)"
                    )

    assert not violations, "\n".join(violations)


def test_legacy_billing_package_absent_from_deploy_surfaces() -> None:
    violations: list[str] = []
    for relative in DEPLOY_SURFACE_FILES:
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "services/billing" in text:
            violations.append(f"{relative} still references services/billing (COMPAT-BILL-001)")

    assert not violations, "\n".join(violations)
