# V1 Release Factory — `release/v1/`

Machine-readable launch contract for the constrained v1 release factory.
These artifacts give every agent task a verifiable finish line; deterministic
commands — not agent self-assessment — decide whether work is correct.

**This directory is a thin control plane over the existing canonical gate
hierarchy (`make verify`, `make production-readiness-gate`, the
behavior-readiness ladder, the release-evidence packet). It never defines a
parallel gate, readiness, risk, or evidence system (INV-FACTORY-001).**

## Source-of-truth rule

```text
release/v1/*               = intended launch contract (committed, human-controlled)
production-readiness/*     = canonical risks and decisions (risk_register.yaml;
                             risk_register.md is a reconciled human view)
artifacts/release/<sha>/*  = observed evidence for one candidate (generated,
                             never committed)
```

## Contents

| File | Purpose |
|---|---|
| `launch-contract.yaml` | Source of truth for what "public v1" means: journeys, scope decisions, targets, load model, classification rules, artifact policy, agent permissions, migration certification policy |
| `architecture-invariants.yaml` | Machine-checkable invariants, each mapped to an existing checker/gate or a task that will build one |
| `journeys/j01..j05-*.yaml` | The five launch-critical journeys with allowed/denied behavior and evidence mapping |
| `schemas/task.schema.json` | Schema for bounded worker task contracts |
| `schemas/result.schema.json` | Schema for worker run results (harness re-verifies `status: complete`) |
| `schemas/candidate-manifest.schema.json` | Schema for the immutable release-candidate evidence bundle |
| `schemas/risk-register.schema.json` | Schema for `production-readiness/risk_register.yaml` |
| `tasks/*.yaml` | The task graph: bounded P0/P1 tasks for the remaining phases |

## Enforcement

`tests/release/test_release_v1_contract_artifacts.py` validates every artifact
(schema conformance, referenced files/gates/checkers exist, dependency graph is
acyclic, risk-register views do not drift). It runs inside the existing
`make gate-release-policy` / `tests/release` suite, so the contract is
CI-enforced. `make validate-launch-contract` runs the same suite locally.

## Harness (thin Python orchestrator)

| Command | Role |
|---|---|
| `make validate-launch-contract` | Validate contract, schemas, tasks, and risk-register reconciliation |
| `make release-baseline` | Classified baseline of canonical gates from a clean checkout → `artifacts/release/<sha>/baseline.json` |
| `make certify-release-candidate RELEASE_SHA=<sha>` | Fail-closed certification of an immutable SHA (live steps need `CERTIFY_LIVE=1`) → `artifacts/release/<sha>/` |
| `make build-release-evidence RELEASE_SHA=<sha>` | Canonical evidence packet + schema-validated candidate manifest; fails closed (nonzero exit) unless the candidate is certified — pass `--package-noncertified-diagnostics` to `scripts/release/build_evidence_bundle.py` for a diagnostics-only bundle |

Implementation: `scripts/release/{models,steps,baseline,certify_candidate,build_evidence_bundle,validate_contract}.py`.
Each step delegates to an existing make/pnpm/pytest command; the orchestrator
records start/end times, command, exit code, log path, and release criterion,
stops on the first blocking failure, and never modifies source.

## Roles

Release Director (reads repo; writes `release/v1/tasks` and planning records
only) → isolated worker agents (one worktree each, no
commit/push/merge/deploy) → independent reviewer (fresh read-only checkout;
review artifact outside the source tree) → required CI gates → merge queue →
release certifier (read-only checkout at the candidate SHA; writes
`artifacts/release/<sha>/` only; isolated staging; no in-flight remediation)
→ publisher (publishes validated patches; cannot waive gates) → **human
production authorization** recorded in the candidate manifest.
