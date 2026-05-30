"""Regression guard for Layer 3 models canonical topology.

Architecture note: value_fabric/layer3/__init__.py is a path-redirect shim
that appends services/layer3-knowledge/src/ to __path__.  The canonical
models source is therefore services/layer3-knowledge/src/api/models.py —
there is no separate shim file at value_fabric/layer3/api/models.py.
"""

from pathlib import Path

# Canonical source — the redirect shim makes this the authoritative file.
CANONICAL_MODELS = Path("services/layer3-knowledge/src/api/models.py")


def test_layer3_canonical_models_is_substantive() -> None:
    """The canonical models file must define the expected Pydantic model classes."""
    canonical_source = CANONICAL_MODELS.read_text(encoding="utf-8")

    assert "class HealthResponse(BaseModel):" in canonical_source
    assert "class GraphRAGResponse(BaseModel):" in canonical_source
    assert "from pydantic import (" in canonical_source


def test_layer3_compat_models_remains_shim_only() -> None:
    """The canonical models file must not be a self-referential re-export shim.

    A re-export of value_fabric.layer3.api.models from within
    services/layer3-knowledge/src/api/models.py would be circular because
    value_fabric.layer3 redirects to services/layer3-knowledge/src/.
    """
    canonical_source = CANONICAL_MODELS.read_text(encoding="utf-8")

    assert "from src.api.models import *" not in canonical_source, (
        "Circular self-import detected: services/layer3-knowledge/src/api/models.py "
        "IS value_fabric.layer3.api.models via the path-redirect shim."
    )
    # Must contain substantive class definitions, not be an empty wrapper
    assert "class " in canonical_source
