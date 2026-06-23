# Memory Protocol: Three-Tier Hierarchy

Agents hallucinate or duplicate work when memory is implicit. This document defines the explicit, typed memory system for the Value Fabric agent fleet.

---

## Architecture

| Tier | Scope | Storage | Lifecycle | Windsurf Location |
|------|-------|---------|-----------|-------------------|
| **Working Memory** | Single turn / thread | In-context (sliding window) | Ephemeral | `memory/working/session-*.json` |
| **Episodic Memory** | Session / task | Vector DB + structured logs | Hours to days | `memory/episodic/` |
| **Semantic Memory** | Cross-session, generalized | Graph DB / curated vector store | Persistent, versioned | `memory/semantic/` |

---

## Tier 1: Working Memory

**Scope:** Current conversation thread only.
**Budget:** 20% of context window (see `CONTEXT.md`).

### Session State Template
Stored in `memory/working/session-<thread_id>.json`:

```json
{
  "session_id": "uuid",
  "agent_id": "test-assurance-001",
  "started_at": "2026-04-28T16:00:00Z",
  "context_budget": {
    "total_tokens": 128000,
    "system_grounding": 51200,
    "code_snippets": 51200,
    "conversation_history": 25600,
    "reserved_for_response": 4000
  },
  "active_rules": ["hard-constraints.yaml#no-raw-sql", "safety-rules.yaml#auth-middleware"],
  "files_in_context": [
    {"path": "services/layer4-agents/src/tools/query_graph.py", "reason": "primary_target", "token_count": 1200}
  ],
  "retrieved_memories": [
    {"type": "semantic", "rule_id": "auto-generated-0042", "relevance": 0.94}
  ],
  "pending_decisions": [],
  "last_action": "generated_positive_test_for_query_graph",
  "turn_count": 7
}
```

### Pruning Strategy
When approaching token limit:
1. Summarize conversation history older than 3 turns
2. Drop lowest-relevance code snippets (re-verify against live AST before re-injection)
3. Never drop system grounding or active rules

---

## Tier 2: Episodic Memory

**Scope:** Per-task execution logs, agent trajectories, tool call sequences.
**Storage:** Structured markdown + JSON in `memory/episodic/`, with vector embeddings for retrieval.
**Retention:** 30 days, then distilled or archived.

### Log Format
```json
{
  "episode_id": "uuid",
  "agent_id": "test-assurance-001",
  "task_hash": "sha256(task_desc + target_files)",
  "task_description": "Add adversarial tests for query_graph tool",
  "target_files": ["services/layer4-agents/src/tools/query_graph.py"],
  "started_at": "2026-04-28T16:00:00Z",
  "completed_at": "2026-04-28T16:15:00Z",
  "outcome": "success",
  "stages": [
    {"stage": "inspection", "duration_sec": 120, "tools_called": ["repo-graph-mcp.get_affected_projects"]},
    {"stage": "test_authoring", "duration_sec": 600, "files_written": ["tests/evals/skills/test_query_graph.py"]},
    {"stage": "verification", "duration_sec": 180, "tests_passed": 5, "tests_failed": 0}
  ],
  "decisions_made": [
    {"decision": "used_mock_neo4j_for_isolation", "rationale": "avoid_live_db_in_unit_tests"}
  ],
  "errors_encountered": [],
  "rules_triggered": ["safety-rules.yaml#no-live-db-in-unit-tests"],
  "memory_distilled": false
}
```

### Deduplication
Before creating a new episode, check `task_hash` against active episodes in `memory/episodic/active-tasks.json`. If match found:
- **Same agent:** Append to existing episode
- **Different agent:** Read existing episode into working memory; do not duplicate work

---

## Tier 3: Semantic Memory

**Scope:** Cross-session, generalized rules and patterns distilled from episodic logs.
**Storage:** Curated markdown in `memory/semantic/`, versioned in Git.
**Lifecycle:** Persistent. Updated via distillation pipeline.

### Distillation Pipeline

After each task completion, a background distillation process (manual or automated) reviews the episode and extracts semantic rules:

```
Episodic Log → Extract Pattern → Validate against Live Code → Store in Semantic Memory
```

### Semantic Rule Format
Stored in `memory/semantic/rules/`:

```markdown
---
rule_id: auto-generated-0042
created_at: 2026-04-28
derived_from: ["episode-uuid-1", "episode-uuid-2"]
confidence: 0.92
applies_to:
  - "services/layer4-agents/src/tools/*.py"
  - "tests/evals/skills/test_*.py"
tags: ["testing", "neo4j", "mocking"]
---

# When editing query_graph tool, always mock Neo4j driver in unit tests

## Pattern
Live Neo4j connections in unit tests cause flakiness and cross-tenant leakage.

## Rule
Always use `AsyncMock` for `Neo4jDriver` in unit tests. Integration tests may use `testcontainers-neo4j`.

## Rationale
Derived from 3 episodes where live Neo4j caused test failures due to RLS policy mismatches.

## Example
```python
from unittest.mock import AsyncMock

async def test_query_graph_isolated():
    mock_driver = AsyncMock()
    mock_driver.execute_query.return_value = [...]
    tool = QueryGraphTool(driver=mock_driver)
    ...
```
```

### Memory Alignment
Before every agent invocation:
1. Embed the task description
2. Retrieve top-k relevant semantic rules (k=5 default)
3. Inject into system prompt under `## Relevant Historical Patterns`
4. Databricks observed this reduces reasoning steps from ~20 to ~5

---

## Anti-Patterns

- **Don't** store large documents in working memory (use vector retrieval + reference)
- **Don't** mix tenant data without namespace isolation in episodic logs
- **Don't** rely on conversation history without summarization
- **Don't** store PII in any memory tier
- **Don't** let semantic memory grow unbounded — review and archive low-confidence rules quarterly

---

## Retention Policy

| Tier | Retention | Action |
|------|-----------|--------|
| Working | Session | Auto-deleted on session end |
| Episodic | 30 days | Distill to semantic, then archive |
| Semantic | Persistent | Manual review quarterly; archive rules with confidence < 0.7 |
| Archived | 1 year | Stored in `archive/` for audit compliance |
