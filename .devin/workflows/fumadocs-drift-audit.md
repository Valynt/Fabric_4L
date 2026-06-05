---
workflow_id: fumadocs-drift-audit
name: Fumadocs Drift Audit
version: 1.0.0
description: Audit Fumadocs documentation drift for ongoing maintenance and migration
pattern: pipeline-dag
risk_level: medium
---

# Fumadocs Documentation Drift Audit

## When to Use

- After every Fumadocs version upgrade
- Before documentation releases
- When UI components, layouts, or navigation change
- During documentation migration or restructuring

## Prerequisites

- Familiarity with current Fumadocs architecture and conventions
- Access to documentation source files (MDX, TSX, config)
- Understanding of Diátaxis framework (tutorials, how-to guides, reference, explanation)
- Baseline commit hash from last documentation release

---

## Step 1: Establish Baseline

```bash
# Identify last docs release commit
BASELINE=$(git log --all --oneline --grep="docs release" | head -1 | awk '{print $1}')
echo "Baseline: $BASELINE"
```

Record: docs version, last release date, baseline commit.

## Step 2: Diff Documentation Source

```bash
# Changed MDX/TSX/TS files since baseline
git diff $BASELINE..HEAD --name-only | grep -E '\.(mdx?|tsx?|ts)$'

# Categorize changes
for file in $(git diff $BASELINE..HEAD --name-only | grep -E '\.(mdx?|tsx?|ts)$'); do
  change_type=$(git diff $BASELINE..HEAD -- $file | grep -E '^\+\+\+|^---' | head -1)
  echo "$file: $change_type"
done
```

## Step 3: Map Impact Assessment

For each changed file, classify:
- **Breaking**: removed component, renamed prop, deleted route
- **Structural**: new layout, nav change, meta.json update
- **Content**: new doc, updated example, rewritten section
- **Cosmetic**: styling, spacing, typo fix

## Step 4: Diátaxis Alignment Check

Ensure Fumadocs presentation matches Diátaxis content semantics:
- Tutorials need ordered nav, "next" links, sequential breadcrumbs
- How-to guides need search prominence, task-focused titles
- Reference needs dense layout, auto-generated tables, tabs
- Explanation needs distinct styling, minimal nav chrome, essay flow

See `.devin/skills/fumadocs/SKILL.md` for the full alignment checklist.

## Step 5: Topic Documentation Inventory

```bash
# List all documentation topics
find content docs -name "*.md*" | sed 's|\.mdx\?||' | sort

# Identify gaps: components without docs, routes without pages
find app -name "*.tsx" | sed 's|\.tsx||' | sort > /tmp/routes.txt
find content docs -name "*.md*" | sed 's|\.mdx\?||' | sort > /tmp/docs.txt
diff /tmp/routes.txt /tmp/docs.txt
```

## Step 6: Cross-Check Docs Against Code

Identify renamed props, moved routes, changed examples, broken screenshots, outdated assumptions.

```bash
# Compare documented routes to actual routes
find app -name 'page.tsx' -o -name 'page.ts' | sort
grep -r "Route\|URL\|Endpoint" content docs --include="*.md*" | grep -E '\s/\`?/[a-z-]+\`?' | sort
```

## Step 7: Cross-Check Against Fumadocs Patterns

Spot where docs or implementation fight the framework. Check layouts, source loading, navigation, MDX components, search, i18n, theming, OpenAPI.

Red flags:
- Custom implementations of Fumadocs-provided features
- Bypassing Fumadocs content layer for direct file reading
- Non-standard MDX component patterns
- Manual navigation trees when file-based would work

## Step 8: Produce Remediation Pack

Deliver structured findings with actionable fixes.
Use the drift-assessment report template in `.devin/skills/fumadocs/SKILL.md`.

---

## Output Format

See `.devin/skills/fumadocs/SKILL.md` for full report templates.

---

## Concrete Checklist

- [ ] Baseline commit identified and recorded
- [ ] Diff from baseline..HEAD reviewed
- [ ] All changed files categorized by impact area
- [ ] Diátaxis-Fumadocs alignment verified
- [ ] Topic documentation inventory complete
- [ ] Code cross-checked against docs
- [ ] Docs cross-checked against Fumadocs patterns
- [ ] Executive summary written
- [ ] Prioritized findings list created
- [ ] Exact files to update identified

---

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
