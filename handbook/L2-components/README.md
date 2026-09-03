# L2 Components — index

One page per verified major component. Read a page only when a behavior card or stage-02 design
note names the component. Paths on each page are repository-verified; do not guess beyond them.

| Component | Page | Primary gates |
|---|---|---|
| Frontend pages and feature shells | `apps-web-pages.md` | AG-05, AG-02, AG-03 |
| FastAPI gateway / BFF (24 routers) | `services-api.md` | AG-05, AG-04, AG-03 |
| Agent orchestration (L4) | `layer4-agents.md` | AG-04, AG-05, AG-02, AG-06 |
| Knowledge / graph / deterministic ROI (L3) | `layer3-knowledge.md` | AG-05, AG-03, AG-02 |
| Ground truth / claims / governance (L5) | `layer5-ground-truth.md` | AG-05, AG-02, AG-04 |
| Value-case domain service (TS) | `value-studio.md` | AG-02, AG-03, AG-09 |
| Cross-surface contracts | `contracts.md` | AG-03, AG-01 |
| Shared packages | `packages.md` | AG-01, AG-02, AG-07 |

Component NOT YET covered by a page (e.g. `services/layer1-ingestion`, `layer2-extraction`,
`layer6-benchmarks`, `layer7-billing` internals): add the page when a behavior first needs it,
using only verified repository paths.
