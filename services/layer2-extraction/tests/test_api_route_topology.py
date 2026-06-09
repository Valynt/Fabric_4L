import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_MODULES = [
    REPO_ROOT / 'src/layer2_extraction/api/routes/jobs.py',
    REPO_ROOT / 'src/layer2_extraction/api/routes/health.py',
    REPO_ROOT / 'src/layer2_extraction/api/routes/system.py',
]


FORBIDDEN_MODULES = {
    'layer2_extraction.api.main',
    'layer2_extraction.api.app_factory',
    'layer2_extraction.api.lifespan',
}
FORBIDDEN_IMPORT_PREFIXES = (
    'layer2_extraction.api.main',
    'layer2_extraction.api.app',
    'layer2_extraction.api.lifespan',
)


def _import_targets(tree: ast.AST) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level == 0:
                targets.add(module)
            elif node.level == 2 and module == 'main':
                targets.add('layer2_extraction.api.main')
    return targets


def test_route_modules_do_not_import_app_globals_directly() -> None:
    for module in ROUTE_MODULES:
        tree = ast.parse(module.read_text(), filename=str(module))
        imports = _import_targets(tree)

        forbidden = [
            target
            for target in imports
            if target in FORBIDDEN_MODULES or target.startswith(FORBIDDEN_IMPORT_PREFIXES)
        ]
        assert not forbidden, f'{module} imports forbidden app globals: {forbidden}'
