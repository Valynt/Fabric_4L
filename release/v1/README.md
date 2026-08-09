# V1 Release Factory — `release/v1/`

Machine-readable launch contract for the constrained v1 release factory.
These artifacts give every agent task a verifiable finish line; deterministic
commands — not agent self-assessment — decide whether work is correct.

**These artifacts wrap the existing canonical gate hierarchy
(`make verify`, `make production-readiness-gate`, the behavior-readiness
ladder). They never define a parallel gate system.**

## Contents

| File | Purpose |
|---|---|
| `launch-contract.yaml` | Source of truth for what "public v1" means: journeys, targets, load model, classification rules, agent topology, concurrency rules |
| `architecture-invariants.yaml` | Machine-checkable invariants, each mapped to an existing checker/gate or a task that will build one |
| `critical-journeys/*.yaml` | The six launch-critical journeys with allowed/denied behavior and evidence mapping |
| `risk-register.yaml` | Launch risks seeded from `THREAT_MODEL.md`, `PRODUCTION_READINESS_REPORT.md`, and the compatibility-debt registry |
| `release-readiness.yaml` | Mapping from launch-contract requirements to the canonical gates/tasks that prove them |
| `task.schema.json` | Schema for bounded worker task contracts |
| `result.schema.json` | Schema for worker run results (harness re-verifies `status: complete`) |
| `candidate-manifest.schema.json` | Schema for the immutable release-candidate evidence bundle |
| `tasks/*.yaml` | The task graph: bounded P0/P1 tasks for the remaining phases |

## Enforcement

`tests/release/test_release_v1_contract_artifacts.py` validates every artifact
(schema conformance, referenced files/gates/checkers exist, dependency graph is
acyclic). It runs inside the existing `make gate-release-policy` /
`tests/release` suite, so the contract is CI-enforced.

## Harness scripts

| Script | Role |
|---|---|
| `scripts/release/baseline.sh` | Phase 1 classified baseline from a clean checkout (validates, never mutates) |
| `scripts/release/verify_changed.sh` | Narrowest-first verification for a change set |
| `scripts/release/certify_candidate.sh` | 17-step fail-closed certification of an immutable SHA (live steps require `CERTIFY_LIVE=1`) |
| `scripts/release/build_evidence_bundle.sh` | Builds and schema-validates the candidate evidence manifest |

## Roles

Release Director (read-only, owns these artifacts) → isolated worker agents
(one worktree each, no commit/push/merge/deploy) → independent reviewer (fresh
read-only checkout) → required CI gates → merge queue → release certifier
(clean environment, staging only, no in-flight remediation) → **human
production authorization** recorded in the candidate manifest.
