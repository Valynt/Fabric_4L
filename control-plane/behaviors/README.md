# Behavior Registry — control-plane/behaviors/

The behavior card is the **unit of navigation** for this repository. Not the directory, not the service, not the page.

## What a behavior is

A **behavior** is one user-visible, normatively-specified capability of ValuePilot: a slice of the canonical journey (J-x) that delivers a product outcome, crosses a declared architectural boundary, and is provable by named release gates. A behavior is defined by its contract — stories (VP-xx), gaps it closes (GAP-xx), rules it enforces (R-x) — not by where its code happens to live.

There are exactly nine behaviors, BEH-01..BEH-09, aligned to journey order (J-1..J-10; VP-14 is cross-cutting and appears inside every card's Verification section rather than as its own behavior).

## Why behavior, not directory

Directories answer "where is the code?". Behaviors answer the questions that actually drive work:

- **Product**: what outcome is required, and which gap does this close? (VP-xx, GAP-xx, R-x)
- **Architecture**: which layers may participate, and who is authoritative? (boundary, components)
- **Implementation**: which verified files implement it, with what inputs, states, and failure modes?
- **Verification**: which tests, tenant-isolation assertions, gates (AG-0x), and evidence (EV-x) prove it?

A behavior spans `apps/web/`, `services/api/`, the layer services, and `contracts/`. No directory contains one. Navigating by directory scatters one behavior across five trees and forces agents to reconstruct intent from code. Navigating by behavior makes the card the single landing point, and every other artifact (product contract, architecture map, release register) links into it by stable ID.

## Card format (normative)

Every card MUST follow this exact section order:

```
# BEH-0x: <name>
```yaml frontmatter: id, name, journey_stage, stories, closes_gaps, rules,
                    boundary, components, primary_gates
## Product         — why the behavior exists; stories/gaps/rules; normative correct behavior
## Architecture    — boundary across layers, components, ascii data-flow diagram
## Implementation  — table of VERIFIED anchors; inputs/outputs; state transitions; failure modes
## Verification    — tests; tenant-isolation assertions; gates (AG-0x + reason); evidence (EV-x)
```

Frontmatter rules:
- `journey_stage` is the primary J-x stage; related stages are named in prose.
- `stories`, `closes_gaps`, `rules`, `primary_gates` use only IDs that exist in `control-plane/product-contract/` and `control-plane/release/`. VP-14 (scope/observe/audit/recover) is implicit in every card.
- `boundary` uses the layer notation `L1..L7`, `web`, `api`, e.g. `web -> api -> L4 -> L3`.
- `components` names the logical components; each MUST resolve to at least one anchor in the Implementation table.

## How cards stay honest

The Implementation section may cite **only paths verified in `context/repo_map.md`** (the repository anchor map). Enforcement:

1. **CI anchor check** — a control under AG-01 (repository integrity) parses every card's anchor table and fails the build if any path no longer exists on the candidate SHA. Anchors are machine-resolvable references, not prose.
2. **ID resolution** — the same check resolves every VP/GAP/R/J/AG ID in frontmatter against `contract_manifest.yaml`; an unresolvable ID is a build failure, never a stale mention.
3. **Drift = gap** — when code and card disagree, the card (backed by the product contract) is the target and the deviation is tracked as a GAP-xx, per the intent-vs-implementation rule. Cards are updated only with the code, in the same change.
4. **No unverified claims** — a card MUST NOT cite a path, route URL, or line number that has not been verified. Uncertainty is written down as uncertainty (see "Open anchors" notes where present).

## Index

| Card | Behavior | Journey | Stories | Closes | Primary gates |
|---|---|---|---|---|---|
| [BEH-01](BEH-01-account-intake.md) | Account intake & analysis launch | J-1 (J-2) | VP-01, VP-02 | GAP-01, GAP-02 | AG-04, AG-05 |
| [BEH-02](BEH-02-hypothesis-capture.md) | Hypothesis capture → validation → promotion | J-4 (J-3, J-5) | VP-03, VP-04, VP-05 | GAP-03, GAP-04 | AG-02, AG-05 |
| [BEH-03](BEH-03-driver-tree-modeling.md) | Driver tree modeling | J-5 | VP-07 | GAP-03, GAP-05 | AG-03, AG-05 |
| [BEH-04](BEH-04-formula-roi-calculation.md) | Formula & ROI calculation | J-7 (J-6) | VP-09, VP-10 | GAP-05, GAP-06, GAP-09, GAP-11 | AG-02, AG-03 |
| [BEH-05](BEH-05-evidence-and-cost-binding.md) | Evidence & cost binding | J-6 | VP-08 | GAP-08, GAP-10 | AG-02, AG-05 |
| [BEH-06](BEH-06-business-case-generation.md) | Business case generation | J-8 | VP-06, VP-11 | GAP-07, GAP-08 | AG-02, AG-03 |
| [BEH-07](BEH-07-deliverable-rendering.md) | Deliverable rendering (CFO/Exec/Technical) | J-9 | VP-11, VP-12 | GAP-07, GAP-08 | AG-02, AG-03 |
| [BEH-08](BEH-08-approval-and-publication.md) | Approval & publication | J-9 | VP-12 | GAP-07, GAP-08, GAP-10, GAP-11 | AG-04, AG-05 |
| [BEH-09](BEH-09-realization-tracking.md) | Realization tracking | J-10 | VP-13 | GAP-11 | AG-02, AG-05 |

Cross-cutting proof: GAP-12 (one fresh-account, candidate-SHA-bound, real-service journey through approval and export) is the golden-path certification control under AG-06; it exercises BEH-01..BEH-08 end to end and is referenced from each card's Verification section.
