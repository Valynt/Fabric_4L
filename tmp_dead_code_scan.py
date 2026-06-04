import os, re

pages = []
for root, _, files in os.walk('apps/web/src/pages'):
    for f in files:
        if f.endswith('.tsx') and not f.endswith('.test.tsx'):
            pages.append(os.path.join(root, f))

for p in pages:
    base = os.path.basename(p).replace('.tsx', '')
    imported = False
    for rroot, _, rfiles in os.walk('apps/web/src'):
        for rf in rfiles:
            if rf.endswith(('.ts', '.tsx')):
                path = os.path.join(rroot, rf)
                if path == p:
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                        if re.search(r'import.*\b' + re.escape(base) + r'\b', content):
                            imported = True
                            break
                except:
                    pass
        if imported:
            break
    if not imported:
        print(p)
