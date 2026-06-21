# Tracked Secret-Bearing Files Report

**Generated:** 2026-05-02
**Constraint:** No file contents were read, printed, or modified.
**Purpose:** Inventory tracked non-example `.env` files for human credential rotation.

---

## Summary

| Metric | Count |
|--------|-------|
| Tracked `.env` files (all) | 13 |
| Tracked non-example `.env` files | 6 |
| Tracked `.env.example` files | 7 |
| Ignored `.env` files | 0 |

## Risk Classification Legend

| Class | Description |
|-------|-------------|
| **CRITICAL** | Non-example `.env` file tracked in Git. May contain live credentials. |
| **LOW** | `.env.example` template. Safe if it contains only placeholders. |

---

## Non-Example `.env` Files (CRITICAL)

| Path | Tracked | Ignored | Risk Class | Recommended Action |
|------|---------|---------|------------|-------------------|
| `frontend/.env.development` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.development.example`, purge history |
| `frontend/.env.production` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.production.example`, purge history |
| `frontend/.env.staging` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.staging.example`, purge history |
| `frontend/.env.test` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.test.example`, purge history |
| `.env.staging` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.staging.example`, purge history |
| `.env.test` | Yes | No | CRITICAL | Rotate any credentials, replace with `.env.test.example`, purge history |

## Example Template `.env` Files (LOW)

| Path | Tracked | Ignored | Risk Class | Recommended Action |
|------|---------|---------|------------|-------------------|
| `.env.dev.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `.env.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `frontend/.env.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `frontend/client/.env.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `tests/security/.env.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `.env.example` | Yes | No | LOW | Verify only placeholders. No action required. |
| `.env.production.example` | Yes | No | LOW | Verify only placeholders. No action required. |

---

## Blocker Status

- [ ] **Credential rotation** — Human action required. Rotate all credentials referenced by the 6 CRITICAL files before any Git purge.
- [ ] **Replace committed .env files with templates** — After rotation, remove non-example `.env` files from tracking and add `.env.*.example` templates.
- [ ] **History purge** — After rotation and replacement, use `git-filter-repo` or BFG Repo-Cleaner to purge `.env` file history.
- [ ] **Collaborator reclone** — All team members must reclone or hard-reset after history rewrite.

## Agent Constraints

Per cleanup guardrails, no agent has:
- Read the contents of any non-example `.env` file
- Modified, moved, or deleted any non-example `.env` file
- Printed or exposed any potential secret values

All `.env.example` files were verified (by earlier audit) to contain only placeholder values.
