---
name: pr-lifecycle
description: Use when work is complete and you need to push it through the full PR pipeline — branch, commit, push, create PR, monitor CI, respond to review feedback, merge to main, and clean up
---

# PR Lifecycle

## Overview

End-to-end PR pipeline: branch → commit → push → create PR → monitor CI → respond to reviews → merge → cleanup.

**Core principle:** Verify at every gate. Never skip CI. Never merge with failing checks.

**Announce at start:** "I'm using the pr-lifecycle skill to take this work through the full PR pipeline."

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`)
- Git remote `origin` points to the correct repository
- All implementation work is complete (use `test-driven-development` and `verification-before-completion` first)

## The Process

### Step 1: Verify Before Pushing

**Run the project's full verification gate before touching git:**

```bash
# Value Fabric canonical verification
make verify
```

**If verification fails:** Stop. Fix issues. Re-run. Do not proceed with failing verification.

**If verification passes:** Continue.

> See also: `verification-before-completion` skill — evidence before claims, always.

### Step 2: Ensure Clean Branch State

**Check current branch and status:**

```bash
BRANCH=$(git branch --show-current)
git status --porcelain
```

**If on `main` or `master`:** Create a feature branch first (Step 3).

**If already on a feature branch with changes:** Skip to Step 4 (commit).

**If on a feature branch with no changes:** Skip to Step 5 (push).

### Step 3: Create Branch (if needed)

```bash
# Determine base branch
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)

# Create and checkout feature branch
git checkout -b <branch-name> "$BASE"
```

**Branch naming:** Use descriptive names (e.g., `feat/layer4-checkpoint-resume`, `fix/tenant-isolation-l3`). No enforced pattern, but conventional commit prefixes are recommended.

> See also: `using-git-worktrees` skill if you need workspace isolation.

### Step 4: Stage and Commit

**Stage changes:**

```bash
git add -A
```

**Review what's staged before committing:**

```bash
git diff --cached --stat
```

**Commit with conventional commit format:**

```bash
git commit -m "<type>(<scope>): <subject>" -m "<body>"
```

**Co-author for AI-assisted commits:**

```
Co-authored-by: Ona <no-reply@ona.com>
```

**Commit types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`

**If the project requires pre-commit hooks:** Ensure they're installed (`pre-commit install`) and passing. If hooks fail, fix the issues and re-commit.

### Step 5: Push to Remote

```bash
git push -u origin <branch-name>
```

**If push is rejected (remote has new commits):**

```bash
git pull --rebase origin <base-branch>
git push -u origin <branch-name>
```

**Never force-push to `main` or `master`.** Force-push to feature branches only with explicit user request.

### Step 6: Create Pull Request

**Use `gh` CLI to create the PR:**

```bash
gh pr create \
  --base <base-branch> \
  --head <branch-name> \
  --title "<type>(<scope>): <subject>" \
  --body-file .github/pull_request_template.md
```

**Or provide the body inline.** The PR body must include the required sections from `.github/pull_request_template.md`:

- **Summary** — what changed and why
- **Governance Impact** — contract shape, tenant isolation, compatibility shim impact
- **Change Type** — Feature / Bug fix / Documentation / Refactor
- **Release & Policy Checklist** — contracts, API versioning, DR runbooks
- **Incremental PR Gate Reporting** — Pass/Fail status for each gate
- **Validation** — confirm `make verify` passed
- **Code Quality Checklist** — accessibility, imports, dead code
- **Risks / Rollback** — known risks and rollback plan
- **PR Size & Status Policy** — small/focused, draft if WIP

**For draft PRs:**

```bash
gh pr create --draft ...
```

**Capture the PR number:**

```bash
PR_NUMBER=$(gh pr view --json number -q '.number')
```

### Step 7: Monitor CI Checks

**Watch CI checks until they complete:**

```bash
gh pr checks "$PR_NUMBER" --watch
```

**If checks fail:**

1. Read the failing check output:
   ```bash
   gh pr checks "$PR_NUMBER" --json name,state,link -q '.[] | select(.state=="FAILURE") | "\(.name): \(.link)"'
   ```

2. Diagnose the failure (use `systematic-debugging` skill)

3. Fix the issue locally

4. Re-run local verification:
   ```bash
   make verify
   ```

5. Commit the fix:
   ```bash
   git add -A
   git commit -m "fix: address CI failure — <description>"
   ```

6. Push the fix:
   ```bash
   git push origin <branch-name>
   ```

7. Return to Step 7 (monitor CI again)

**If checks pass:** Continue to Step 8.

**CI timeout:** If checks don't complete within a reasonable time, check status without watching:

```bash
gh pr checks "$PR_NUMBER"
```

### Step 8: Respond to PR Review Comments

**Check for review comments:**

```bash
# List review comments
gh pr view "$PR_NUMBER" --json reviews,comments -q '.reviews[].body, .comments[].body'

# List inline review comments
gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments -q '.[] | "\(.id): \(.path):\(.line) — \(.body)"'
```

**Responding to inline review comments — reply in the thread, not as a top-level comment:**

```bash
gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments/<comment-id>/replies \
  -f body="<response>"
```

**When responding to feedback:**

> See also: `receiving-code-review` skill — verify before implementing, technical rigor over performative agreement.

- **Understand** the feedback before acting
- **Verify** against codebase reality
- **Evaluate** technical correctness for this codebase
- **Respond** with technical acknowledgment or reasoned pushback
- **Implement** fixes one item at a time, test each

**After addressing feedback:**

1. Commit fixes:
   ```bash
   git add -A
   git commit -m "fix: address review feedback — <description>"
   ```

2. Push:
   ```bash
   git push origin <branch-name>
   ```

3. Reply to the review thread confirming the fix:
   ```bash
   gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments/<comment-id>/replies \
     -f body="Fixed in <commit-sha>. <brief description of what changed>."
   ```

4. Return to Step 7 (monitor CI again)

**Resolving review threads:**

```bash
# Resolve a conversation thread
gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments/<comment-id>/replies \
  -f body="Addressed." \
  -F in_reply_to=<comment-id>
```

### Step 9: Verify All Checks Pass Before Merge

**Final verification before merging:**

```bash
# Check PR status — all CI must be green
gh pr checks "$PR_NUMBER"

# Check review status — all reviews must be approved or dismissed
gh pr view "$PR_NUMBER" --json reviewDecision -q '.reviewDecision'
```

**Required before merge:**
- All CI checks: `SUCCESS`
- Review decision: `APPROVED` (or no reviews required)
- No unresolved review threads with blocking changes

**If any check is failing or pending:** Do NOT merge. Return to Step 7 or Step 8.

### Step 10: Merge to Main

**Merge the PR:**

```bash
# Squash merge (preferred for clean history)
gh pr merge "$PR_NUMBER" --squash --delete-branch

# Or merge commit (if preserving commit history is important)
gh pr merge "$PR_NUMBER" --merge --delete-branch

# Or rebase merge (if linear history is required)
gh pr merge "$PR_NUMBER" --rebase --delete-branch
```

**Merge strategy selection:**

| Strategy | When to use |
|----------|-------------|
| `--squash` | Default — clean single-commit history on main |
| `--merge` | When individual commits matter (e.g., multi-step refactors) |
| `--rebase` | When linear history is required and commits are well-organized |

**If merge fails due to conflicts:**

```bash
# Pull latest base, rebase, push
git fetch origin <base-branch>
git rebase origin/<base-branch>
git push --force-with-lease origin <branch-name>
```

Then retry the merge.

### Step 11: Cleanup

**After successful merge with `--delete-branch`:**

```bash
# Switch back to base branch and pull latest
git checkout <base-branch>
git pull origin <base-branch>

# Prune deleted remote branches
git fetch --prune

# Delete local branch (if not already deleted)
git branch -d <branch-name>
```

**If using a worktree** (see `using-git-worktrees` skill):

```bash
# Only clean up worktrees under .worktrees/ or worktrees/
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git worktree remove "$WORKTREE_PATH"
git worktree prune
```

**Do NOT remove worktrees you didn't create.** Only clean up worktrees under `.worktrees/` or `worktrees/`.

## Quick Reference

| Step | Action | Gate |
|------|--------|------|
| 1 | Run `make verify` | Must pass |
| 2 | Check branch state | — |
| 3 | Create feature branch | — |
| 4 | Stage + commit | Pre-commit hooks must pass |
| 5 | Push to remote | Push must succeed |
| 6 | Create PR via `gh pr create` | PR must be created |
| 7 | Monitor CI via `gh pr checks --watch` | All checks must be SUCCESS |
| 8 | Respond to review comments | All feedback addressed |
| 9 | Verify checks + reviews | All green + APPROVED |
| 10 | Merge via `gh pr merge` | Merge must succeed |
| 11 | Cleanup branch + worktree | — |

## Common Mistakes

**Pushing without local verification**
- **Problem:** CI fails on something you could have caught locally
- **Fix:** Always run `make verify` before pushing

**Merging with failing CI**
- **Problem:** Broken code lands on main
- **Fix:** Never merge until all checks are SUCCESS

**Replying as top-level PR comments instead of thread replies**
- **Problem:** Reviewers can't track which comment is being addressed
- **Fix:** Use `gh api .../comments/<id>/replies` to reply in-thread

**Skipping review feedback**
- **Problem:** Reviewer concerns go unaddressed, blocking merge
- **Fix:** Address every comment — fix, push back with reasoning, or clarify

**Force-pushing to main**
- **Problem:** Destroys shared history, breaks collaborators
- **Fix:** Never force-push to `main` or `master`

**Not deleting the branch after merge**
- **Problem:** Branch clutter accumulates
- **Fix:** Use `--delete-branch` flag or delete manually

## Red Flags

**Never:**
- Push without running `make verify` first
- Merge with failing or pending CI checks
- Merge without review approval (when reviews are required)
- Force-push to `main` or `master`
- Ignore review comments — address every one
- Reply to inline comments as top-level PR comments
- Delete branches before confirming merge success
- Skip the PR template required sections

**Always:**
- Run `make verify` before pushing
- Use conventional commit format with co-author
- Fill in all required PR template sections
- Monitor CI to completion
- Reply to review comments in their threads
- Verify all checks are green before merging
- Delete the branch after merge
- Pull latest main after merge

## Integration with Other Skills

- **`using-git-worktrees`** — use before Step 3 if you need workspace isolation
- **`verification-before-completion`** — use at Step 1 and Step 9
- **`requesting-code-review`** — use before Step 6 for internal subagent review
- **`receiving-code-review`** — use at Step 8 when handling PR review feedback
- **`finishing-a-development-branch`** — this skill is a more detailed, PR-focused alternative
- **`systematic-debugging`** — use when CI failures need diagnosis
