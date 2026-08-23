with open('./services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py', 'r') as f:
    content = f.read()

import re

# Remove the unused _MATCH_PATTERN_PATTERN
content = re.sub(
    r'\s*_MATCH_PATTERN_PATTERN = re\.compile\(\s*r"\\b\(MATCH\|OPTIONAL\\s\+MATCH\)\\s\*\(\?:\[A-Za-z_\]\[A-Za-z0-9_\]\*\\s\*=\\s\*\)\?\\(\[\^)\]\*\\)",\s*re\.IGNORECASE,\s*\)',
    "",
    content
)

with open('./services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py', 'w') as f:
    f.write(content)
