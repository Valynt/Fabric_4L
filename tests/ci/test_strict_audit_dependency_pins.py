from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

STRICT_AUDITED_SERVICES = (
    "layer2-extraction",
    "layer3-knowledge",
    "layer6-benchmarks",
    "layer4-agents",
)

VULNERABLE_PINS = (
    ("click", "8.3.2"),
    ("setuptools", "81.0.0"),
    ("ecdsa", "0.19.2"),
)


def test_strict_audit_lockfiles_do_not_pin_known_vulnerable_packages() -> None:
    for service in STRICT_AUDITED_SERVICES:
        uv_lock = (REPO_ROOT / "services" / service / "uv.lock").read_text(encoding="utf-8")

        for package, version in VULNERABLE_PINS:
            assert f'name = "{package}"\nversion = "{version}"' not in uv_lock, service
