import re

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/persistence.py", "r") as f:
    content = f.read()

# Fix redefinitions and type ignore tags
content = content.replace("class Base(DeclarativeBase):  # type: ignore[valid-type,misc]", "class Base(DeclarativeBase):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class AuditRunDB(Base):  # type: ignore[valid-type,misc]", "class AuditRunDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class FindingDB(Base):  # type: ignore[valid-type,misc]", "class FindingDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class FindingOccurrenceDB(Base):  # type: ignore[valid-type,misc]", "class FindingOccurrenceDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class ScorecardDB(Base):  # type: ignore[valid-type,misc]", "class ScorecardDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class AreaScoreDB(Base):  # type: ignore[valid-type,misc]", "class AreaScoreDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("class SprintDB(Base):  # type: ignore[valid-type,misc]", "class SprintDB(Base):  # type: ignore[valid-type,misc,no-redef]")
content = content.replace("await conn.run_sync(Base.metadata.create_all)", "await conn.run_sync(Base.metadata.create_all)  # type: ignore[attr-defined]")

# Fix "runs" redefinition
content = content.replace("runs = await self.list_runs_for_repository(repository)", "runs_list = await self.list_runs_for_repository(repository)")
content = content.replace("for run in runs:", "for run in runs_list:")

# Fix append
content = content.replace("runs_with_dates.append(run.started_at, run)", "runs_with_dates.append((run.started_at, run))")
content = content.replace("return [run for _, run in sorted_runs]", "return [r for _, r in sorted_runs]")

with open("services/layer4-agents/src/layer4_agents/agents/audit_orchestrator/persistence.py", "w") as f:
    f.write(content)
