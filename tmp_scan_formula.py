import os, re

for root, _, files in os.walk('apps/web/src/pages/FormulaBuilder/components'):
    for f in files:
        if f.endswith('.tsx') or f.endswith('.ts'):
            p = os.path.join(root, f)
            base = f.replace('.tsx', '').replace('.ts', '')
            imported = False
            for rroot, _, rfiles in os.walk('apps/web/src'):
                for rf in rfiles:
                    if rf.endswith(('.ts', '.tsx')):
                        path = os.path.join(rroot, rf)
                        if path == p:
                            continue
                        try:
                            with open(path, 'r', encoding='utf-8') as fh:
                                if re.search(r'import.*\b' + re.escape(base) + r'\b', fh.read()):
                                    imported = True
                                    break
                        except:
                            pass
                if imported:
                    break
            if not imported:
                print(p)
