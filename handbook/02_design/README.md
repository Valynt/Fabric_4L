# Stage 02 — Design

Goal: turn the behavior scope note into a design note with impacted components and anchors.
Still no code. Check boundaries and known gaps before designing.

## Input

- A verified behavior scope note from `01_understand/`.

## Procedure

1. **Read the L2 page for each component** in the scope note:
   `handbook/L2-components/<component>.md`. Take its purpose, owned behaviors, key verified
   paths, and dependencies.
2. **Check allowed dependencies.** Open `control-plane/architecture/boundaries.md`. Any new
   dependency the change introduces MUST be on the allowed list. Adapter policy applies:
   commodity capabilities (identity, ingestion, workflow durability, review tooling,
   observability, structured LLM output) go behind adapters, not bespoke code.
3. **Check the GAP register** (`control-plane/product-contract/09_gap-register.md`). If the
   change touches an open `GAP-xx`, the design MUST converge toward the required behavior, never
   widen the deviation. Record the gap disposition.
4. **Read the behavior card's Implementation section** for existing anchors, inputs/outputs,
   state transitions, and failure modes. Design within them or plan their versioned change.
5. **Decide contract impact.** If the change alters a versioned contract surface (API schema,
   event envelope, tool manifest under `contracts/`), the design MUST state the version
   transition. Breaking changes require an approved version transition (gate AG-03).

## Output

A **design note**:

```
behavior: BEH-xx
impacted_components:
  - <component>            # MUST have a handbook/L2-components/ page
    anchors: [path, path#symbol, ...]
    change: <what changes>
new_dependencies: [...]      # each checked against boundaries.md; empty is normal
contract_impact: none | versioned-transition: <surface, new version>
gaps_touched: [GAP-xx: disposition]
rules_enforced: [R-x, ...]   # how the design satisfies each rule
```

## Verification

- Every impacted component has an L2 page under `handbook/L2-components/`.
- Every declared dependency is allowed by `control-plane/architecture/boundaries.md`.
- Every rule in `rules_enforced` has a stated enforcement mechanism, not an aspiration.
- Unresolvable anchors or missing L2 pages block progression — add the L2 page or correct the
  anchor first.

Proceed to `03_implement/`.
