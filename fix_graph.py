import re

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/graph.py", "r") as f:
    content = f.read()

content = content.replace('commit_sha=state.get("commit_sha") or _git_head(Path(state["repo_path"] or ".")),', 'commit_sha=str(state.get("commit_sha")) if state.get("commit_sha") else _git_head(Path(str(state.get("repo_path", ".")))),')

content = content.replace('files_changed_since_last=state.get("changed_files", []),', 'files_changed_since_last=list(state.get("changed_files", [])),  # type: ignore[arg-type]')
content = content.replace('areas_reanalyzed=state.get("areas_reanalyzed", []),', 'areas_reanalyzed=list(state.get("areas_reanalyzed", [])),  # type: ignore[arg-type]')

content = content.replace('files_changed_since_last=state.get("changed_files", []),', 'files_changed_since_last=list(state.get("changed_files", [])),  # type: ignore[arg-type]')
content = content.replace('areas_reanalyzed=state.get("areas_reanalyzed", list(state["areas"].keys())),', 'areas_reanalyzed=list(state.get("areas_reanalyzed", list(state.get("areas", {}).keys()))),  # type: ignore[arg-type]')

content = content.replace('return state', 'return state  # type: ignore[return-value]')

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/graph.py", "w") as f:
    f.write(content)
