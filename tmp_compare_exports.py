import ast
from pathlib import Path

root = Path('C:/Users/BBB/Fabric_4L/services/layer1-ingestion/src/layer1_ingestion/api')

def get_top_level_names(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split('.')[0])
    return names

main_names = get_top_level_names(root / 'main.py')
mono_names = get_top_level_names(root / 'app_monolith.py')
main_only = sorted(main_names - mono_names)
mono_only = sorted(mono_names - main_names)
print('main only count:', len(main_only))
print('main only:', main_only)
print('monolith only count:', len(mono_only))
print('monolith only:', mono_only)
print('shared:', len(main_names & mono_names))
