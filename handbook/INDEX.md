# Handbook — Fabric_4L / ValuePilot AI Workspace

The single entry point for any human or agent working in this repository.
Replaces the legacy per-tool agent directories (`.claude/`, `.kimi/`, `.roo/`, ...). See `MIGRATION.md`.

**Rule: do NOT ingest the whole repository. Navigate it.** The behavior is the unit of navigation,
not the directory. Read only what the path below tells you to read.

## The architecture in one picture

```text
                    HUMAN / AGENT ENTRY POINT
                              |
                    Harness Handbook / Index
                              |
             +----------------+----------------+
             |                                 |
       Product Contract                 Architecture
       VP / GAP / Rules              System topology
             |                                 |
             +---------------+-----------------+
                             |
                    Behavior being changed
                             |
                   Progressive disclosure
                             |
                L1: System / Domain
                             |
                L2: Components involved
                             |
                L3: Functions / state /
                    APIs / code anchors
                             |
                       Implementation
                             |
                         Verification
                             |
                Release Control Register
                             |
                     Test + Evidence
                             |
                 RELEASE_AUTHORIZED
                       or BLOCKED
```

## How to navigate

1. **Start at `control-plane/contract_manifest.yaml`.** It is the machine-readable hub linking
   product rules (`R-x`), stories (`VP-xx`), gaps (`GAP-xx`), journey stages (`J-x`),
   behaviors (`BEH-xx`), and release controls (`CTRL-xx`, gates `AG-0x`).
2. **Pick the behavior you are changing** from the index below (or resolve it from the manifest).
3. **Follow its card L1 → L2 → L3**: read the card at `control-plane/behaviors/BEH-xx-*.md`
   (Product → Architecture → Implementation → Verification), drop to `L1-system/` for context,
   `L2-components/` for the components it touches, and `L3-implementation/` anchors for exact code.
4. **Verify against the release gates** the card names, and produce evidence per
   `control-plane/release/evidence_schema.json`.

Only load a directory or file when a card, component page, or anchor points at it.

## Behavior index

| ID | Name | Purpose | Journey stage | Card |
|---|---|---|---|---|
| BEH-01 | account-intake | Start or resume a tenant/account-scoped analysis case | J-1 | `control-plane/behaviors/BEH-01-account-intake.md` |
| BEH-02 | hypothesis-capture | Hypothesis generation, validation, promotion from reviewed signals | J-4 (consumes J-2–J-3) | `control-plane/behaviors/BEH-02-hypothesis-capture.md` |
| BEH-03 | driver-tree-modeling | Materialize the persistent driver tree and value model | J-5 | `control-plane/behaviors/BEH-03-driver-tree-modeling.md` |
| BEH-04 | formula-roi-calculation | Governed formulas and deterministic ROI scenario calculation | J-7 (formulas from J-6) | `control-plane/behaviors/BEH-04-formula-roi-calculation.md` |
| BEH-05 | evidence-and-cost-binding | Bind evidence, benchmarks, and solution cost to claims | J-6 | `control-plane/behaviors/BEH-05-evidence-and-cost-binding.md` |
| BEH-06 | business-case-generation | Generate the evidence-linked narrative business case | J-8 | `control-plane/behaviors/BEH-06-business-case-generation.md` |
| BEH-07 | deliverable-rendering | Render CFO / Executive / Technical views from one model | J-9 | `control-plane/behaviors/BEH-07-deliverable-rendering.md` |
| BEH-08 | approval-and-publication | Review, approve, publish, export immutable versions | J-9 | `control-plane/behaviors/BEH-08-approval-and-publication.md` |
| BEH-09 | realization-tracking | Track realized value against the approved forecast | J-10 | `control-plane/behaviors/BEH-09-realization-tracking.md` |

Journey stage IDs and names are defined in `control-plane/product-contract/04_canonical-journey.md`.

## The four stages

Every change runs through four stages, in order. Each stage has inputs, outputs, and a
verification condition. Do not skip stages.

| Stage | Directory | Input → Output |
|---|---|---|
| 1. Understand | `01_understand/` | change request → behavior scope note (BEH-xx + components) |
| 2. Design | `02_design/` | scope note → design note with impacted L2 components and anchors |
| 3. Implement | `03_implement/` | design note → code change + updated anchors |
| 4. Verify | `04_verify/` | code change → evidence records bound to a SHA, per the gates |

## Layout

```
handbook/
  INDEX.md               # this file
  01_understand/         # stage 1: locate the behavior and its contract
  02_design/             # stage 2: component boundaries, gaps, impacted anchors
  03_implement/          # stage 3: code change rules (R-4, R-6, R-7, ...)
  04_verify/             # stage 4: gates AG-01..AG-09, evidence
  L1-system/             # system map (product, topology, data flow)
  L2-components/         # one page per verified component
  L3-implementation/     # anchor conventions + handbook-from-reality resync spec
  schemas/               # contract_manifest + behavior card schemas
  MIGRATION.md           # legacy agent-dir deprecation mapping
```

## Normative rules you cannot violate

Reference by ID; full text in `control-plane/product-contract/01_product-intent.md`.

- **R-2** — the authoritative model is server-persisted, tenant-scoped, versioned. Browser storage is cache only.
- **R-4** — financial math is deterministic and reproducible. An LLM never silently replaces a formula or input.
- **R-6** — authorization, tenant, account, case, and version uncertainty fail closed.
- **R-7** — an approved or published version is immutable; later edits create a new draft with lineage.
- **R-8** — every quantitative claim exposes a provenance path to its original source.
