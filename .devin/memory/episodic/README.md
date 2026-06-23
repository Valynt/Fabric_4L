# Episodic Memory

Task logs and structured execution records. Retention: **30 days**.

## File Naming

```
episodic/
  YYYY-MM/
    <agent-id>_<task-hash>_<timestamp>.json
```

## Format

See `MEMORY.md` for the full episodic log schema.

## Active Tasks

`active-tasks.json` maintains the in-progress task registry for deduplication:

```json
{
  "tasks": [
    {
      "task_hash": "sha256:...",
      "agent_id": "test-assurance-001",
      "episode_id": "uuid",
      "started_at": "2026-04-28T16:00:00Z",
      "status": "running"
    }
  ]
}
```

## Distillation Queue

Episodic logs marked with `"memory_distilled": false` are candidates for the distillation pipeline. Review these weekly to extract semantic rules for `memory/semantic/`.
