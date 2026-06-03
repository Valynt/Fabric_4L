---
workflow_id: template-pipeline-dag
name: Pipeline DAG
version: 1.0.0
description: Multi-stage pipeline where each stage is an agent with explicit input/output contracts
pattern: pipeline-dag
risk_level: low
---

# Pipeline (DAG) Workflow Template

## Pipeline Definition

```yaml
stages:
  - id: generate
    agent: code-generator
    input: spec_file
    output: generated_code.tar
    
  - id: test
    agent: test-assurance
    input: generated_code.tar
    output: test_report.json
    depends_on: [generate]
    
  - id: review
    agent: code-reviewer
    input: generated_code.tar, test_report.json
    output: review_approval.json
    depends_on: [test]
    
  - id: merge
    agent: merge-bot
    input: review_approval.json
    output: merged_commit
    depends_on: [review]
    gate: human_approval
```

## State Machine

```json
{
  "pipeline_id": "uuid",
  "current_stage": "generate",
  "stages": {
    "generate": {"status": "running", "artifact": null},
    "test": {"status": "pending", "artifact": null},
    "review": {"status": "pending", "artifact": null},
    "merge": {"status": "pending", "artifact": null}
  },
  "artifacts": {}
}
```

## Failure Handling

- Stage failure stops downstream stages
- Failed stage may be retried once
- After retry failure, halt and surface artifacts + logs

## Artifact Storage

Artifacts pass through shared object store:
- Local: `memory/episodic/artifacts/`
- Remote: S3 bucket or equivalent
- Reference by URI in state JSON, not inline
