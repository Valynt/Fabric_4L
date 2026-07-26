cat << 'INNER_EOF' > /tmp/fix_scoring.py
import re

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/scoring.py", "r") as f:
    content = f.read()

# Fix returning Any where float is expected
content = re.sub(r'return deduction\n', r'return float(deduction)\n', content)

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/scoring.py", "w") as f:
    f.write(content)
INNER_EOF
python3 /tmp/fix_scoring.py
