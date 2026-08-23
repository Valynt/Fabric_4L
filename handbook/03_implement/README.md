# Stage 03 — Implement

Goal: make the change, following L3 anchors to the exact code. Keep contract surfaces stable
or version them.

## Input

- A verified design note from `02_design/` with impacted components and anchors.

## Procedure

1. **Follow the anchors.** Each anchor is `path` or `path#symbol` (conventions in
   `handbook/L3-implementation/README.md`). Open only anchored files and their direct neighbors.
2. **Make the change** inside the impacted components declared in the design note. Do not
   introduce cross-layer calls not allowed by `control-plane/architecture/boundaries.md`.
3. **Keep contract surfaces stable.** Changes to `contracts/openapi/`, `contracts/jsonschema/`,
   `contracts/tool-manifests/`, or generated clients require the version transition declared in
   the design note. Never silently break a consumer.
4. **Update anchors if behavior changed.** When the change adds, removes, or relocates an
   anchored function or state transition, update the behavior card's Implementation section and
   the manifest in the same commit. Stale anchors fail CI.

## Non-negotiable rules (reference by ID)

- **R-4 — deterministic financial math.** Calculation logic (ROI, formulas, scenarios) MUST be
  deterministic and reproducible from stored inputs, formula versions, and engine version. An
  LLM MAY narrate a result; it MUST NOT replace a formula, invent an input, or alter an
  approved calculation. L3 owns the math; L4 orchestrates, never redefines it.
- **R-6 — fail-closed authorization.** Every read/write verifies tenant, account, and
  parent-case scope from the backend authorization snapshot. Missing, malformed, expired, or
  conflicting scope MUST reject before business logic runs. No silent defaults.
- **R-7 — immutable approved versions.** Approved/published artifacts (model, ROI snapshot,
  narrative, export) MUST NOT be mutated. An edit creates a new draft with explicit lineage.
- Also respect any other `R-x` in the scope note (R-2 server authority, R-3 human gates on AI
  output, R-5 labeled fallbacks, R-8 provenance paths).

## Output

- Code changes inside the declared components.
- Updated behavior-card anchors and manifest entries when behavior or surfaces changed.
- Tests for the changed behavior (unit at minimum; integration against real persistence when a
  service boundary is crossed — mocks are never release evidence).

## Verification

- Changed code is reachable from the anchors listed in the design note.
- No new cross-boundary dependency outside `boundaries.md`.
- Tests pass locally in the developer changed-scope lane (< 2 min: format, lint, affected unit
  tests, type checks).

Proceed to `04_verify/`.
