# Memory Hierarchy

Explicit, typed memory storage for the agent fleet. See `MEMORY.md` for the full protocol.

## Directory Structure

```
memory/
  working/       # Ephemeral session state (in-context, per-thread)
  episodic/      # Task logs and structured execution records (30-day retention)
  semantic/      # Persistent distilled rules and patterns (versioned in Git)
```

## Usage

- **Working:** Automatically managed by agents per session. Do not edit manually.
- **Episodic:** Written by workflow completion. Review monthly for distillation.
- **Semantic:** Human-curated distilled knowledge. PR-based updates only.

## Retention

| Tier | Retention | Action |
|------|-----------|--------|
| Working | Session | Auto-deleted |
| Episodic | 30 days | Distill, then archive |
| Semantic | Persistent | Review quarterly |
| Archived | 1 year | Audit compliance |
