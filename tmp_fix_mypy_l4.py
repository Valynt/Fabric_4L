import os

# Find all Python modules under src/layer4_agents
modules = []
base = "services/layer4-agents/src/layer4_agents"
for root, _, files in os.walk(base):
    for f in files:
        if f.endswith(".py"):
            rel = os.path.relpath(os.path.join(root, f), "services/layer4-agents/src")
            module = "src." + rel[:-3].replace(os.sep, ".")
            modules.append(module)

modules.sort()

# Read current pyproject.toml
with open("services/layer4-agents/pyproject.toml", "r", encoding="utf-8") as fh:
    content = fh.read()

# Find the module list and insert after the last entry before the closing bracket
last_entry = '    "src.workflows.roi_calculator",'
if last_entry not in content:
    print("Could not find last entry")
    exit(1)

# Generate the new entries, excluding ones already present
existing_lines = set(line.strip().strip('",') for line in content.splitlines() if line.strip().startswith('"src.'))
new_entries = [f'    "{m}",' for m in modules if m not in existing_lines]

if not new_entries:
    print("No new entries to add")
    exit(0)

insert_text = "\n".join(new_entries) + "\n"
content = content.replace(last_entry, last_entry + "\n" + insert_text)

with open("services/layer4-agents/pyproject.toml", "w", encoding="utf-8") as fh:
    fh.write(content)

print(f"Added {len(new_entries)} modules")
