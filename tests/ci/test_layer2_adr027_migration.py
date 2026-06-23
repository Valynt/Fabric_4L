from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER2_SERVICE_ROOT = REPO_ROOT / "services" / "layer2-extraction"


def test_layer2_full_dockerfile_does_not_recreate_removed_value_fabric_namespace() -> None:
    dockerfile = (LAYER2_SERVICE_ROOT / "Dockerfile.full").read_text(encoding="utf-8")

    assert "COPY value_fabric/" not in dockerfile
    assert "value_fabric/layer2" not in dockerfile


def test_layer2_readme_points_contributors_to_service_tree() -> None:
    readme = (LAYER2_SERVICE_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Canonical runtime implementation (edit here):** `services/layer2-extraction/src/`" in readme
    assert "Canonical runtime implementation (edit here):** `value_fabric/layer2/`" not in readme
    assert "re-export `value_fabric.layer2.*`" not in readme
