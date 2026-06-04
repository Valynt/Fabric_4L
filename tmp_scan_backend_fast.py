import os, re

def build_index(root_dir):
    """Build a single string of all python file contents for fast searching."""
    all_content = ""
    for rroot, _, rfiles in os.walk(root_dir):
        for rf in rfiles:
            if rf.endswith('.py'):
                path = os.path.join(rroot, rf)
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        all_content += fh.read() + "\n"
                except:
                    pass
    return all_content

services_content = build_index('services')

# Also check value_fabric and packages
value_fabric_content = build_index('value_fabric')
packages_content = build_index('packages')

all_content = services_content + value_fabric_content + packages_content

def find_dead(directory, ext, search_content):
    dead = []
    if not os.path.exists(directory):
        return dead
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(ext) and not f.startswith('test_') and not f.endswith('.test.py'):
                p = os.path.join(root, f)
                base = f.replace(ext, '')
                # Check if imported anywhere
                pattern = r'from\s+.*\b' + re.escape(base) + r'\b|import\s+.*\b' + re.escape(base) + r'\b'
                if not re.search(pattern, search_content):
                    dead.append(p)
    return dead

# Check layer4 tools
print("=== Layer4 Tools ===")
for d in find_dead('services/layer4-agents/src/tools', '.py', all_content):
    print(d)

# Check layer4 services
print("\n=== Layer4 Services ===")
for d in find_dead('services/layer4-agents/src/services', '.py', all_content):
    print(d)

# Check layer4 routes
print("\n=== Layer4 Routes ===")
for d in find_dead('services/layer4-agents/src/api/routes', '.py', all_content):
    print(d)

# Check value_fabric namespace
print("\n=== value_fabric namespace ===")
for d in find_dead('value_fabric', '.py', all_content):
    print(d)

# Check other backend layers for __init__ imports vs file existence
print("\n=== All backend layers - orphan py files ===")
for layer in ['layer1-ingestion', 'layer2-5-signal-refinery']:
    src_dir = f'services/{layer}/src'
    if os.path.exists(src_dir):
        layer_content = build_index(src_dir)
        for root, _, files in os.walk(src_dir):
            for f in files:
                if f.endswith('.py') and not f.startswith('test_') and not f.endswith('.test.py') and f != '__init__.py':
                    p = os.path.join(root, f)
                    base = f.replace('.py', '')
                    # Use relative path for package import check
                    rel = os.path.relpath(p, src_dir).replace('\\', '.').replace('/', '.').replace('.py', '')
                    if rel.startswith('.'):
                        rel = rel[1:]
                    pattern = r'from\s+.*\b' + re.escape(base) + r'\b|import\s+.*\b' + re.escape(base) + r'\b'
                    if not re.search(pattern, layer_content):
                        print(p)
