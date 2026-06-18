import os, re

root = 'C:/Users/BBB/Fabric_4L'
for dirpath, _, filenames in os.walk(root):
    if '.git' in dirpath or 'node_modules' in dirpath or '.venv' in dirpath or '__pycache__' in dirpath:
        continue
    for fn in filenames:
        if fn.endswith('.py'):
            path = os.path.join(dirpath, fn)
            try:
                txt = open(path, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            # Look for L1-specific app_monolith references
            if 'layer1_ingestion.api.app_monolith' in txt or 'api.app_monolith' in txt:
                if 'layer3' in path or 'layer3-knowledge' in path:
                    continue
                print(path)
                for i, line in enumerate(txt.splitlines(), 1):
                    if 'app_monolith' in line:
                        print(f'  {i}: {line.strip()[:100]}')
