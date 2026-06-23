"""Architecture contract for Layer 3 API models module.

The value_fabric.layer3 namespace is a path-redirect shim: its __init__.py
appends services/layer3-knowledge/src/ to __path__, making the service tree
the canonical source.  services/layer3-knowledge/src/api/models.py is therefore
the canonical Pydantic models module — it must define model classes and must
not be an empty re-export wrapper.
"""

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_PATH = REPO_ROOT / "services/layer3-knowledge/src/api/models.py"


def test_layer3_models_is_substantive_canonical_module() -> None:
    """The Layer 3 API models file must define Pydantic model classes.

    Since value_fabric.layer3 redirects to services/layer3-knowledge/src/,
    this file IS the canonical source and must contain real model definitions,
    not a self-referential re-export (which would be circular).
    """
    content = MODELS_PATH.read_text(encoding="utf-8")
    tree = ast.parse(content)
    class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    assert class_names, (
        f"{MODELS_PATH.relative_to(REPO_ROOT)} must define at least one Pydantic model class. "
        "This file is the canonical Layer 3 API models source."
    )
    # Must not be a circular self-import shim
    assert "from src.api.models import *" not in content, (
        "Circular self-import detected: this file IS value_fabric.layer3.api.models "
        "via the path-redirect shim and cannot re-export itself."
    )
