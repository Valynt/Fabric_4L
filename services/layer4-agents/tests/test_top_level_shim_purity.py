import ast
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src"
CANON = SRC / "layer4_agents"


def _has_implementation(node: ast.Module) -> bool:
    for child in ast.walk(node):
        if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return True
    return False


@pytest.mark.parametrize(
    "path",
    [
        SRC / "database.py",
        SRC / "database_facade.py",
        SRC / "exceptions.py",
        SRC / "health_check.py",
        SRC / "main.py",
        SRC / "model_registry_client.py",
        SRC / "observability.py",
        SRC / "resilience.py",
        SRC / "resilience_ports.py",
        SRC / "startup_dependencies.py",
    ],
)
def test_top_level_file_is_shim(path: Path):
    module = ast.parse(path.read_text())
    assert not _has_implementation(module), f"{path} contains implementation; must be a shim"
