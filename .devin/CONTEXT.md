# Context Management Protocol

Context is not how much text you can shove into the prompt. It is **structured grounding**. This document defines the monorepo-specific context protocol for all Value Fabric agents.

---

## Context Budget: 40 / 40 / 20

For every agent invocation, reserve the context window as follows:

| Budget | Purpose | Content |
|--------|---------|---------|
| **40% System Grounding** | Rules, graph, memory | Active rules, project graph, semantic memories, agent identity |
| **40% Relevant Code** | Target + related code | Retrieved snippets (validated against live AST), diffs, type definitions |
| **20% Conversation** | History + decisions | Summarized conversation, explicit state JSON, pending decisions |

> **Never exceed these budgets.** If code snippets exceed 40%, prune lowest-relevance files and re-verify against AST.

---

## Context Providers

### 1. Project Graph Context

**Source:** `repo-graph-mcp` → `get_project_dependencies`, `get_affected_projects`
**Location:** `context/project-graph.yaml`
**Purpose:** Prevent cross-cutting changes without knowing blast radius.

**Protocol:**
1. Before editing any file, call `repo-graph-mcp.get_project_dependencies(target_file)`
2. Inject as structured JSON:
   ```json
   {
     "target": "services/layer4-agents/src/tools/query_graph.py",
     "dependencies": ["layer3-knowledge", "shared/identity"],
     "dependents": ["frontend/client/src/hooks/useGraphQuery.ts"],
     "affected_tests": ["tests/evals/skills/test_query_graph.py"],
     "boundary_violations": []
   }
   ```
3. If boundary violations exist, halt and escalate.

---

### 2. Relevant Code Context

**Source:** Vector search + AST validation
**Location:** `context/project-graph.yaml` (retrieval config)
**Purpose:** Provide accurate, non-stale code snippets.

**Protocol:**
1. Embed the task description
2. Vector search over function/class embeddings (from `code-mcp.search_symbols`)
3. **Validate** retrieved snippets against live AST (`code-mcp.get_type_definition`)
4. If stale (hash mismatch), re-index and retry once
5. Inject validated snippets with file paths and line numbers

**Validation Check:**
```yaml
retrieval_validation:
  enabled: true
  method: ast_hash_comparison
  fallback: full_file_read
  max_stale_retries: 1
```

---

### 3. Diff Context

**Source:** Git + `diff-context.yaml`
**Purpose:** Help agent understand what has already changed in this session.

**Protocol:**
1. Fetch `git diff --cached` and `git diff` of working branch
2. Fetch last 5 commits: `git log --oneline -5`
3. Inject as:
   ```markdown
   ## Current Changes
   ```diff
   {git_diff}
   ```

   ## Recent Commits
   {commit_history}
   ```
4. Agent must review diff before proposing new changes to avoid conflicts.

---

### 4. Constraint Context

**Source:** `registry/rules.json` + `rules/*.yaml`
**Location:** `context/constraint-context.yaml`
**Purpose:** Load only rules relevant to files being touched.

**Protocol:**
1. Map target files to rule categories via `files_glob` patterns
2. Load matching rules from `rules/hard-constraints.yaml`, `rules/safety-rules.yaml`, etc.
3. Run lightweight policy agent evaluation: `pass / warn / block`
4. If `block`, halt immediately with reason
5. Inject active rules into system grounding budget

**Example Mapping:**
```yaml
file_path: "services/layer4-agents/src/tools/query_graph.py"
active_rules:
  - hard-constraints.yaml#tool-manifest-sync-required
  - safety-rules.yaml#no-pii-in-prompts
  - safety-rules.yaml#neo4j-parameterized-queries
  - dependency-rules.yaml#layer4-may-import-layer3
```

---

## Sliding Window Strategy

### Working Memory Pruning (when approaching limit)

1. **Summarize conversation:** Collapse turns older than 3 into a single decision summary
2. **Drop irrelevant code:** Remove snippets with relevance score < 0.7
3. **Compress rules:** Load only highest-severity rules if rule set is large
4. **Preserve immutable:** Never drop system identity, active constraints, or explicit state JSON

### Context Assembly Order

```
1. System prompt + agent identity
2. Active constraints (hard constraints + safety rules for target files)
3. Semantic memories (top-k from memory/semantic/)
4. Project graph context (dependencies, dependents, affected tests)
5. Diff context (current changes + recent commits)
6. Relevant code snippets (validated, ranked by relevance)
7. Conversation history (summarized)
8. Explicit state JSON (if in workflow)
```

---

## Validation

Before executing any tool call, verify:
- [ ] Context budget is within 40/40/20 split
- [ ] All code snippets have been AST-validated
- [ ] Active rules match the files being touched
- [ ] Diff context has been reviewed for conflicts
- [ ] Semantic memories are from this monorepo (not hallucinated)

---

## Anti-Patterns

- **Don't** dump raw file contents without relevance ranking
- **Don't** inject entire directory trees
- **Don't** use stale embeddings without AST validation
- **Don't** ignore boundary violations from project graph
- **Don't** overload conversation budget with raw tool outputs (summarize first)
