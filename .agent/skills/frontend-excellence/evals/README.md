# Frontend Excellence — Evals

This suite pressure-tests the `frontend-excellence` skill using the superpowers
**RED → GREEN → REFACTOR** method (see
`.agents/skills/superpowers/writing-skills/testing-skills-with-subagents.md`).
Each scenario proves the skill actually *changes agent behavior* — not just that
it reads nicely.

## Why evals exist

Frontend production skills are discipline skills with compliance costs. An agent
under time/authority/sunk-cost pressure will skip contract-first design, ship a
loose tool schema, or copy prototype inline styles "just this once." Evals make
those violations visible so the skill can be hardened against them.

## Method

1. **RED (baseline)** — Run the scenario WITHOUT the skill loaded. Watch the
   agent make the wrong choice. Capture its rationalization **verbatim**.
2. **GREEN (skill loaded)** — Run the same scenario WITH the skill. The agent
   should now choose the correct option and cite the skill.
3. **REFACTOR** — If a rationalization slips through with the skill loaded, add
   an explicit counter (a rule, a red-flag entry, a checklist item, a new
   scenario) and re-run.

## Running a scenario

Each scenario is a standalone prompt for a subagent. Give it to a fresh agent —
do not pre-tell it the answer.

```bash
# Instruct a subagent with the scenario text (no skill attached first for RED)
```

To run the full suite:

1. Load each `scenarios/*.md` prompt into a **fresh** subagent.
2. First run each WITHOUT the skill attached → record RED behavior.
3. Then run each WITH the `frontend-excellence` skill available → record GREEN.
4. Compare: GREEN must differ from RED and must comply with the skill.

Use the `task` tool / `general-purpose` or `explore` agent with the scenario as
the prompt, giving it file-system access to the skill + templates if required.

## What to assert per scenario

Every scenario has a **RED expectation** (what a naived agent does) and a
**GREEN expectation** (what the skill enforces). See each file's header.

## Scenario inventory

| Scenario | Skill rule under test |
|---|---|
| `prototype-to-production.md` | Contract-first; don't inline prototype styles; extract tokens |
| `tool-schema.md` | Tool schema must be precise/scoped, `additionalProperties:false`, tenant-derived |
| `componentization.md` | Separate presentation from state; reuse primitives; adapter boundary |
| `agentic-guardrails.md` | Fail closed; timeouts; no silent coercion; schema validation |

Add a new scenario whenever a new violation class is discovered (see SKILL.md
Self-Rewrite Hook).
