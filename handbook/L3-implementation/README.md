# L3 — Implementation Anchors

Level 3 of progressive disclosure: exact code locations for the behavior being changed.
Anchors are the contract between the handbook and the repository.

## Anchor conventions

An anchor is:

```
path                  # a verified file or directory
path#symbol           # a file plus a function, class, route, or exported symbol
```

Rules:

1. Anchors in behavior cards and L2 pages MUST come from verified repository paths. Directory-
   listing-level verification exists today; symbol-level anchors (`path#symbol`) are added as
   they are confirmed by code reads or the resync job.
2. Anchors are relative to the repository root. No absolute paths, no branch-qualified URLs.
3. An anchor that no longer resolves is **stale** — CI fails on stale anchors (see below).
4. Anchors identify location, not behavior. Semantics live in the behavior card
   (inputs/outputs, state transitions, failure modes).

## How to add an anchor

1. Confirm the path exists in the repository (and the symbol, for `path#symbol`).
2. Add it to the behavior card's Implementation section, and to the manifest's component list
   if the component relationship is new.
3. If no behavior card claims the code you are touching, that behavior is undocumented — add or
   extend a card; do not leave code outside the behavior map.
4. Same commit: code change + anchor change. Never update anchors separately.

## Spec: handbook derived from reality

The handbook is generated and checked from the code, not maintained as free-floating prose.

**Pipeline (resync job):**

1. **Static analysis** extracts facts from the repository: functions, classes, routes, call
   edges, state reads/writes, and execution stages, per service and app.
2. **Behavioral regrouping** clusters those facts by the canonical journey and the BEH-xx
   taxonomy — behavior, not directory, is the grouping key.
3. **Synthesis** regenerates L1/L2/L3 content: system map, component pages, and anchor lists are
   derived from the extracted facts and the behavior clusters.
4. **Verification (CI drift check):**
   - every anchor in `control-plane/behaviors/*.md` and `handbook/L2-components/*.md` resolves
     to a current path (and symbol, where symbol-level);
   - every behavior implied by the extracted facts maps to a BEH-xx card — undocumented behavior
     fails CI;
   - every card's Verification section names controls that exist in
     `control-plane/release/control_register.yaml`;
   - every ID (VP, GAP, R, J, BEH, CTRL, AG) cited in prose resolves in
     `control-plane/contract_manifest.yaml`.

**Failure semantics:** stale anchor, undocumented behavior, unresolvable ID, or dangling control
reference blocks the merge under gate AG-01 (repository-integrity / documentation and ownership
checks). The fix is to resync the handbook or the code — never to delete the reference to make
CI pass.

**Freshness:** the resync job runs on every merge candidate; handbook content and the manifest
MUST describe the candidate SHA being merged, matching the evidence-freshness rule (AG-08).
