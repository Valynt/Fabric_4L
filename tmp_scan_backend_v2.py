import os, re

EXCLUDES = {'.hypothesis', '.tmp-local', '.uv-cache-local', '__pycache__', '.pytest_cache', 'node_modules', '.git'}

def should_skip(path):
    for ex in EXCLUDES:
        if ex in path:
            return True
    return False

def build_index(root_dir):
    all_content = []
    for rroot, _, rfiles in os.walk(root_dir):
        if should_skip(rroot):
            continue
        for rf in rfiles:
            if rf.endswith('.py'):
                path = os.path.join(rroot, rf)
                if should_skip(path):
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        all_content.append(fh.read())
                except:
                    pass
    return "\n".join(all_content)

services_content = build_index('services')
value_fabric_content = build_index('value_fabric')
packages_content = build_index('packages')
all_content = services_content + value_fabric_content + packages_content

def find_dead(directory, ext, search_content):
    dead = []
    if not os.path.exists(directory):
        return dead
    for root, _, files in os.walk(directory):
        if should_skip(root):
            continue
        for f in files:
            if f.endswith(ext) and not f.startswith('test_') and not f.endswith('.test.py'):
                p = os.path.join(root, f)
                base = f.replace(ext, '')
                pattern = r'from\s+.*\b' + re.escape(base) + r'\b|import\s+.*\b' + re.escape(base) + r'\b'
                if not re.search(pattern, search_content):
                    dead.append(p)
    return dead

print("=== Layer4 Tools ===")
for d in find_dead('services/layer4-agents/src/tools', '.py', all_content):
    print(d)

print("\n=== Layer4 Services ===")
for d in find_dead('services/layer4-agents/src/services', '.py', all_content):
    print(d)

print("\n=== Layer4 Routes ===")
for d in find_dead('services/layer4-agents/src/api/routes', '.py', all_content):
    print(d)

print("\n=== value_fabric namespace ===")
for d in find_dead('value_fabric', '.py', all_content):
    print(d)
