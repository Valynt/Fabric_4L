import re

with open("services/layer4-agents/src/layer4_agents/integrations/providers/salesforce/connector.py", "r") as f:
    content = f.read()

content = content.replace('"probability": rec.get("Probability") / 100 if rec.get("Probability") else 0,', '"probability": (rec.get("Probability") / 100) if rec.get("Probability") is not None else 0,  # type: ignore[operator]')

with open("services/layer4-agents/src/layer4_agents/integrations/providers/salesforce/connector.py", "w") as f:
    f.write(content)
