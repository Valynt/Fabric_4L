---
skill_id: pr-lifecycle
name: PR Lifecycle
version: 1.0.0
description: Full PR pipeline — branch, commit, push, create PR, monitor CI, respond to review feedback, merge to main, and clean up
side_effects: exec
timeout_ms: 600000
required_context: []
allowed_agents:
  - "*"
related_workflow: []
---

# PR Lifecycle

## When to Use

Use when implementation work is complete and you need to push it through the full PR pipeline:
- Branch creation from the correct base
- Staging and committing with conventional commit format
- Pushing to remote
- Creating a PR with the project's PR template
- Monitoring CI checks to completion
- Responding to PR review comments in-thread
- Merging to main after all checks pass and reviews are approved
- Cleaning up branches and worktrees

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| branch_name | string | yes | Feature branch name (e.g., `feat/layer4-checkpoint-resume`) |
| base_branch | string | no | Base branch to target (defaults to repo HEAD, usually `main`) |
| merge_strategy | string | no | `squash` (default), `merge`, or `rebase` |
| draft | boolean | no | Create as draft PR (default: false) |
| pr_title | string | no | PR title (defaults to last commit message subject) |
| pr_body | string | no | PR body (defaults to `.github/pull_request_template.md`) |

## Steps

### Step 1: Verify Before Pushing

Run the project's full verification gate before touching git:

```bash
make verify
```

If verification fails: stop, fix issues, re-run. Do not proceed with failing verification.

### Step 2: Ensure Clean Branch State

```bash
BRANCH=$(git branch --show-current)
git status --porcelain
```

- On `main`/`master`: create a feature branch (Step 3)
- On a feature branch with changes: proceed to Step 4 (commit)
- On a feature branch with no changes: skip to Step 5 (push)

### Step 3: Create Branch (if needed)

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)
git checkout -b <branch-name> "$BASE"
```

Branch naming: use descriptive names with conventional commit prefixes (`feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`, `ci/`, `perf/`).

### Step 4: Stage and Commit

```bash
git add -A
git diff --cached --stat
git commit -m "<type>(<scope>): <subject>" -m "<body>"
```

AI-assisted commits must include:

```
Co-authored-by: Ona <no-reply@ona.com>
```

Ensure pre-commit hooks are installed (`pre-commit install`) and passing. If hooks fail, fix and re-commit.

### Step 5: Push to Remote

```bash
git push -u origin <branch-name>
```

If push is rejected (remote has new commits):

```bash
git pull --rebase origin <base-branch>
git push -u origin <branch-name>
```

Never force-push to `main` or `master`. Force-push to feature branches only with explicit user request.

### Step 6: Create Pull Request

```bash
gh pr create \
  --base <base-branch> \
  --head <branch-name> \
  --title "<title>" \
  --body-file .github/pull_request_template.md
```

For draft PRs, add `--draft`.

Capture the PR number:

```bash
PR_NUMBER=$(gh pr view --json number -q '.number')
```

The PR body must include all required sections from `.github/pull_request_template.md`:
- Summary, Governance Impact, Change Type, API Evolution, Release & Policy Checklist, Incremental PR Gate Reporting, Validation, Code Quality Checklist, Risks/Rollback, PR Size & Status Policy.

### Step 7: Monitor CI Checks

```bash
gh pr checks "$PR_NUMBER" --watch
```

If checks fail:
1. Read failing check output: `gh pr checks "$PR_NUMBER" --json name,state,link -q '.[] | select(.state=="FAILURE") | "\(.name): \(.link)"'`
2. Diagnose the failure
3. Fix locally
4. Re-run `make verify`
5. Commit fix: `git commit -m "fix: address CI failure — <description>"`
6. Push: `git push origin <branch-name>`
7. Return to Step 7

If checks pass: continue to Step 8.

### Step 8: Respond to PR Review Comments

Check for review comments:

```bash
gh pr view "$PR_NUMBER" --json reviews,comments -q '.reviews[].body, .comments[].body'
gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments -q '.[] | "\(.id): \(.path):\(.line) — \(.body)"'
```

Reply to inline comments in their threads (not as top-level PR comments):

```bash
gh api repos/{owner}/{repo}/pulls/"$PR_NUMBER"/comments/<comment-id>/replies \
  -f body="<response>"
```

When responding to feedback:
- Understand the feedback before acting
- Verify against codebase reality
- Evaluate technical correctness for this codebase
- Respond with technical acknowledgment or reasoned pushback
- Implement fixes one item at a time, test each

After addressing feedback:
1. Commit: `git commit -m "fix: address review feedback — <description>"`
2. Push: `git push origin <branch-name>`
3. Reply to thread: `gh api .../comments/<comment-id>/replies -f body="Fixed in <commit-sha>. <description>."`
4. Return to Step 7 (monitor CI again)

### Step 9: Verify All Checks Pass Before Merge

```bash
gh pr checks "$PR_NUMBER"
gh pr view "$PR_NUMBER" --json reviewDecision -q '.reviewDecision'
```

Required before merge:
- All CI checks: `SUCCESS`
- Review decision: `APPROVED` (or no reviews required)
- No unresolved blocking review threads

If any check is failing or pending: do NOT merge. Return to Step 7 or Step 8.

### Step 10: Merge to Main

```bash
# Squash merge (preferred)
gh pr merge "$PR_NUMBER" --squash --delete-branch

# Merge commit (when individual commits matter)
gh pr merge "$PR_NUMBER" --merge --delete-branch

# Rebase merge (when linear history is required)
gh pr merge "$PR_NUMBER" --rebase --delete-branch
```

| Strategy | When to use |
|----------|-------------|
| `--squash` | Default — clean single-commit history on main |
| `--merge` | Multi-step refactors where individual commits matter |
| `--rebase` | Linear history required, commits well-organized |

If merge fails due to conflicts:

```bash
git fetch origin <base-branch>
git rebase origin/<base-branch>
git push --force-with-lease origin <branch-name>
```

Then retry the merge.

### Step 11: Cleanup

```bash
git checkout <base-branch>
git pull origin <base-branch>
git fetch --prune
git branch -d <branch-name>
```

If using a worktree (only clean up worktrees under `.worktrees/` or `worktrees/`):

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git worktree remove "$WORKTREE_PATH"
git worktree prune
```

## Output

| Field | Description |
|------|-------------|
| pr_number | The PR number created |
| pr_url | URL to the PR on GitHub |
| merge_commit | SHA of the merge commit on main |
| branch_deleted | Boolean — whether the feature branch was deleted |
| status | `merged` or `failed` with reason |

## Edge Cases

- **Push rejected (new remote commits):** Rebase onto base branch, resolve conflicts, push again.
- **CI flaky failures:** Re-run the failing check via `gh run rerun <run-id>`. If it passes on retry, proceed.
- **Review requested changes after CI passes:** Address feedback, push, re-monitor CI, re-verify before merge.
- **Merge conflict at merge time:** Rebase locally, force-push with lease, retry merge.
- **Branch protection rules block merge:** Ensure all required checks pass and required reviews are approved. Cannot bypass without admin override.
- **Draft PR:** CI may not run on draft PRs depending on repo settings. Mark as ready for review (`gh pr ready "$PR_NUMBER"`) when ready.
- **Multiple review rounds:** Each round of fixes requires re-running CI. Loop Steps 7–8 until all green.

## Anti-Patterns

- **Pushing without `make verify`** — CI will catch what you could have caught locally
- **Merging with failing or pending CI** — broken code lands on main
- **Replying to inline comments as top-level PR comments** — reviewers can't track which comment is addressed
- **Ignoring review comments** — address every comment: fix, push back with reasoning, or clarify
- **Force-pushing to main/master** — destroys shared history
- **Not deleting the branch after merge** — branch clutter accumulates
- **Skipping PR template sections** — all sections in `.github/pull_request_template.md` are required
- **Claiming completion without fresh verification evidence** — run the command, read the output, then claim the result
