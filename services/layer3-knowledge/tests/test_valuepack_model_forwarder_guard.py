"""Guardrails ensuring ValuePack models are defined in the canonical source."""

from pathlib import Path


def test_service_valuepack_module_is_canonical_source() -> None:
    module_path = Path("services/layer3-knowledge/src/models/valuepack.py")
    content = module_path.read_text(encoding="utf-8")

    # The canonical module must define actual models, not delegate to a shim
    assert "BaseModel" in content or "class " in content, (
        "services/layer3-knowledge/src/models/valuepack.py must be the canonical "
        "source defining ValuePack models directly (not a shim forwarder)"
    )
    # Must not reference the removed value_fabric.layer3 shim
    assert "from value_fabric.layer3" not in content, (
        "services/layer3-knowledge/src/models/valuepack.py must not import from "
        "the removed value_fabric.layer3 shim namespace"
    )
