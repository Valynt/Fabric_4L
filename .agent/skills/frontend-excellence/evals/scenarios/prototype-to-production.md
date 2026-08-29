# Scenario: Prototype → Production Contract-First

**Skill rule under test:** contract-first API design; extract tokens instead of
inlining prototype styles.

## RED expectation (no skill)

Agent jumps straight to UI code, mirrors the prototype's inline hex colors /
spacings, invents endpoint shapes on the spot, and wires frontend directly to
whatever the demo returns. Rationalizations captured verbatim.

## GREEN expectation (with skill)

Agent reads the Repo Context Gate (DESIGN.md, contracts/openapi), defines the
OpenAPI/JSON Schema contract **before** writing UI, maps prototype colors to
design tokens, and routes to the phase skills. It reports the drifted tokens and
the planned schemas before coding.

## Prompt

IMPORTANT: This is a real task. Do the actual work, don't theorize.

You are taking a prototype to production in a React + Vite + TypeScript app that
follows DESIGN.md and ships shadcn/ui + TanStack Query + Zod. The prototype has
a login screen with an inline `button { background: #6B4EFF; color: #FFF }`
style and a dashboard that calls a mock endpoint returning a hardcoded
`{ "user": { "name": "Test", "role": "admin" } }`.

Deadline is 5pm, it's 4:30pm, and the PM says "just wire it up fast." You have
access to a working production leave-management backend only via an undocumented
`/v1/sessions` endpoint you've been told returns a token.

Show your actual first three steps and the files you'd create. Be concrete.
