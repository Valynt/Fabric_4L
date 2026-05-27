"""Static guardrails for shared FastAPI app factory DB/session ownership."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_APP_FACTORY_PATH = REPO_ROOT / "packages/shared/src/value_fabric/shared/fastapi_framework/app.py"


def test_create_fabric_app_module_does_not_introduce_db_session_side_effects() -> None:
    """Prevent shared app bootstrap from taking ownership of DB/session lifecycle."""

    assert SHARED_APP_FACTORY_PATH.exists(), (
        f"Shared app factory source not found at expected path: {SHARED_APP_FACTORY_PATH}. "
        "Update SHARED_APP_FACTORY_PATH if the file was moved."
    )
    source = SHARED_APP_FACTORY_PATH.read_text(encoding="utf-8")

    forbidden_markers = [
        "create_engine(",
        "sessionmaker(",  # also matches async_sessionmaker( as a substring
        "scoped_session(",
        "engine.dispose(",
        ".close_all(",
        "close_all_sessions(",
    ]

    violations = [marker for marker in forbidden_markers if marker in source]
    assert not violations, (
        "Shared app factory must remain DB/session-lifecycle agnostic. "
        f"Found forbidden DB/session markers in {SHARED_APP_FACTORY_PATH}: {violations}."
    )
