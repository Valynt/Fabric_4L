# DOC-002 README Setup Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining README claim that `make setup` starts infrastructure and applies migrations, and prevent that exact documentation drift from returning.

**Architecture:** Treat the Makefile `setup` target as the executable source of truth and the README as a tested consumer of that contract. Make one copy-only correction and extend the existing documentation contract suite rather than adding a new checker or workflow.

**Tech Stack:** Markdown, Python 3.11+, pytest.

## Global Constraints

- Preserve the existing Quickstart, command names, and canonical documentation links.
- Do not change runtime code, public contracts, dependencies, lockfiles, generated files, workflows, migrations, or security controls.
- Preserve unrelated local changes.
- Use pnpm only if a Node command becomes necessary; do not use npm or yarn.

---

### Task 1: Align and enforce the README setup description

**Files:**
- Modify: `README.md`
- Test: `tests/docs/test_command_map.py`

**Interfaces:**
- Consumes: the `Makefile` `setup` target, whose documented responsibility is installing service development dependencies into the pytest Python environment.
- Produces: a README command-table row containing `| \`make setup\` | Install Python service development dependencies |` and a pytest regression assertion for that exact contract.

- [ ] **Step 1: Confirm the regression assertion detects the stale contract**

Inspect the implementation commit's parent and verify its README contains:

```markdown
| `make setup` | Install deps, start dev services, apply migrations |
```

Then verify the added test requires the corrected row and rejects this stale row. Expected: the assertion is incompatible with the parent README and therefore guards the intended drift.

- [ ] **Step 2: Verify the focused regression test passes on the implementation**

Run:

```bash
pytest tests/docs/test_command_map.py::test_readme_describes_make_setup_as_dependency_install_only -v
```

Expected: one test passes.

- [ ] **Step 3: Run the complete command-map documentation suite**

Run:

```bash
pytest tests/docs/test_command_map.py -v
```

Expected: all tests in the file pass with no failures.

- [ ] **Step 4: Run repository diff hygiene and relevant command-map validation**

Run:

```bash
git diff --check origin/main...HEAD
pnpm docs:check
```

Expected: no whitespace errors and the documented repository docs validation passes.

- [ ] **Step 5: Review scope and publish**

Confirm the branch changes only the approved design record, README row, and focused documentation test. Commit any remaining approved files with a conventional message and `Co-authored-by: Ona <no-reply@ona.com>`, push the finding branch, and open or update a draft PR containing finding ID `DOC-002`, inspected files, exact validation results, rollback, and residual risk.
