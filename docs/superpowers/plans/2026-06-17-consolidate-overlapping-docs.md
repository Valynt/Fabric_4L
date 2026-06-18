# Sub-plan I: Consolidate Overlapping Documentation (#1)

**Goal:** Remove duplicate and near-duplicate docs so there is exactly one canonical location for each piece of information.

**Canonical locations**
- ADRs: `docs/explanations/adr/`
- Runbooks: `docs/operations/runbooks/`
- Platform architecture: `docs/core-concepts/architecture.md`
- Public doc site engine: keep `docs-site/` as the rendering layer; move or mirror content from `docs/` only where `docs-site/` is the source of truth.

**Scope**
1. Merge duplicate runbooks across `docs/runbooks/`, `docs/operations/runbooks/`, and `docs/troubleshooting/runbooks/`.
2. Move the 4 stray ADRs from `docs/adr/` into `docs/explanations/adr/` (or delete if superseded).
3. Replace root `ARCHITECTURE.md` and `docs/architecture.md` with redirects to `docs/core-concepts/architecture.md`.
4. Resolve near-duplicates: `docs/accessibility.md` vs `docs/accessibility_policy.md`, `docs/product-brief.md` vs `docs/product_brief.md`, `docs/ENVIRONMENT.md` vs `docs/getting-started/environment.md`.

**Files to inspect / modify**
- `docs/runbooks/*` — keep unique files only; delete duplicates that exist in `docs/operations/runbooks/`.
- `docs/troubleshooting/runbooks/*` — keep unique files only.
- `docs/operations/runbooks/*` — canonical runbook tree.
- `docs/adr/*.md` — move/adapt to `docs/explanations/adr/`.
- `docs/explanations/adr/README.md` — update index.
- `ARCHITECTURE.md`, `docs/architecture.md` — redirect stubs.
- `ops/README.md`, `ops/incident/README.md`, `monitoring/docs/log-retention-policy.md` — update broken links.
- `docs/DOCUMENTATION_AUDIT_REPORT.md` — mark items resolved.

**Approach**
1. For each duplicate runbook basename, compare content and keep the most complete/operational version in `docs/operations/runbooks/`.
2. Replace deleted copies with a short redirect stub pointing to the canonical path.
3. For ADRs, read the 4 stray files and either append them to the canonical index or mark them superseded by existing ADRs.
4. Rewrite root `ARCHITECTURE.md` to a 20-line summary with a link to `docs/core-concepts/architecture.md`.
5. Delete `docs/architecture.md` entirely or replace it with a redirect; `CHANGELOG.md` already documents this consolidation.

**Validation**
- `grep -R '<relative-path-to-deleted-file>' --include='*.md' docs ops monitoring` returns no broken links.
- `mkdocs build` (if using `docs-site/`) succeeds.
- `make check-readiness-consistency` passes.

**Rollback**
All deletions are recoverable from git history. Keep redirects for at least one release cycle before removing stubs.

**Risks**
- External bookmarks to root `ARCHITECTURE.md` break if not redirected.
- `docs/troubleshooting/runbooks/` contains files referenced by `monitoring/` and archive; verify each deletion.
