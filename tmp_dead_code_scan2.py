import os, re

def find_dead(root_dir, check_dir):
    files = []
    for r, _, filenames in os.walk(check_dir):
        for f in filenames:
            if f.endswith('.tsx') and not f.endswith('.test.tsx'):
                files.append(os.path.join(r, f))

    for p in files:
        base = os.path.basename(p).replace('.tsx', '')
        imported = False
        for rroot, _, rfiles in os.walk(root_dir):
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

# Check intelligence pages
find_dead('apps/web/src', 'apps/web/src/pages/intelligence')
print("---")
# Check evidence pages
find_dead('apps/web/src', 'apps/web/src/pages/evidence')
print("---")
# Check admin pages
find_dead('apps/web/src', 'apps/web/src/pages/admin')
print("---")
# Check calculator pages
find_dead('apps/web/src', 'apps/web/src/pages/calculator')
print("---")
# Check drivers pages
find_dead('apps/web/src', 'apps/web/src/pages/drivers')
print("---")
# Check realization pages
find_dead('apps/web/src', 'apps/web/src/pages/realization')
