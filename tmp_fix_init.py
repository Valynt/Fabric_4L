with open("services/layer4-agents/pyproject.toml", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace(".__init__", "")
with open("services/layer4-agents/pyproject.toml", "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced .__init__ entries")
