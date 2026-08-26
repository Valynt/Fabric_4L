# Release Governance — Control Plane

This directory is the release-governance control plane for Fabric_4L. It enforces one
outcome: **no change can merge, become a release candidate, or deploy to production unless
every material risk is covered by a current, successful, authoritative blocking control.**

## The four-way separation

Release governance is split into four artifacts with distinct responsibilities. Each artifact
MUST remain authoritative in exactly one dimension:

| Artifact | Question it answers | Role |
|---|---|---|
| `control_register.yaml` | **WHAT** must pass | Machine-readable register of the 9 aggregate gates (AG-01..AG-09), their CTRL controls, the decision point each control blocks, and the evidence each control requires. |
| `test_strategy.md` | **HOW** it is proven | Test environments, portfolio, lanes, Fabric-specific coverage, tenant-hostility protocol, and mock policy that produce the proof. |
| `evidence_schema.json` | **WHAT** valid proof looks like | JSON Schema (draft 2020-12) for a single evidence record: subject binding, freshness, conclusion semantics. |
| `evaluator.md` | **RELEASE or BLOCK** | The decision algorithm that aggregates evidence against the register and produces the merge / release / promotion decision. |

Rules:

- The register is the only place that declares which controls exist and what they block.
  Evaluators MUST NOT hardcode control lists; they MUST read `control_register.yaml`.
- The strategy MUST NOT weaken a register requirement. A test lane MAY add evidence, never
  subtract a control.
- Evidence that does not validate against `evidence_schema.json` MUST be treated as missing.
- The evaluator MUST fail closed: a failed, missing, expired, cancelled, skipped, or
  inconclusive critical control can never remain merely informational.

## The three authoritative decision points

| Decision | Required proof | What blocks at this point |
|---|---|---|
| **Merge authorization** | The change is safe to integrate into main. | Static analysis, tests, contracts, migration definitions, manifest validation. |
| **Release authorization** | The exact source SHA and built artifact satisfy the complete release contract. | DAST, live tenancy journeys, restore validation, performance, staging certification. |
| **Production promotion** | The same signed artifact passed staging certification and is safe to deploy. | Canary health, SLOs, change approval, artifact verification. |

Blocking rule: **a control blocks at the earliest practical decision point.** Each control in
the register carries `blocks: merge | release | promotion` accordingly.

Scheduled or long-running tests MAY provide evidence asynchronously, but their results MUST
feed a blocking release decision through AG-08 (release-evidence).

## File map

| File | Contents |
|---|---|
| `control_register.yaml` | Decision points, evidence types (EV-x), gates AG-01..AG-09 with CTRL-\<gate\>-\<nn\> controls, security controls (FAB4L-SEC-*), waiver policy. |
| `test_strategy.md` | Level-10 outcome, 5 environments, 20-area portfolio, Fabric-specific coverage, tenant hostility, mock policy, 8 execution lanes, evidence fields. |
| `evidence_schema.json` | JSON Schema for one authoritative evidence record; conclusion enum; blocking-conclusion semantics. |
| `evaluator.md` | Aggregation rules and the `evaluate()` decision algorithm; target implementation `scripts/ci/evaluate_release_controls.py`. |
| `levels.md` | Level-10 rubric: 5 categories, all subcategories, weakest-link scoring, 90-day sustained-evidence requirement. |

## ID scheme

- `AG-0x` — aggregate release gates; the gate `name` (e.g. `04-security-gates`) is also the
  required GitHub check context.
- `CTRL-<gate>-<nn>` — individual release controls, children of one gate.
- `EV-x` — evidence types declared in the register.
- `FAB4L-SEC-P{0-3}-{DOMAIN}` — security audit controls, preserved verbatim from the
  Enterprise Security Audit Contract and mapped to gates in the register's
  `security_controls` section.

All nine aggregate names are required GitHub check contexts on pull requests and merge
groups. Fail-closed semantics apply: an aggregate reports success only when every expected
required child reports success.
