"""Static contracts for Playwright journey module resolution and tenant paths."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPO_ROOT / "apps" / "web"
E2E_ROOT = WEB_ROOT / "e2e"
SOURCE_ROOT = WEB_ROOT / "src"
SOURCE_IMPORT = re.compile(r"from\s+['\"]@/([^'\"]+)['\"]")


def _source_module_exists(module: str) -> bool:
    candidate = SOURCE_ROOT / module
    return any(
        path.exists()
        for path in (
            candidate,
            candidate.with_suffix(".ts"),
            candidate.with_suffix(".tsx"),
            candidate / "index.ts",
            candidate / "index.tsx",
        )
    )


def test_e2e_source_alias_imports_resolve() -> None:
    unresolved: list[str] = []
    for path in E2E_ROOT.rglob("*.ts"):
        for module in SOURCE_IMPORT.findall(path.read_text(encoding="utf-8")):
            if not _source_module_exists(module):
                unresolved.append(f"{path.relative_to(REPO_ROOT)}: @/{module}")

    assert unresolved == []


def test_billing_journey_uses_environment_aware_tenant_paths() -> None:
    source = (E2E_ROOT / "journeys" / "j20-billing-entitlement-gates.spec.ts").read_text(
        encoding="utf-8"
    )

    assert "tenantScopedPath" in source
    assert "MOCK_TENANT_SLUG" not in source
