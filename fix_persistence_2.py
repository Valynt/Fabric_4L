import re

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/persistence.py", "r") as f:
    content = f.read()

content = content.replace("self._session_factory = None", "self._session_factory = None  # type: ignore[assignment]")

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/persistence.py", "w") as f:
    f.write(content)
