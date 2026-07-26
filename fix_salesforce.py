import re

with open("services/layer4-agents/src/layer4_agents/integrations/providers/salesforce/connector.py", "r") as f:
    content = f.read()

content = content.replace('instance_url=self.instance_url,', 'instance_url=self.instance_url or "",')
content = content.replace('self.instance_url = new_instance_url', 'self.instance_url = new_instance_url  # type: ignore[assignment]')

# Fix unsupported operand types for / ("None" and "int")  [operator] in 324
content = re.sub(r'limit_value = (.*?)\n\s+if (.*?):', r'limit_value = \1\n            if \2 and limit_value is not None:', content)

with open("services/layer4-agents/src/layer4_agents/integrations/providers/salesforce/connector.py", "w") as f:
    f.write(content)
