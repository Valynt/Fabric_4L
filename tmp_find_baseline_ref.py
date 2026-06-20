import os
root = 'C:/Users/BBB/Fabric_4L'
for dirpath, _, files in os.walk(root):
    if '.git' in dirpath or 'artifacts' in dirpath:
        continue
    for f in files:
        if f.endswith(('.py', '.sh', '.yml', '.yaml')):
            path = os.path.join(dirpath, f)
            try:
                with open(path, encoding='utf-8', errors='ignore') as fh:
                    for i, line in enumerate(fh, 1):
                        if 'deep_import_baseline' in line:
                            print(f'{path}:{i}:{line.rstrip()}')
            except Exception:
                pass
