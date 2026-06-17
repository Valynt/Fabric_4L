import os

for dirpath, dirnames, filenames in os.walk('c:/Users/BBB/Fabric_4L'):
    if 'value_fabric' in dirpath and 'packages' not in dirpath:
        continue
    if '.git' in dirpath:
        continue
    for f in filenames:
        if f.endswith('.py'):
            p = os.path.join(dirpath, f)
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                    if 'Layer4EventContext' in content:
                        print(p)
            except OSError:
                pass
