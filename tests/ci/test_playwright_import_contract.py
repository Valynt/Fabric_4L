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


def test_live_seed_issues_validation_session_directly_against_backend() -> None:
    source = (REPO_ROOT / "scripts" / "db" / "seed-e2e-data.ts").read_text(encoding="utf-8")
    function = source.split("async function issueValidationSessionCookieHeader()", 1)[1].split(
        "async function probeBackendEndpoint", 1
    )[0]

    assert "if (!BASE_URL)" in function
    assert r"`${BASE_URL.replace(/\/$/, '')}/v1/validation/session`" in function
    assert "LIVE_FRONTEND_URL" not in function
