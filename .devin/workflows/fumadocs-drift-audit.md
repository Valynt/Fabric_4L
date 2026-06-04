---
workflow_id: fumadocs-drift-audit
name: Fumadocs Drift Audit
version: 1.0.0
description: Audit Fumadocs documentation drift for ongoing maintenance and migration
pattern: circuit-breaker
risk_level: low
---

# Fumadocs Drift Audit Workflow

Systematic audit of Fumadocs-based documentation to detect drift between code implementation and documentation, ensuring ongoing maintenance quality.

## Mental Model: Diátaxis → Fumadocs

```
Diátaxis (Content Model)          Fumadocs (Delivery System)
─────────────────────           ─────────────────────────
WHAT the docs are                 HOW the docs are delivered

/docs/tutorials/                  Fumadocs Layouts
/docs/how-to/          →         Navigation Trees
/docs/reference/                  Search + Components
/docs/explanation/                Theming + UX
```

**This workflow is for post-migration maintenance.** After initial setup:
- Diátaxis structure lives in content files
- Fumadocs renders, structures, and delivers that content
- The audit ensures Fumadocs correctly expresses Diátaxis semantics

**Alignment checks:**
| Diátaxis Type | Presentation Need | Fumadocs Support |
|---------------|-------------------|------------------|
| **Tutorials** | Linear progression | Ordered nav, "next step" flow |
| **How-to** | Fast lookup | Search prominence, minimal noise |
| **Reference** | Completeness | Structured tables, API rendering |
| **Explanation** | Narrative depth | Long-form layout, fewer interruptions |

## When to Use

- **Post-Release**: After code changes affecting routes, layouts, or components
- **Periodic Maintenance**: Monthly/quarterly documentation health checks
- **Pre-Migration**: Before migrating documentation to Fumadocs
- **Drift Detection**: When docs appear out of sync with UI or API behavior
- **Package Updates**: After upgrading `fumadocs-*` packages

## Activation Criteria

Do not treat package version changes alone as meaningful. The audit is only complete after checking:
- Route structure changes
- Source loading configuration
- Navigation tree generation
- MDX components
- API/OpenAPI generation
- Layout and theme modifications

## Prerequisites

- Git history accessible
- Fumadocs packages installed (`fumadocs-core`, `fumadocs-ui`, `fumadocs-mdx`)
- Documentation files in version control
- Ability to run dev/build commands

---

## Workflow Steps

### 1. Locate the Baseline Commit

Find the last commit that materially changed Fumadocs packages or docs-framework wiring.

**Concrete Actions:**
```bash
# Find commits that changed fumadocs packages
git log --all --full-history -- '*.json' '*.ts' '*.js' | grep -A5 -B5 "fumadocs-"

# Find last docs structure change
git log --all --oneline -- 'content/**' 'docs/**' 'app/**/docs/**' | head -20

# Identify baseline (last known good docs state)
git log --oneline --grep="docs" --grep="documentation" --all-match | head -10
```

**What to Look For:**
- Changes to `fumadocs-core`, `fumadocs-ui`, `fumadocs-mdx` dependencies
- Modifications to `source.config.ts` or `lib/source.ts`
- Layout component changes (`app/layout.tsx`, `app/docs/layout.tsx`)
- Route handler modifications (`app/docs/[[...slug]]/page.tsx`)
- MDX component updates (`components/mdx.tsx`)

**Deliverable:**
- Baseline commit hash: `__________`
- Baseline date: `__________`
- Baseline description: `__________`

---

### 2. Diff from Baseline to HEAD

Review all changes with documentation impact, not just `docs/` folder.

**Concrete Actions:**
```bash
# Full diff from baseline
git diff <BASELINE_COMMIT>..HEAD --name-only

# Filter for high-impact file patterns
git diff <BASELINE_COMMIT>..HEAD --name-only | grep -E '\.(tsx?|jsx?|mdx?|json|yaml|yml)$'

# Get detailed diff for key files
git diff <BASELINE_COMMIT>..HEAD -- 'app/**' 'lib/**' 'components/**' 'content/**' 'docs/**'
```

**Impact Areas to Map:**

| Category | File Patterns | Doc Impact |
|----------|---------------|------------|
| **Layout** | `app/layout.tsx`, `app/docs/layout.tsx`, `fumadocs-ui/layouts/*` | Page structure, navigation appearance |
| **Navigation** | `lib/source.ts`, `source.config.ts`, `meta.json`, `_meta.tsx` | Sidebar, breadcrumbs, page tree |
| **MDX Components** | `components/mdx.tsx`, `components/fumadocs/*` | Component availability, props, usage |
| **Source Loading** | `lib/source.ts`, `content/**`, `*.config.ts` | Content discovery, frontmatter handling |
| **OpenAPI** | `app/api/**`, `lib/openapi.ts`, `scripts/openapi-*` | API documentation accuracy |
| **Theme** | `app/globals.css`, `tailwind.config.*`, `theme.config.*` | Visual appearance, color schemes |
| **Search** | `lib/search.ts`, `app/api/search/**` | Search functionality, indexing |
| **Build** | `next.config.*`, `package.json`, `tsconfig.json` | Build process, output structure |
| **Authoring** | `content/**`, `docs/**`, `*.mdx` | Content freshness, examples |

**Deliverable:**
- Changed file impact table (see Output Format below)

---

### 3. Map Impact Areas

Sort changes into categories and assess documentation impact.

**Concrete Actions:**

For each changed file, determine:
1. **Does this affect user-facing documentation?**
   - Public routes added/removed/renamed
   - Component props changed
   - Layout structure modified
   - Navigation reordered

2. **Does this affect authoring workflow?**
   - New MDX components available
   - Frontmatter requirements changed
   - Build requirements updated
   - CLI commands modified

3. **Does this affect build output?**
   - Static export configuration
   - Search indexing behavior
   - OpenAPI generation
   - MDX compilation

**Impact Assessment Matrix:**

| File | Change Type | User Impact | Author Impact | Build Impact | Doc Action Required |
|------|-------------|-------------|---------------|--------------|---------------------|
| | | | | | |

---

### 4. Check Diátaxis-Fumadocs Alignment

**Critical for ongoing maintenance:** Ensure Fumadocs presentation matches Diátaxis content semantics.

**Alignment Drift to Detect:**

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
- Navigation structure drift: [Y/N]

---

### 5. Collect Topic Documentation Inventory

Gather all documentation related to the identified topics.

**Concrete Actions:**

```bash
# Find all docs mentioning specific components
find content docs -name '*.mdx' -o -name '*.md' | xargs grep -l "<ComponentName>"

# Find API documentation
grep -r "api/" content docs --include="*.md*" | head -20

# Find navigation-related docs
grep -r -i "navigation\|sidebar\|breadcrumb" content docs --include="*.md*"

# Find layout/theme docs
grep -r -i "layout\|theme\|color" content docs --include="*.md*" | grep -v node_modules
```

**Documentation Sources to Check:**
- MDX pages in `content/docs/` or `docs/`
- README files in component directories
- Internal notes in `.windsurf/`, `notes/`, `specs/`
- Code comments that are effectively authoritative
- Package documentation (README.md, CONTRIBUTING.md)

**Deliverable:**
- Topic-doc inventory table (see Output Format)

---

### 6. Cross-Check Docs Against Code

Identify renamed props, moved routes, changed examples, broken screenshots, outdated assumptions.

**Concrete Actions:**

**Check Components:**
```typescript
// Compare documented props vs actual component props
// Look for:
// - Props that no longer exist
// - New props not documented
// - Changed default values
// - Removed components
```

**Check Routes:**
```bash
# List all current app routes
find app -name 'page.tsx' -o -name 'page.ts' -o -name 'page.jsx' | sort

# Compare to documented routes
grep -r "Route\|URL\|Endpoint\|/docs/" content docs --include="*.md*" | grep -E '\s/`\?/[a-z-]+`\?' | sort
```

**Check Examples:**
- Are code examples in docs still valid?
- Do MDX imports match actual file paths?
- Are component usage patterns current?

**Check Screenshots:**
- Screenshots reference current UI?
- Alt text accurate?
- Images still render?

---

### 7. Cross-Check Against Fumadocs Patterns

Spot where your docs or implementation fight the framework.

**Fumadocs Pattern Areas to Check:**

| Area | Current Pattern | Fumadocs Recommended | Conflict? |
|------|-----------------|----------------------|-----------|
| **Layouts** | | `DocsLayout`, `HomeLayout` | |
| **Source Loading** | | `loader()`, `defineDocs()` | |
| **Navigation** | | `meta.json`, file-based | |
| **MDX Components** | | `defaultMdxComponents` | |
| **Search** | | Orama/Algolia integration | |
| **i18n** | | `createI18n()` | |
| **Theming** | | CSS variables, Tailwind | |
| **OpenAPI** | | `fumadocs-openapi` | |

**Red Flags:**
- Custom implementations of Fumadocs-provided features
- Bypassing Fumadocs content layer for direct file reading
- Non-standard MDX component patterns
- Manual navigation trees when file-based would work
- Missing `fumadocs-ui` components where applicable

---

### 8. Produce Remediation Pack

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
| Layout customization | `docs/layouts.mdx`, `README.md` | Partial | Needs update |
| MDX components | `docs/components/*.mdx` | Complete | Current |
| API documentation | `docs/api/*.mdx` | Missing | Create |
```

### Stale/Missing/Duplicate List

```markdown
## Stale Documentation
1. `docs/components/accordion.mdx` - Props table outdated (P1)
2. `docs/quickstart.md` - Uses old CLI command (P0)

## Missing Documentation
1. New `Tabs` component usage (P1)
2. `meta.json` advanced configuration (P2)

## Duplicate Documentation
1. `docs/layout.mdx` and `docs/theme.mdx` overlap on customization (P2)
```

### Top 10 Fixes Ranked

```markdown
| Rank | Issue | User Impact | Effort | File |
|------|-------|-------------|--------|------|
| 1 | Quickstart uses deprecated command | High | 5 min | `docs/quickstart.md` |
| 2 | Component props outdated | High | 30 min | `docs/components/*.mdx` |
| 3 | Missing navigation docs | Medium | 2 hrs | `docs/navigation.mdx` |
```

### Diátaxis-Fumadocs Alignment Report

```markdown
## Alignment Status

| Diátaxis Type | Content Count | Presentation | Issues |
|---------------|---------------|--------------|--------|
| **Tutorials** | 5 | Ordered nav, next-links | ✅ Aligned |
| **How-to Guides** | 12 | Task-grouped, searchable | ⚠️ Mixed with tutorials |
| **Reference** | 8 | Dense layout, API tables | ❌ Using blog spacing |
| **Explanation** | 3 | Essay layout | ❌ Heavy sidebar chrome |

## Critical Misalignments

1. **Reference docs use tutorial layout** — Switch to dense `DocsLayout` variant
2. **Tutorials lack explicit ordering** — Add `order` frontmatter + `meta.json`
3. **How-to guides not searchable** — Add search weighting for `/how-to/` prefix
```

---

## Concrete Checklist

- [ ] Baseline commit identified and recorded
- [ ] Diff from baseline..HEAD reviewed
- [ ] All changed files categorized by impact area
- [ ] **Diátaxis-Fumadocs alignment verified** (tutorials/how-to/reference/explanation presentation)
- [ ] Topic documentation inventory complete
- [ ] Code cross-checked against docs (props, routes, examples)
- [ ] Docs cross-checked against Fumadocs patterns
- [ ] Executive summary written
- [ ] Prioritized findings list created
- [ ] Exact files to update identified
- [ ] Draft markdown prepared for top 3 fixes

---

## Safety Rules

1. **Never assume package version = docs current.** Always verify code behavior.
2. **Prefer code as source of truth** when docs and code conflict.
3. **Flag hidden prerequisites explicitly** — undocumented requirements block users.
4. **Test documented commands** before marking as current.
5. **Screenshot everything** — visual drift is hardest to detect from code.
6. **Document your audit trail** — include commit hashes, commands run, evidence captured.

---

## Integration with CI (Optional)

Add periodic audit to `.github/workflows/docs-health.yml`:

```yaml
name: Documentation Health Check
on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full git history
      - name: Find baseline commit
        run: |
          BASELINE=$(git log --all --oneline --grep="docs release" | head -1 | awk '{print $1}')
          echo "baseline=$BASELINE" >> $GITHUB_OUTPUT
      - name: Report changes since baseline
        run: |
          git diff ${{ steps.baseline.outputs.baseline }}..HEAD --name-only | grep -E '\.(mdx?|tsx?|ts)$' || echo "No docs-related changes"
```
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "fumadocs-drift-audit-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
