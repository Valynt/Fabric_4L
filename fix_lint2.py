with open('./services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py', 'r') as f:
    content = f.read()

target = """    _MATCH_PATTERN_PATTERN = re.compile(
        r"\\b(MATCH|OPTIONAL\\s+MATCH)\\s*(?:[A-Za-z_][A-Za-z0-9_]*\\s*=\\s*)?\\([^)]*\\)",
        re.IGNORECASE,
    )

"""
content = content.replace(target, "")

with open('./services/layer4-agents/src/layer4_agents/tools/knowledge_tools.py', 'w') as f:
    f.write(content)
