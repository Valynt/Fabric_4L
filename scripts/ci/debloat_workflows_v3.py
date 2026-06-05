#!/usr/bin/env python3
"""De-bloat fabric_ui_drift_agent.md."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".devin" / "workflows"


def rewrite_fabric_ui_drift_agent() -> int:
    src = WORKFLOWS_DIR / "fabric_ui_drift_agent.md"

    new_content = """---
workflow_id: fabric-ui-drift-agent
name: Fabric UI Drift Agent
version: 1.0.0
description: Fabric System Hardening + UI Consistency Deployment with autonomous multi-agent enforcement loop
pattern: manager-worker
risk_level: medium
---

# Fabric UI System Enforcement

Autonomous Multi-Agent Enforcement Loop for achieving zero drift across all UI — token-driven, primitive-based, visually consistent.

**Mode**: Looped autonomous execution. Does not stop at partial completion.

**Loop Termination Condition**:
- ALL pages use Fabric primitives
- AND zero inline styles remain
- AND zero magic values exist
- AND entity colors centralized
- AND build + lint + visual checks pass
- AND audit agent reports zero violations

---

## AGENT 1: DISCOVERY AGENT

**Purpose**: Map current state without judgment.
**Input**: `apps/web/src/`
**Output**: Raw inventory of everything UI-related.

### Tasks

**1.1 Token Audit**
```bash
grep -rn "oklch\|--[a-z-]*:" src/index.css src/globals.css 2>/dev/null > /tmp/token_inventory.txt
```
Document every present token, missing token, and mismatched value.

**1.2 Style Drift Scan**
```bash
grep -rn "style={{" src/pages/ src/components/ 2>/dev/null
grep -rn "\\[\\(px\\|rem\\|em\\|vh\\|vw\\|\\%\\)\\]" src/pages/ src/components/ 2>/dev/null | grep -v "w-full\\|h-full"
grep -rn "bg-gray-\\|bg-slate-\\|bg-blue-\\|bg-green-\\|bg-red-" src/pages/ src/components/ 2>/dev/null | grep -v "entityColors\\|EntityBadge"
grep -rn "shadow-\\[" src/pages/ src/components/ 2>/dev/null
grep -rn "rounded-\\[" src/pages/ src/components/ 2>/dev/null
grep -rn "text-\\[" src/pages/ src/components/ 2>/dev/null
```

**1.3 Primitive Usage Map**
```bash
grep -rn "from.*WfPrimitives\\|PageHeader\\|FabricCard\\|FilterBar\\|StatusBadge\\|MetricCard\\|DataTable\\|SidePanel\\|FabricDialog\\|LoadingSkeleton\\|EntityBadge" src/pages/ src/components/ 2>/dev/null | sort
```

**1.4 Entity Color Pattern Detection**
```bash
grep -rn "violet-100\\|cyan-100\\|amber-100\\|emerald-100" src/pages/ src/components/ 2>/dev/null
```

---

## AGENT 2: ANALYZE AGENT

**Purpose**: Compare discovery output against Fabric spec. Produce gap analysis.

**Analysis Dimensions**:
- Token accuracy (P0 if different)
- Token completeness (P0 if missing)
- Primitive coverage (P1 if ad-hoc)
- Spacing consistency (P1 if magic values)
- Typography (P1 if off-scale)
- Shadow/radius usage (P2 if custom)
- Entity colors (P1 if scattered)
- Import discipline (P1 if deep relative)

See `.devin/skills/fabric-ui-drift/SKILL.md` for the full gap report template.

---

## AGENT 3: FIX AGENT (Refactor)

**Purpose**: Apply smallest correct fix for each gap. Never break functionality.

### Hard Rules
- **No Ad-hoc Styling**: inline styles → className + token; magic values → scale values; non-token colors → semantic tokens; custom shadows/radii → token equivalents
- **Primitives First**: use PageHeader, FabricCard, FilterBar, StatusBadge, MetricCard, DataTable, SidePanel, FabricDialog, LoadingSkeleton, EntityBadge
- **Semantic Colors Protected**: capability→violet, usecase→cyan, persona→amber, valuedriver→emerald (centralized in entityColors map)
- **Bridge, Don't Break**: keep imports working; migrate paths in separate commits
- **Smallest Correct Fix**: one pattern at a time per file; build check after every 3 files

**Fix Sequence Per Page**:
1. Replace page title → `<PageHeader>`
2. Replace card containers → `<FabricCard>`
3. Replace metric displays → `<MetricCard>`
4. Replace status badges → `<StatusBadge>`
5. Replace filter bars → `<FilterBar>`
6. Replace tables → `<DataTable>`
7. Replace entity colors → `<EntityBadge>` or `getEntityColors()`
8. Remove inline styles and magic values
9. Replace loading spinners → `<LoadingSkeleton>`
10. Replace dialogs/panels → `<FabricDialog>` / `<SidePanel>`

---

## AGENT 4: VALIDATE AGENT

**Purpose**: Confirm correctness after fixes.

**Validation Gates** (all must pass):
1. TypeScript: `npx tsc --noEmit` — 0 errors
2. ESLint: `npm run lint` — 0 errors
3. Build: `npm run build` — success, no CSS warnings
4. Visual Structure: no `<div>` page headers, no `bg-[#...]`, no `style={{`, no magic values
5. Primitive Adoption: every page imports at least 1 Fabric primitive
6. Entity Color Centralization: no `bg-violet-100`, `bg-cyan-100`, etc. outside `entity-colors.ts`

**On Failure**: Log error → identify cause → revert or repair → re-run all gates → repeat until pass.

---

## AGENT 5: AUDIT AGENT

**Purpose**: Apply enterprise-grade consistency lens.

**Checks**:
- Architecture consistency — all pages use same primitive set
- Import discipline — barrel imports from `@/components/ui/fabric/`
- No duplicate styling systems — only Fabric tokens
- UI contract integrity — props interfaces consistent
- Data flow correctness — no styling logic in data hooks
- Accessibility — focus states visible, semantic HTML preserved
- Dark mode — all colors have dark variants
- Performance — no unnecessary re-renders from style changes

If audit FAILs → loop back to FIX AGENT.

---

## AGENT 6: REPORT AGENT

**Purpose**: Produce final deployment report.

**Trigger**: When loop terminates (all gates pass, audit passes).
**Output**: `apps/web/FABRIC_DEPLOYMENT_REPORT.md`

See `.devin/skills/fabric-ui-drift/SKILL.md` for the full report template.

---

## BEGIN EXECUTION

Paste the **Workflow Trigger Prompt** into Windsurf and execute.
Monitor iteration count. Expected: 2-4 complete loops for initial deployment.

## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "fabric-ui-drift-agent-001",
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
"""

    src.write_text(new_content, encoding="utf-8")
    new_len = len(new_content.splitlines())
    print(f"fabric_ui_drift_agent.md: {new_len} lines")
    return new_len


def main() -> int:
    rewrite_fabric_ui_drift_agent()
    return 0


if __name__ == "__main__":
    sys.exit(main())
