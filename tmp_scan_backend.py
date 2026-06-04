import os, re

def check_dir(directory, ext):
    """Find files in directory that are never imported anywhere in the project."""
    dead = []
    if not os.path.exists(directory):
        return dead
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(ext) and not f.startswith('test_') and not f.endswith('.test.py'):
                p = os.path.join(root, f)
                base = f.replace(ext, '')
                imported = False
                for rroot, _, rfiles in os.walk('services'):
                    for rf in rfiles:
                        if rf.endswith('.py'):
                            path = os.path.join(rroot, rf)
                            if path == p:
                                continue
                            try:
                                with open(path, 'r', encoding='utf-8') as fh:
                                    content = fh.read()
                                    # Check for import of module or specific names
                                    if re.search(r'from\s+.*\b' + re.escape(base) + r'\b|import\s+.*\b' + re.escape(base) + r'\b', content):
                                        imported = True
                                        break
                            except:
                                pass
                    if imported:
                        break
                if not imported:
                    dead.append(p)
    return dead

# Check layer4 tools
print("=== Layer4 Tools ===")
for d in check_dir('services/layer4-agents/src/tools', '.py'):
    print(d)

# Check layer4 services methods
print("\n=== Layer4 Services ===")
for d in check_dir('services/layer4-agents/src/services', '.py'):
    print(d)

# Check layer4 routes
print("\n=== Layer4 Routes ===")
for d in check_dir('services/layer4-agents/src/api/routes', '.py'):
    print(d)

# Check value_fabric namespace
print("\n=== value_fabric namespace ===")
for d in check_dir('value_fabric', '.py'):
    print(d)
