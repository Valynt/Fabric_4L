# Layer Quality Scorecard

This scorecard is a machine-readable governance artifact for release gating.

- Policy source: `config/baselines/layer-quality-threshold-policy.json`
- Generated artifact: `config/baselines/layer-quality-scorecard.json`
- Attention registry: `config/baselines/layer-quality-attention-registry.json`
- CI markdown summary: `artifacts/layer-quality-scorecard.md`
- Generator: `scripts/ci/layer_quality_scorecard.py`

## Signals tracked per layer

1. `tenant_isolation_tests`
2. `contract_tests`
3. `migration_discipline`
4. `security_negative_paths`
5. `docs_contract_freshness`

## Attention findings

The scorecard also validates file-level attention findings that do not fit a single layer-wide coverage signal:

1. `ungoverned_hotspots`
2. `stale_decisions`
3. `knowledge_silos`

Each registry item must include an owner, evidence path, review due date, and remediation state. Generated files must point to their source contract and generation command instead of carrying hand-written governance comments. Knowledge-silo findings require a secondary or backup owner. Alert-tuning decisions require a decision date, runbook path, and non-stale review due date.

Rust/Cargo checks are not part of this scorecard because Rust is not currently used in tracked production code. If Rust is introduced, the maturity evidence must add a root or workspace `Cargo.lock` plus CI coverage for `cargo clippy --all-targets --all-features` and `cargo audit`.

## Regression threshold policy

The release gate fails when either condition is violated:

- A layer score drops below `per_layer_min_score`.
- The number of failed layers exceeds `max_failed_layers`.
- Any attention registry item fails its required governance evidence checks.

Current thresholds are defined in the policy JSON and consumed by CI so regressions are visible before release.
