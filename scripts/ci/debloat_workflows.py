#!/usr/bin/env python3
"""De-bloat oversized .devin/workflows by extracting detailed content to skill docs."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".devin" / "workflows"
SKILLS_DIR = ROOT / ".devin" / "skills"


def rewrite_launch_readiness() -> int:
    src = WORKFLOWS_DIR / "launch-readiness-assessment.md"
    content = src.read_text(encoding="utf-8")

    # 1. Condense sprint plan in workflow steps (lines ~123-166)
    old_sprints = """6. **Generate a Refreshed 5-Sprint Plan**

   **Sprint 1 — Launch Gate Repair and Baseline Evidence**
   - Goal: Align `prod-readiness.yml` to the commands and files that actually exist now.
   - Tasks:
     - [ ] Repair missing policy/config references used by launch gates
     - [ ] Replace or restore missing `make` targets referenced by `prod-readiness.yml`
     - [ ] Ensure launch-gate jobs produce fresh `arch`, `security`, `agent`, `state`, `obs`, and `release` artifacts
     - [ ] Re-run baseline gate sequence using current repo commands
   - Exit Criteria: The launch-gate workflow runs end-to-end and any remaining failures are real product failures, not broken gate plumbing.

   **Sprint 2 — Security Isolation and Contract Closure**
   - Goal: Clear the current security-isolation and contract-drift blockers.
   - Tasks:
     - [ ] Fix the reported cross-tenant access success path
     - [ ] Raise critical-endpoint isolation test coverage from 85% to 100%
     - [ ] Clear the single contract-drift violation
     - [ ] Regenerate fresh `artifacts/security/*` and `artifacts/arch/*`
   - Exit Criteria: Fresh arch and security artifacts both pass.

   **Sprint 3 — Monitoring, Health, and Kubernetes Verification**
   - Goal: Produce real verification for observability and deployment readiness.
   - Tasks:
     - [ ] Verify Prometheus endpoints return real counters
     - [ ] Verify health checks expose actual dependency status
     - [ ] Verify Kubernetes manifests render cleanly and deploy in staging or equivalent validation path
     - [ ] Produce the missing observability evidence artifacts
   - Exit Criteria: Health, metrics, and Kubernetes checklist items are verified from current evidence, not inferred.

   **Sprint 4 — L1 Ingestion Hardening and Runtime Confidence**
   - Goal: Verify or finish the remaining L1 launch-critical runtime work.
   - Tasks:
     - [ ] Confirm actual Celery/Redis wiring status with code and runtime evidence
     - [ ] Complete any remaining rate-limit/runtime hardening needed for launch
     - [ ] Re-run smoke and integration paths against the validated L1 state
     - [ ] Decide whether any remaining L1 gaps are launch blockers or explicit post-launch carryovers
   - Exit Criteria: L1 reaches target with evidence, or is explicitly de-scoped from initial launch with recorded risk acceptance.

   **Sprint 5 — Final Evidence Refresh and Go/No-Go**
   - Goal: Re-run the full evidence stack and produce a final launch decision.
   - Tasks:
     - [ ] Re-run gate, smoke, and verification artifacts
     - [ ] Recompute the dual-track readiness table
     - [ ] Refresh the final launch checklist
     - [ ] Produce explicit go/no-go status with owners for any carryovers
   - Exit Criteria: The release policy is green, or the final report documents a no-go decision with residual blockers and owners."""

    new_sprints = """6. **Generate a Refreshed 5-Sprint Plan**

   Produce a dependency-aware 5-sprint plan tied to the top blockers:
   - Sprint 1 — Launch Gate Repair and Baseline Evidence
   - Sprint 2 — Security Isolation and Contract Closure
   - Sprint 3 — Monitoring, Health, and Kubernetes Verification
   - Sprint 4 — L1 Ingestion Hardening and Runtime Confidence
   - Sprint 5 — Final Evidence Refresh and Go/No-Go

   See `.devin/skills/launch-readiness-assessment/SKILL.md` for full sprint templates."""

    content = content.replace(old_sprints, new_sprints)

    # 2. Remove Output Format template, Execution Log, Concrete Actions
    old_tail = """## Output Format

```markdown
# Launch Readiness Assessment - {YYYY-MM-DD}

**Claimed Readiness: {N}%**
**Verified Readiness: {N}% | Blocked**

| Layer | Claimed | Verified | Target | Gap | Evidence |
|-------|---------|----------|--------|-----|----------|
| L1 Ingestion | {N}% | {N}% / Unverified / Blocked | 90% | {text} | {artifact or note} |
| L2 Extraction | {N}% | {N}% / Unverified / Blocked | 95% | {text} | {artifact or note} |
| L3 Knowledge | {N}% | {N}% / Unverified / Blocked | 90% | {text} | {artifact or note} |
| L4 Agents | {N}% | {N}% / Unverified / Blocked | 85% | {text} | {artifact or note} |
| L5 Ground Truth | 100% | {N}% / Unverified / Blocked | 100% | {text} | {artifact or note} |
| Frontend | {N}% | {N}% / Unverified / Blocked | 85% | {text} | {artifact or note} |
| DevOps | {N}% | {N}% / Unverified / Blocked | 80% | {text} | {artifact or note} |

## L6 Benchmarks Note
- Claimed: {text}
- Verified: {text}
- Launch relevance: {text}

## Top 5 Launch Blockers
1. [Blocker] -> [Evidence] -> [Owning sprint]
2. ...

## Refreshed 5-Sprint Plan
### Sprint 1 — Launch Gate Repair and Baseline Evidence
- Goal: ...
- Exit Criteria: ...

### Sprint 2 — Security Isolation and Contract Closure
- Goal: ...
- Exit Criteria: ...

### Sprint 3 — Monitoring, Health, and Kubernetes Verification
- Goal: ...
- Exit Criteria: ...

### Sprint 4 — L1 Ingestion Hardening and Runtime Confidence
- Goal: ...
- Exit Criteria: ...

### Sprint 5 — Final Evidence Refresh and Go/No-Go
- Goal: ...
- Exit Criteria: ...

## Quick Wins
- [ ] [Quick win]

## Launch Checklist ({met}/{total} verified)
- [ ] [Criterion]
```

## Execution Log Format

Present progress using this structured format:

```
[INIT] Loaded ROADMAP.md, prior assessments, and newest local evidence artifacts
[GATES] Launch-gate integrity: commands={ok|drift} policy={ok|missing} artifacts={ok|missing}
[ASSESS] Claimed readiness captured for L1-L5, Frontend, DevOps; L6 noted separately
[VERIFY] Fresh evidence mapped to arch/security/state/agent/obs/smoke signals
[RISKS] Identified top 5 blockers from verified evidence
[PLAN] Generated refreshed 5-sprint sequence around current blockers
[CHECKLIST] Final launch checklist: {N}/{total} verified
[REVIEW] Presenting assessment and awaiting approval before creating any dated artifact
[ARTIFACTS] User approved - creating new dated launch-readiness report
[COMPLETE] Assessment saved without touching archived or superseded reports
```

## Concrete Actions Checklist

- [ ] Read and analyzed `ROADMAP.md` current claimed state
- [ ] Read newest local evidence artifacts across release, arch, security, smoke, and test outputs
- [ ] Verified launch-gate workflow integrity against current repo files and commands
- [ ] Built a dual-track readiness table with claimed and verified fields
- [ ] Identified top 5 blockers from current evidence
- [ ] Generated a refreshed 5-sprint plan tied to those blockers
- [ ] Kept L6 separate from the main readiness table
- [ ] Presented assessment without creating artifacts
- [ ] Only after approval: created a new dated report in `.windsurf/plans/`
- [ ] Preserved older dated assessments and archived Phase 2 documents

## Safety Rules"""

    new_tail = """## Output Format

Generate a dated report following the template in `.devin/skills/launch-readiness-assessment/SKILL.md`.
Include: readiness table, L6 note, top 5 blockers, 5-sprint plan, quick wins, and launch checklist.

## Safety Rules"""

    content = content.replace(old_tail, new_tail)

    src.write_text(content, encoding="utf-8")
    new_len = len(content.splitlines())
    print(f"launch-readiness-assessment.md: {new_len} lines")
    return new_len


def rewrite_fumadocs_drift_audit() -> int:
    src = WORKFLOWS_DIR / "fumadocs-drift-audit.md"
    content = src.read_text(encoding="utf-8")

    # Extract the massive remediation pack tables and detailed output format
    # Replace with a concise reference
    old_remediation = """### 8. Produce Remediation Pack

Deliver structured findings with actionable fixes.

**Required Deliverables:**

#### A. Executive Summary
- Total drift instances found: N
- Drift categories: [component|routing|navigation|theme|build|content]
- Risk level: [Critical|High|Medium|Low]
- Estimated effort to remediate: [hours/days]

#### B. Prioritized Findings

**Stale Commands:**
| Command | Doc Location | Current Behavior | Fix |
|---------|--------------|------------------|-----|
| | | | |

**Stale Component Names:**
| Documented Name | Actual Name | File | Fix |
|-------------------|-------------|------|-----|
| | | | |

**Stale File Paths:**
| Documented Path | Actual Path | References | Fix |
|-----------------|-------------|------------|-----|
| | | | |

**Moved Routes:**
| Old Route | New Route | Redirect Needed? | Docs Updated? |
|-----------|-----------|------------------|---------------|
| | | | |

**Hidden Prerequisites:**
| Requirement | Where Required | Currently Documented? | Action |
|-------------|----------------|----------------------|--------|
| | | | |

**Incomplete Examples:**
| Example Location | Issue | Missing | Fix |
|------------------|-------|---------|-----|
| | | | |

**Duplicate/Overlapping Docs:**
| Documents | Overlap Area | Recommendation |
|-----------|--------------|----------------|
| | | |

**Content/UI Mismatch:**
| Doc Description | Actual UI | Location | Fix |
|-----------------|-----------|----------|-----|
| | | | |

#### C. Exact Files to Update

| Priority | File | Change Type | Effort |
|----------|------|-------------|--------|
| P0 | | | |
| P1 | | | |
| P2 | | | |

#### D. Draft Markdown for Top 3 Fixes

Provide ready-to-paste markdown updates for highest-value fixes.

---

## Output Format

### Changed File Impact Table

```markdown
| File | Change Type | Impact Area | Doc Action |
|------|-------------|-------------|------------|
| `app/docs/layout.tsx` | Modified | Layout | Check layout docs, sidebar config |
| `lib/source.ts` | Modified | Source Loading | Update content source documentation |
| `components/mdx.tsx` | Added | MDX Components | Document new components |
| `content/docs/api/*.mdx` | Deleted | Content | Remove or redirect broken links |
```

### Topic-Doc Inventory

```markdown
| Topic | Docs Found | Coverage | Status |
|-------|------------|----------|--------|
| | | | |
```"""

    new_remediation = """### 8. Produce Remediation Pack

Deliver structured findings with actionable fixes.
Use the drift-assessment report template in `.devin/skills/fumadocs/SKILL.md`.

---

## Output Format

See `.devin/skills/fumadocs/SKILL.md` for report templates."""

    content = content.replace(old_remediation, new_remediation)

    # Also trim the Diátaxis alignment tables
    old_diataxis = """**Alignment Drift to Detect:**

| Diátaxis Type | Fumadocs Presentation | Drift Indicator |
|---------------|----------------------|-----------------|
| **Tutorials** | `/tutorials/` section with ordered `meta.json` | Flat nav breaks linear flow |
| | "Next step" buttons at page bottom | Missing progression cues |
| | Sequential breadcrumbs (Step 1 → 2 → 3) | No hierarchy shown |
| **How-to Guides** | `/how-to/` clearly labeled in sidebar | Mixed with other types |
| | Search-weighted prominence | Buried in nav hierarchy |
| | Task-focused page titles | Vague/generic titles |
| **Reference** | `/reference/` with dense layout | Blog-style spacing |
| | Auto-generated API tables | Manual, error-prone tables |
| | Tabbed interface (params, responses, errors) | Long scroll-only pages |
| **Explanation** | `/explanation/` distinct styling | Same layout as tutorials |
| | Minimal sidebar interruptions | Heavy nav chrome |
| | Essay-like reading flow | Fragmented by CTAs |

**Concrete Checks:**

```bash
# Verify Diátaxis folder structure preserved
grep -r "category.*tutorial\|category.*how-to\|category.*reference\|category.*explanation" content docs --include="*.mdx"

# Check meta.json enforces ordering in tutorials
find content -path "*/tutorials/meta.json" -exec cat {} \;

# Verify type-specific frontmatter
head -20 content/tutorials/*/index.mdx | grep -E "^type:|^category:|^order:"

# Check layout differences per type
ls -la app/docs/
```

**Red Flags:**
- All doc types use identical layouts
- Navigation doesn't signal doc type visually
- Tutorials lack explicit "next" links
- Reference pages use blog-style wide spacing
- How-to guides mixed without task-oriented grouping
- Search doesn't weight reference higher than explanation

**Deliverable:**
- Diátaxis type coverage: N tutorials, N how-to, N reference, N explanation
- Layout alignment issues found: N
- Navigation structure drift: [Y/N]"""

    new_diataxis = """**Alignment Drift to Detect:**

Ensure Fumadocs presentation matches Diátaxis content semantics:
- Tutorials need ordered nav, "next" links, sequential breadcrumbs
- How-to guides need search prominence, task-focused titles
- Reference needs dense layout, auto-generated tables, tabs
- Explanation needs distinct styling, minimal nav chrome, essay flow

**Concrete Checks:**

```bash
# Verify Diátaxis folder structure preserved
grep -r "category.*tutorial\|category.*how-to\|category.*reference\|category.*explanation" content docs --include="*.mdx"

# Check meta.json enforces ordering in tutorials
find content -path "*/tutorials/meta.json" -exec cat {} \;
```

See `.devin/skills/fumadocs/SKILL.md` for the full alignment checklist."""

    content = content.replace(old_diataxis, new_diataxis)

    src.write_text(content, encoding="utf-8")
    new_len = len(content.splitlines())
    print(f"fumadocs-drift-audit.md: {new_len} lines")
    return new_len


def rewrite_autonomous_test_assurance() -> int:
    src = WORKFLOWS_DIR / "autonomous-test-assurance-agent.md"
    content = src.read_text(encoding="utf-8")

    # Remove the massive Example Test Patterns section
    old_examples = """### 4.4 Example Test Patterns

**Python (pytest) - Tenant Isolation:**

```python
# Positive test
async def test_user_can_read_own_tenant_data(client, auth_headers, tenant_a):
    \"\"\"Proves tenant A user can read tenant A data.\"\"\"
    response = await client.get(
        "/api/entities",
        headers={**auth_headers, "X-Tenant-ID": tenant_a.id}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(e["tenant_id"] == tenant_a.id for e in data)

# Negative test
async def test_user_cannot_read_other_tenant_data(client, auth_headers, tenant_a, tenant_b):
    \"\"\"Proves tenant A user cannot read tenant B data.\"\"\"
    # Create entity in tenant B
    entity_b = await create_entity(tenant_id=tenant_b.id)

    # Try to access as tenant A user
    response = await client.get(
        f"/api/entities/{entity_b.id}",
        headers={**auth_headers, "X-Tenant-ID": tenant_a.id}
    )
    assert response.status_code == 404  # Not 403 - don't reveal existence
```

**TypeScript (Vitest) - Auth Guard:**

```typescript
// Positive test
it('allows authenticated users to access protected route', async () => {
  const wrapper = render(<ProtectedRoute />, {
    wrapper: createAuthWrapper({ isAuthenticated: true, user: mockUser })
  });

  await waitFor(() => {
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument();
  });
});

// Negative test
it('redirects unauthenticated users to login', async () => {
  const wrapper = render(<ProtectedRoute />, {
    wrapper: createAuthWrapper({ isAuthenticated: false })
  });

  await waitFor(() => {
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });
});
```"""

    new_examples = """### 4.4 Example Test Patterns

See `.devin/skills/autonomous-test-assurance/SKILL.md` for full test pattern examples in Python and TypeScript."""

    content = content.replace(old_examples, new_examples)

    # Remove the massive report template in Phase 7
    old_report = """### 7.1 Self-Generate Remediation Report

**Autonomous action**: Create `artifacts/testing/assurance-remediation-report.md` with complete context:

```markdown
# Test Assurance Remediation Report

## Executive Summary
- Production invariants identified: N
- P0 gaps addressed: N
- P1 gaps addressed: N
- Tests added: N positive, N negative
- Tests refactored: N
- Production fixes required: N (minimal)
- Production-assurance score before: X%
- Production-assurance score after: Y%

## Test Coverage Map
[Link to test-inventory.md]

## Production Invariants
[Link to invariants document]

## Test Gap Matrix
[Link to gap matrix with status updates]

## Tests Added

### Positive Tests
| File | Test | Boundary Covered | Status |
|------|------|------------------|--------|
| | | | |

### Negative/Adversarial Tests
| File | Test | Boundary Covered | Status |
|------|------|------------------|--------|
| | | | |

### Regression Tests
| File | Test | Violation Fixed | Status |
|------|------|-----------------|--------|
| | | | |

## Tests Refactored

| File | Change | Risk Covered |
|------|--------|--------------|
| | | |

## Production Code Changes

| File | Change | Reason |
|------|--------|--------|
| | | |

## Commands Run

```bash
# Narrow tests
pytest tests/security/test_tenant_isolation.py -v
# Result: X passed, Y failed

# Broader gate
make test-security
# Result: All passed
```

## Remaining P0/P1 Gaps

| Boundary | Reason Not Addressed | Recommended Action |
|----------|---------------------|-------------------|
| | | |

## Residual Risk

- [ ] Description of remaining risk

## Recommended CI Production Gate

```yaml
# Suggested addition to CI
- name: Production Assurance Gate
  run: |
    pnpm test:security
    pnpm test:tenant-isolation
    pnpm test:authorization
```

## PR Review Checklist

- [ ] Tests are meaningful
- [ ] Negative tests fail on vulnerable behavior
- [ ] Mocks are not hiding the real boundary
- [ ] Selectors are stable
- [ ] Assertions are atomic
- [ ] CI is updated if needed
```"""

    new_report = """### 7.1 Self-Generate Remediation Report

**Autonomous action**: Create `artifacts/testing/assurance-remediation-report.md`.
Use the report template in `.devin/skills/autonomous-test-assurance/SKILL.md`."""

    content = content.replace(old_report, new_report)

    # Remove High-Value First Targets section
    old_targets = """## High-Value First Targets

### Priority 1: Tenant Isolation
```bash
# Start here
grep -r "tenant_id" services/*/src/api/routes.py --include="*.py"
```

Tests to add:
- Cross-tenant read denied
- Cross-tenant write denied
- Spoofed tenant header ignored/rejected
- Missing tenant context fails closed
- Tenant ID in route/body/query cannot override authenticated context

### Priority 2: Authorization
```bash
grep -r "role\|permission\|admin" services/*/src/ --include="*.py" | grep -i "require\|check\|verify"
```

Tests to add:
- Unauthenticated request returns 401
- Authenticated wrong-role request returns 403
- User cannot access another user's resource
- Admin-only actions require admin role

### Priority 3: Input Validation
```bash
grep -r "BaseModel\|validator\|Field" services/*/src/models/ --include="*.py"
```

Tests to add:
- Malformed payload rejected
- Unknown fields rejected or ignored by policy
- Unsafe strings sanitized
- Invalid enum/state transition rejected

### Priority 4: Database/RLS
```bash
grep -r "USING\|WITH CHECK" services/*/migrations/ --include="*.sql"
```

Tests to add:
- Tenant A cannot SELECT tenant B
- Tenant A cannot UPDATE tenant B
- Tenant A cannot DELETE tenant B

### Priority 5: Webhook/Job Idempotency
```bash
grep -r "idempotency\|dedup" services/*/src/ --include="*.py"
```

Tests to add:
- Duplicate event does not duplicate side effects
- Failed job retries safely
- Poison message goes to DLQ

### Priority 6: Frontend Route Guards
```bash
grep -r "RouteGuard\|ProtectedRoute\|useAuth" apps/web/src/ --include="*.tsx"
```

Tests to add:
- Protected routes redirect unauthenticated users
- Tenant switch clears stale state
- Forbidden resources show safe error state

---

## CI Gate Definition"""

    new_targets = """## High-Value First Targets

Target areas in priority order:
1. **Tenant Isolation** — cross-tenant read/write, spoofed headers, missing context
2. **Authorization** — 401/403 boundaries, role checks, resource ownership
3. **Input Validation** — malformed payloads, unknown fields, unsafe strings
4. **Database/RLS** — USING/WITH CHECK enforcement
5. **Webhook/Job Idempotency** — duplicate events, retries, DLQ
6. **Frontend Route Guards** — auth redirects, tenant switch, error states

See `.devin/skills/autonomous-test-assurance/SKILL.md` for grep commands and full test templates per priority.

---

## CI Gate Definition"""

    content = content.replace(old_targets, new_targets)

    # Also remove the detailed refactoring patterns in Phase 5
    old_refactor_patterns = """### 5.3 Refactoring Patterns

**Before/After: Weak Assertion:**

```python
# Before - vague
assert result is not None

# After - explicit
assert result.status == "completed"
assert result.tenant_id == expected_tenant_id
```

**Before/After: Positional Selector:**

```typescript
// Before - fragile
const button = container.querySelector('button:nth-child(2)');

// After - stable
const button = screen.getByRole('button', { name: /submit/i });
```

**Before/After: Over-Mocked Security:**

```python
# Before - mocks bypass real auth
@patch('auth.verify_token', return_value=mock_user)
def test_route_with_auth(mock_verify):
    response = client.get("/protected")
    assert response.status_code == 200

# After - tests real boundary
def test_route_with_valid_token(client, valid_token):
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
```"""

    new_refactor_patterns = """### 5.3 Refactoring Patterns

See `.devin/skills/autonomous-test-assurance/SKILL.md` for before/after examples covering weak assertions, positional selectors, and over-mocked security."""

    content = content.replace(old_refactor_patterns, new_refactor_patterns)

    # Remove the detailed security checklist in 4.3
    old_security_checklist = """### 4.3 Security Test Requirements

For each boundary:

```markdown
## Security Test Checklist

### Authentication
- [ ] Missing auth fails (401)
- [ ] Invalid auth fails (401)
- [ ] Expired token fails (401)
- [ ] Malformed token fails (401)

### Authorization
- [ ] Wrong role fails (403)
- [ ] User accessing another user's resource fails
- [ ] Admin-only actions require admin role

### Tenant Isolation
- [ ] Wrong tenant fails
- [ ] Spoofed tenant headers fail/rejected
- [ ] Route/body/query tenant mismatch fails
- [ ] Missing tenant context fails closed

### Input Validation
- [ ] Malformed input fails safely
- [ ] Unknown fields rejected (or ignored by policy)
- [ ] Unsafe strings sanitized
- [ ] Invalid enum/state transition rejected
- [ ] Oversized payloads rejected

### Destructive Actions
- [ ] Require ownership proof
- [ ] Require authorization proof
- [ ] Require confirmation (frontend)

### Secrets Protection
- [ ] Sensitive fields not in errors
- [ ] Sensitive fields not in logs
- [ ] Sensitive fields not in responses
- [ ] API keys redacted in audit logs

### Idempotency
- [ ] Duplicate webhook doesn't double-apply
- [ ] Failed job retries safely
- [ ] Poison messages go to DLQ
- [ ] Missing idempotency key handled safely
```"""

    new_security_checklist = """### 4.3 Security Test Requirements

For each boundary, verify authentication, authorization, tenant isolation, input validation, destructive actions, secrets protection, and idempotency.
See `.devin/skills/autonomous-test-assurance/SKILL.md` for the full security test checklist."""

    content = content.replace(old_security_checklist, new_security_checklist)

    src.write_text(content, encoding="utf-8")
    new_len = len(content.splitlines())
    print(f"autonomous-test-assurance-agent.md: {new_len} lines")
    return new_len


def main() -> int:
    lines = {}
    lines["launch-readiness-assessment.md"] = rewrite_launch_readiness()
    lines["fumadocs-drift-audit.md"] = rewrite_fumadocs_drift_audit()
    lines["autonomous-test-assurance-agent.md"] = rewrite_autonomous_test_assurance()

    print("\nDe-bloat complete.")
    for name, count in lines.items():
        print(f"  {name}: {count} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
