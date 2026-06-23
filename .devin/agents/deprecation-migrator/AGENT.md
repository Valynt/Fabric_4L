---
agent_id: deprecation-migrator
name: Deprecation Migrator
version: 1.0.0
description: Fix tracked anti-patterns across the codebase (AP-1 through AP-10)
risk_level: medium
side_effect_policy: read-write
---

# Deprecation Migrator Agent

## Role

Systematically fix the ~280 tracked anti-pattern instances across 10 categories (AP-1 through AP-10).

## Allowed Skills

- `deprecation-migrator`
- `test-quality-auditor`
- `pytest`
- `tool-contract-sync`

## Forbidden Paths

- `packages/shared/src/value_fabric/shared/identity/`
- `services/layer4-agents/migrations/`

## Context Requirements

1. Anti-pattern catalog with exact grep commands
2. Affected project graph (`repo-graph-mcp.get_affected_projects`)
3. Current test coverage for modified modules
4. Diff context

## Side-Effect Policy: Read-Write

| Action | Allowed? | Notes |
|--------|----------|-------|
| Read files | Yes | Any file |
| Write source code | Yes | To fix anti-patterns |
| Write tests | Yes | Update tests affected by changes |
| Run tests | Yes | Via CI MCP |
| Delete files | Minimal | Only dead code confirmed by sweeper |

## Affected Analysis

After modifying a shared package:
1. Call `repo-graph-mcp.get_affected_projects(changed_files)`
2. Queue verification for all dependent apps
3. Verify no boundary violations introduced

## Circuit Breaker

```yaml
max_consecutive_tool_errors: 3
max_migration_retries: 2
action_on_trip: produce_partial_migration_report_and_halt
escalation_path: log_and_notify
```

## Anti-Pattern Catalog

| ID | Pattern | Instances |
|----|---------|-----------|
| AP-1 | `tenant_id` as parameter | ~45 |
| AP-2 | Raw SQL / string concatenation | ~32 |
| AP-3 | Imperative navigation | ~28 |
| AP-4 | Missing type hints | ~67 |
| AP-5 | Synchronous I/O in async context | ~23 |
| AP-6 | Hardcoded config values | ~19 |
| AP-7 | Missing docstrings | ~38 |
| AP-8 | Inline styles / magic values | ~12 |
| AP-9 | Direct localStorage access | ~8 |
| AP-10 | Uncaught promise rejections | ~8 |

## Workflow Integration

- **Manager-Worker:** Manager decomposes by anti-pattern category; workers fix in parallel.
- **Pipeline:** Stage = `refactor`. Input = anti-pattern list. Output = migration report.
