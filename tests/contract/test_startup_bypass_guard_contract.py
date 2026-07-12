from __future__ import annotations

from pathlib import Path

import pytest
from value_fabric.shared.startup import reject_insecure_bypass_in_production

REPO_ROOT = Path(__file__).resolve().parents[2]
BYPASS_FLAG_TOKENS = (
    "ALLOW_INSECURE_DEV_AUTH_BYPASS",
    "DEV_AUTH_BYPASS",
    "AUTH_BYPASS_ENABLED",
    "ALLOW_DEV_AUTH_BYPASS",
)


def _service_entrypoint_paths(service_root: Path) -> list[Path]:
    return sorted(service_root.glob("src/**/api/main.py"))


def _settings_modules_with_bypass_flags(service_root: Path) -> list[Path]:
    settings_files = sorted(service_root.glob("src/**/*.py"))
    flagged: list[Path] = []
    for path in settings_files:
        if "settings" not in path.name and path.name != "config.py":
            continue
        text = path.read_text(encoding="utf-8")
        if any(token in text for token in BYPASS_FLAG_TOKENS):
            flagged.append(path)
    return flagged


def test_services_with_bypass_flags_apply_shared_startup_guard() -> None:
    services_dir = REPO_ROOT / "services"
    service_dirs = [p for p in sorted(services_dir.iterdir()) if p.is_dir()]

    missing: list[str] = []
    for service_root in service_dirs:
        flagged_settings = _settings_modules_with_bypass_flags(service_root)
        if not flagged_settings:
            continue

        entrypoints = _service_entrypoint_paths(service_root)
        if not entrypoints:
            missing.append(f"{service_root.name}: no api/main.py entrypoint found")
            continue

        for entrypoint in entrypoints:
            text = entrypoint.read_text(encoding="utf-8")
            if "reject_insecure_bypass_in_production" not in text:
                missing.append(
                    f"{service_root.name}: {entrypoint.relative_to(REPO_ROOT)} missing startup guard; "
                    f"flagged settings: {[str(p.relative_to(REPO_ROOT)) for p in flagged_settings]}"
                )

    assert not missing, "\n".join(missing)


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_shared_startup_guard_rejects_bypass_flags_in_production_like(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "true")

    with pytest.raises(RuntimeError, match="cannot enable auth bypass flags"):
        reject_insecure_bypass_in_production(service_name="contract-test")
