import os, re

root_dir = r'c:/Users/BBB/Fabric_4L'
skip_dirs = {'.git', '.tmp', '.pytest_cache', '.venv', 'node_modules', '.uv-cache-local', '.tmp-local', '__pycache__', '.tmp_check_old_path_usage'}

# Map old path -> canonical path for duplicate layer1 files
old_canonical = {
    'src.compliance.pii_scanner': 'layer1_ingestion.compliance.pii_scanner',
    'src.crawler.playwright_crawler': 'layer1_ingestion.crawler.playwright_crawler',
    'src.api.routes.compatibility': 'layer1_ingestion.api.routes.compatibility',
}

results = {}
for old, canonical in old_canonical.items():
    old_pattern = re.compile(rf'from\s+{re.escape(old)}\s+import|import\s+{re.escape(old)}\b')
    canonical_pattern = re.compile(rf'from\s+{re.escape(canonical)}\s+import|import\s+{re.escape(canonical)}\b')
    old_users = []
    canonical_users = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                    if old_pattern.search(content):
                        old_users.append(os.path.relpath(path, root_dir))
                    if canonical_pattern.search(content):
                        canonical_users.append(os.path.relpath(path, root_dir))
            except Exception:
                pass
    results[old] = {'old': old_users, 'canonical': canonical_users}

for old, data in results.items():
    print(f'{old}:')
    print(f'  old path users: {len(data["old"])}')
    for f in data['old']:
        print(f'    {f}')
    print(f'  canonical users: {len(data["canonical"])}')
    for f in data['canonical']:
        print(f'    {f}')
