# AI Evaluations (v1 manifest-first)

`manifest.yaml` is the entry point. It references the **existing** evaluation
runners (`make evals`, `pytest tests/evals`) rather than relocating them —
per `release/v1/tasks/V1-EVALS-001.yaml`, the pre-launch gap is evaluation
*coverage*, not folder layout.

Structure:

```text
evals/
  manifest.yaml    # runner + asset registry (source of truth for this tree)
  datasets/        # curated evaluation datasets
  rubrics/         # model-graded rubrics calibrated against human labels
  adversarial/     # injection and cross-tenant exfiltration sets
  baselines/       # frozen baseline results for regression comparison
```

Deterministic gates (schema validity, tool authorization, retrieval tenant
isolation, citation presence, cost/latency budgets) are enforced through the
existing `ai-evals-pipeline.yml` workflow. Implementation moves into this
tree only when the movement materially improves the release gate.
