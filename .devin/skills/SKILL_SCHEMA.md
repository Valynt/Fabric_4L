# Skill Authoring Specification

Skills are **typed, versioned, and testable** capability modules. Every skill must conform to this schema.

---

## File Location

```
skills/
  <skill-name>/
    SKILL.md          # Required — human-readable behavior definition
    schema.json       # Optional — explicit JSON Schema for inputs/outputs
    tests/            # Optional — unit tests for skill logic
```

---

## SKILL.md Frontmatter

```yaml
---
skill_id: unique-kebab-case-id        # Must match registry/skills.json
name: human-readable-name
version: 1.0.0                        # SemVer
description: One-line purpose
side_effects: none | read | write | network | exec
timeout_ms: 30000
required_context:                     # List of context providers needed
  - project_graph
  - test_inventory
allowed_agents:                       # Which agents may invoke this skill
  - test-assurance
  - code-reviewer
  - "*"                              # Wildcard = all agents
---
```

---

## Required Sections

### 1. When to Use
Clear conditions for invoking this skill.

### 2. Input Parameters
Document every parameter with type, description, and required/optional status.

### 3. Steps
Numbered procedure. Each step should be actionable.

### 4. Output
Describe the return value, including key fields.

### 5. Edge Cases
Document known edge cases and how to handle them.

### 6. Anti-Patterns
What NOT to do when using this skill.

---

## Registry Registration

After creating a skill, add it to `registry/skills.json` with:

```json
{
  "skill_id": "your-skill-id",
  "name": "your-skill-name",
  "version": "1.0.0",
  "description": "...",
  "input_schema": { ... },
  "output_schema": { ... },
  "side_effects": "read",
  "timeout_ms": 30000,
  "required_context": ["project_graph"],
  "allowed_agents": ["*"]
}
```

---

## Side-Effect Policy

| Value | Meaning | Example |
|-------|---------|---------|
| `none` | Pure computation | Formatting, analysis |
| `read` | Reads from DB/files | Query graph, search docs |
| `write` | Modifies files/DB | Write tests, refactor code |
| `network` | External API call | LLM call, CRM export |
| `exec` | Runs subprocess | pytest, Playwright, build |

The Skill Registry validates inputs and enforces side-effect policies before routing to MCP servers.

---

## Versioning Rules

- **Patch (1.0.1):** Documentation fixes, non-behavioral changes
- **Minor (1.1.0):** New optional parameters, new output fields
- **Major (2.0.0):** Breaking changes to required parameters or output schema

Always update `registry/skills.json` when bumping versions.
