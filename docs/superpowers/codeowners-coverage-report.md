# CODEOWNERS Coverage Report — Task P0.1

**Worktree:** `~/.config/superpowers/worktrees/Fabric_4L/remediation/code-health-2026-06-22`  
**Date:** 2026-06-22  
**Status:** DONE_WITH_CONCERNS  

## 1. Scope

The original remediation plan claimed the following files/pages were "unowned":

- `apps/web/src/auth/ClerkAuthBridge.tsx`
- `apps/web/src/components/routing/RequireClerkAuth.tsx`
- `apps/web/src/components/routing/UnifiedRouteGuard.tsx`
- `apps/web/src/contexts/AuthContext.tsx`
- `apps/web/src/pages/ClerkSignIn.tsx`
- Various admin and governance pages under `apps/web/`

This report verifies whether those paths are covered by existing patterns in `.github/CODEOWNERS`.

## 2. Static Pattern Coverage Check

### 2.1 Relevant CODEOWNERS patterns

| Line | Pattern | Owners |
|------|---------|--------|
| 5 | `*` | `@value-fabric/maintainers` |
| 15 | `**/*auth*` | `@value-fabric/security-leads` `@value-fabric/backend-leads` |
| 84 | `apps/web/` | `@value-fabric/frontend-leads` `@value-fabric/ux-designers` |
| 185 | `/apps/web/` | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |

GitHub CODEOWNERS resolves conflicts by **last matching pattern wins**.

### 2.2 File-by-file coverage

| File path | Matches `*` | Matches `**/*auth*` | Matches `apps/web/` | Matches `/apps/web/` | Effective owners (last match wins) |
|-----------|-------------|---------------------|---------------------|----------------------|------------------------------------|
| `apps/web/src/auth/ClerkAuthBridge.tsx` | Yes | Yes | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/components/routing/RequireClerkAuth.tsx` | Yes | Yes | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/components/routing/UnifiedRouteGuard.tsx` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/contexts/AuthContext.tsx` | Yes | Yes | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/pages/ClerkSignIn.tsx` | Yes | Yes | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/components/admin/*` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/governance/*` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/pages/admin/*` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/pages/Governance*.tsx` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |
| `apps/web/src/pages/TargetsAdmin*.tsx` | Yes | No | Yes | Yes | `@value-fabric/frontend-leads` `@value-fabric/sre-leads` |

### 2.3 Finding

**All files investigated are covered by at least one CODEOWNERS pattern.** The original claim that these files are "unowned" is **incorrect**.

The most specific applicable pattern for every file under `apps/web/` is `/apps/web/` at line 185, which assigns:

- `@value-fabric/frontend-leads`
- `@value-fabric/sre-leads`

### 2.4 Pattern-precedence concern

The security-critical auth files (e.g. `ClerkAuthBridge.tsx`, `RequireClerkAuth.tsx`, `AuthContext.tsx`) also match the earlier `**/*auth*` pattern at line 15, which would assign `@value-fabric/security-leads` and `@value-fabric/backend-leads`. Because `/apps/web/` appears later in the file, it overrides the auth-specific pattern for all files under `apps/web/`. This may be unintended from a security-ownership perspective, but it does **not** mean the files are unowned.

> No change to `.github/CODEOWNERS` was made because team membership could not be verified via `gh` (see Section 3).

## 3. Team Membership Check

### 3.1 Attempted commands

| Team | Command | Result |
|------|---------|--------|
| `value-fabric/maintainers` | `gh api orgs/value-fabric/teams/maintainers/members` | HTTP 404 Not Found |
| `value-fabric/security-leads` | `gh api orgs/value-fabric/teams/security-leads/members` | HTTP 404 Not Found |
| `value-fabric/backend-leads` | `gh api orgs/value-fabric/teams/backend-leads/members` | HTTP 404 Not Found |
| `value-fabric/frontend-leads` | `gh api orgs/value-fabric/teams/frontend-leads/members` | HTTP 404 Not Found |

### 3.2 `gh` auth status

```text
github.com
  ✓ Logged in to github.com account bmsull560 (keyring)
  - Active account: true
  - Git operations protocol: https
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

### 3.3 Blocker

The `gh` CLI is authenticated to account `bmsull560`, but this worktree's `origin` remote is `https://github.com/bmsull560/Fabric_4L.git`. The CODEOWNERS file references teams under the `value-fabric` organization (`@value-fabric/...`). All API calls to `orgs/value-fabric/teams/...` returned **404 Not Found**.

Possible explanations:

1. This repository is a fork; the `value-fabric` teams exist only in the upstream organization and are not resolvable from `bmsull560/Fabric_4L`.
2. The authenticated token lacks access to the `value-fabric` organization.
3. The `value-fabric` organization or teams do not exist.

**Conclusion:** Team membership and emptiness cannot be verified. Per task instructions, `.github/CODEOWNERS` was left unchanged.

## 4. Branch Protection Check

### 4.1 Corrected command

```bash
gh api repos/bmsull560/Fabric_4L/branches/main/protection \
  --jq '{required_pull_request_reviews: .required_pull_request_reviews}'
```

### 4.2 Result

```json
{"required_pull_request_reviews":null}
```

### 4.3 Interpretation

`required_pull_request_reviews` is `null`, which means the `main` branch in `bmsull560/Fabric_4L` has **no required pull request review policy** configured. Consequently, **`require_code_owner_reviews` is not enabled**.

This is a **Confirmed Null** finding: we successfully queried the actual remote and confirmed that branch protection does not currently require CODEOWNERS review.

## 5. Summary

| Item | Category | Result |
|------|----------|--------|
| Static pattern coverage | **Confirmed** | **PASS** — all investigated files are covered by CODEOWNERS patterns. |
| Team membership verification | **Blocked / Missing Data** | `gh` returns 404 for all `value-fabric` team APIs; cannot verify teams from this fork context. |
| Branch protection verification | **Confirmed Null** | Query against `bmsull560/Fabric_4L` succeeded; `required_pull_request_reviews` is `null`, so `require_code_owner_reviews` is **not enabled**. |
| CODEOWNERS modified | **Confirmed** | **No** — team emptiness could not be verified. |

## 6. Recommendations

1. **Close the P0.1 "unowned files" finding** because the listed paths are all covered by existing patterns.
2. **Review pattern precedence** for `apps/web/` auth files if the intent is for `@value-fabric/security-leads` to co-own them. Consider moving the `**/*auth*` pattern after the `apps/web/` patterns, or adding an explicit `apps/web/**/auth/` or `apps/web/src/auth/` pattern.
3. **Verify team references** against the actual repository owner (`bmsull560` vs `value-fabric`) before relying on CODEOWNERS enforcement in this fork.
4. **Re-run team/branch-protection checks** from a context authenticated against the `value-fabric` organization.
