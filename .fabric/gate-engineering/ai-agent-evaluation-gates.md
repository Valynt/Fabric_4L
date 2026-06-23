# AI and Agent Evaluation Gates

## Scope

Changes to agents, prompts, models, retrieval, ranking, validation, or benchmarks must pass these gates before production.

## Required evidence

| Gate | Measurement | Threshold |
|---|---|---|
| Prompt versioning | Manifest and code match | Every prompt has a versioned file and schema |
| Model versioning | Model config is pinned | `model` identifier is immutable reference |
| Structured-output validation | Schema validation test | 100% of evaluated outputs validate |
| Provenance completeness | Provenance audit | Every claim has source lineage |
| Tool authorization | Tool manifest tests | Tools execute only with authorized scopes |
| Prompt injection | Adversarial test suite | No policy bypass on adversarial inputs |
| Tenant-boundary retrieval | Hostile retrieval tests | No cross-tenant retrieval |
| Unsupported claims | Claim-refusal tests | Unsupported claims are refused |
| Contradictions | Contradiction tests | Contradictions are flagged, not synthesized |
| Benchmark labeling | Benchmark tests | Benchmarks are not presented as customer truth |
| Override policy | Override tests | Human review triggered when required |
| Regression comparison | A/B against production | No regression on critical-error metrics |

## Critical-error thresholds

A single occurrence of any critical error may fail the release even if aggregate metrics improve:

- Fabricated evidence
- Cross-tenant retrieval
- Unsupported financial claim
- Missing provenance
- Incorrect stakeholder attribution
- Incorrect unit or currency
- Benchmark presented as customer fact
- Invalid override handling

## Quality, latency, cost thresholds

| Metric | Target | Warning | Block |
|---|---|---|---|
| Output quality (eval score) | ≥ baseline | baseline - 5% | baseline - 10% |
| P99 latency | ≤ baseline + 20% | + 30% | + 50% |
| Cost per workflow | ≤ baseline + 10% | + 20% | + 30% |

## Human-review triggers

- Unsupported claim detected
- Confidence below threshold
- Override requested
- Benchmark recommendation
- Financial value calculation

## Fallback behavior

Every agent path must have a fallback that does not silently degrade to a weaker model or bypass validation.

## Evidence retention

Agent evaluation evidence is retained in `artifacts/agent/` for one year and includes prompt version, model version, dataset version, eval results, and critical-error inventory.
