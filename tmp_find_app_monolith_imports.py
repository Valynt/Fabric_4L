import os

root = 'C:/Users/BBB/Fabric_4L'
matches = []
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
            if 'app_monolith' in txt:
                matches.append((path, txt.count('app_monolith')))

for path, count in sorted(matches):
    print(f'{count} {path}')
