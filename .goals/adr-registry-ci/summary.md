# Goal Summary: adr-registry-ci

## What was achieved

ADR Registry + CI gate (`make check-adr`) delivered and independently verified (Inspector: PASS, iteration 1).

- **AC1** - Dual-corpus registry `docs/decisions/adr-registry.yaml` exactly matches disk: 47 architecture ADRs + 5 implementation decisions, all with related paths that exist.
- **AC2** - `scripts/ci/check_adr.py` fail-closed: empty corpora, non-mapping corpora, unregistered ADRs, missing related paths, index drift, and content-rule violations all fail; no fail-open early return.
- **AC3** - `make check-adr` target wired into `VERIFY_CHECKS` (deliberately not into `check-health-ratchets`); documented in `COMMANDS.md`.
- **AC4** - GitHub and Depot PR workflows carry identical ADR gate steps (ADR-047 lockstep maintained); parity tests pass.
- **AC5** - 10 focused tests including a registry-without-corpora fail-closed test.
- **AC6** - Inventory regenerated and current (237 phony / 234 public / 237 total, includes `check-adr`).
- **AC7** - Docs updated: governance.md, COMMANDS.md, DISCOVERY_MAP.md, both corpus READMEs, decisions TEMPLATE.
- **AC8** - All gates run fresh: checker, numbering (47 files), 10/10 tests, inventory `--check`, command-map + parity + inventory suites (42/43; sole failure is the pre-existing Windows-CRLF fixture-hash test that reproduces at the base commit).

## Iteration history

1. Iteration 1 first run: BLOCKED (preToolUse hook blocked all shell/git calls).
2. Resumed after shell access restored: code-review hard findings fixed, all gates re-run green, lint clean.
3. Inspector verification: PASS with full per-AC evidence in `inspector-feedback-1.md`.

## Key issues raised and resolved

- Fail-open registry when `corpora` removed/empty -> fail-closed failures.
- Stale hardcoded inventory counts -> corrected + regenerated.
- `check-adr` missing from `VERIFY_CHECKS` -> added.
- WORKSPACE validation count drift -> corrected to 10 passed.
- Doc wording drift (governance.md, decisions README) -> fixed.
- Speculative `CorpusConfig.id_form` -> removed everywhere.
- Ruff findings (import order, duplicate `startswith`) -> fixed.

## Recommendations

- Pre-existing (unrelated): `test_build_inventory_is_deterministic_and_complete` hashes a CRLF-written fixture on Windows; normalize newlines in the fixture before hashing.
- Optional cleanup: `decisions_numbering_failures` duplicates `numbering_failures` shape; merging is a judgement call left open.
- `docs/agents/issue-tracker.md` is missing; run `/setup-mattpocock-skills` to restore it.