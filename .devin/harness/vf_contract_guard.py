"""Value Fabric pre-edit contract guard.

Static checks that run before an agent edits code, to catch drift
before it enters the working tree.
"""
import subprocess
import sys
from pathlib import Path
from typing import List

from vf_layer_router import warn_on_cross_layer

__all__ = ["check_openapi_drift", "check_frontend_types_sync", "pre_edit_guard"]

ROOT = Path(__file__).parent.parent.parent


def check_openapi_drift() -> list:
    """Run the OpenAPI diff script when API route files are in scope."""
    script = ROOT / "scripts" / "analyze-openapi-dil-diff.py"
    if not script.exists():
        return []
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT, capture_output=True, text=True, timeout=60
        )
    except (subprocess.TimeoutExpired, OSError):
        return ["OPENAPI_CHECK_TIMEOUT: Could not run OpenAPI drift check within 60s."]

    if result.returncode != 0:
        return [f"OPENAPI_DRIFT: {result.stdout.strip()}\n{result.stderr.strip()}"]
    return []


def check_frontend_types_sync() -> List[str]:
    """Emit an advisory when apps/web/ is in scope.

    We do not auto-run npm scripts because they may need a dev server.
    The advisory prompts the user or agent to verify type sync manually.
    """
    if not (ROOT / "apps" / "web").exists():
        return []
    return [
        "FRONTEND_TYPE_SYNC: apps/web/ is in scope. "
        "Ensure generated API types are up to date. "
        "Run: pnpm --dir apps/web typecheck"
    ]


def pre_edit_guard(file_paths: List[str], intent: str) -> List[str]:
    """Run all pre-edit checks. Returns list of blocking issues.

    Non-empty list means the agent should pause and surface warnings.
    """
    issues = []

    # Layer-boundary checks (advisory)
    issues.extend(warn_on_cross_layer(file_paths, intent))

    # OpenAPI drift when API routes are touched
    normalized = [p.replace("\\", "/").lower() for p in file_paths]
    if any("api/routes" in p for p in normalized):
        issues.extend(check_openapi_drift())

    # Frontend type sync when apps/web/ is touched
    if any(p.startswith("apps/web/") for p in normalized):
        issues.extend(check_frontend_types_sync())

    return issues


def main():
    """CLI entry point: print pre-edit guard results."""
    import os

    intent = os.environ.get("TASK", "")
    files_raw = os.environ.get("FILES", "")
    file_paths = [p.strip() for p in files_raw.split(",") if p.strip()]

    if not intent:
        print("Usage: TASK='<intent>' FILES='path1,path2' python vf_contract_guard.py")
        sys.exit(1)

    issues = pre_edit_guard(file_paths, intent)

    if issues:
        print("Pre-edit guard issues found:")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    else:
        print("Pre-edit guard passed.")


if __name__ == "__main__":
    main()
