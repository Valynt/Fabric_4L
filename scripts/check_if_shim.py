import os

# Check a sample of "equivalent" files to see if they're shims or actual implementations
samples = [
    "services/layer3-knowledge/src/api/routes/entities.py",
    "services/layer3-knowledge/src/retrieval/graph_rag.py",
    "services/layer4-agents/src/layer4_agents/tools/registry.py",
    "services/layer3-knowledge/src/schema/initializer.py",
    "services/layer4-agents/src/database.py",
]

for path in samples:
    full = f"c:/Users/BBB/Fabric_4L/{path}"
    if os.path.exists(full):
        with open(full, 'r') as f:
            content = f.read()
        is_shim = "from value_fabric" in content and "import *" in content
        is_compat = "compat" in content.lower() or "shim" in content.lower()
        print(f"{path}:")
        print(f"  is_shim: {is_shim}")
        print(f"  is_compat: {is_compat}")
        if len(content) < 500:
            print(f"  content preview: {content[:200]}...")
        print()
    else:
        print(f"{path}: DOES NOT EXIST")
