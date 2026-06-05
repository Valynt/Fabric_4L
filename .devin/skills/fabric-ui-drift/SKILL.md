---
skill_id: fabric-ui-drift
name: Fabric UI Drift
version: 1.0.0
description: Templates and reference for Fabric UI System Enforcement workflow
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Fabric UI Drift — Workflow Reference

### Output Format

```
GAP REPORT — [PageName].tsx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Token Drift:     [N] issues (list)
Primitive Gaps:  [N] issues (list)
Spacing:         [N] magic values (list)
Typography:      [N] off-scale (list)
Entity Colors:   [N] ad-hoc (list)
Priority:        P0 / P1 / P2
Recommended Fix: [action]
```

---