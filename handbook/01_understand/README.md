# Stage 01 — Understand

Goal: locate the behavior the change request touches and the contract that constrains it.
Read narrowly. Do not explore the repo; follow IDs.

## Input

- A change request (feature, fix, gap closure, refactor).

## Procedure

1. **Resolve the behavior.** Open `control-plane/contract_manifest.yaml`. Match the request to a
   `BEH-xx` entry (via its stories, gaps, or name). If no behavior matches, the behavior is
   undocumented — stop and report; see `L3-implementation/README.md` (handbook-from-reality spec).
2. **Read the product contract section** for the behavior's `VP-xx` story
   (`control-plane/product-contract/06_user-stories.md`) and every `R-x` rule and `GAP-xx`
   entry the manifest lists for it. Note the journey stage (`J-x`) and its entry/exit gates in
   `control-plane/product-contract/04_canonical-journey.md`.
3. **Read the behavior card** at the `card:` path in the manifest
   (`control-plane/behaviors/BEH-xx-*.md`), sections **Product** and **Architecture** only.
   Note the boundary (e.g. `L4 -> L5 -> L3`) and the named components.

## Output

A **behavior scope note**:

```
change: <one line>
behavior: BEH-xx <name>
journey: J-x
stories: [VP-xx, ...]        # each resolvable in the manifest
rules: [R-x, ...]            # constraints the change MUST respect
gaps: [GAP-xx, ...]          # gaps the change closes or must not widen
components: [...]            # from the card's Architecture section
```

## Verification

- Every ID in the scope note (BEH, J, VP, R, GAP) resolves to an entry in
  `control-plane/contract_manifest.yaml`.
- Every named component has a page in `handbook/L2-components/` (checked in stage 02).
- If any citation cannot be resolved, the scope note is invalid. Fix the manifest first — do not
  proceed on unresolvable references.

Proceed to `02_design/`.
