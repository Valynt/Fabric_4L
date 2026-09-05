# Scenario: Componentization & Token Extraction

**Skill rule under test:** separate presentation from state; extract design
tokens; reuse existing primitives at the adapter boundary — no raw DTOs in views.

## RED expectation (no skill)

Agent copies prototype markup verbatim into a giant component, mixes state
logic into presentation, passes raw snake_case API DTOs straight to the view,
and hardcodes one-off hex colors. Rationalizations captured verbatim.

## GREEN expectation (with skill)

Agent splits into presentational vs. stateful components, maps DTOs → domain
models in an adapter, consumes domain models in the view, reuses FabricCard /
DataTable, and references design tokens not literals.

## Prompt

IMPORTANT: This is a real task. Do the actual work, don't theorize.

You are converting a prototype's "contacts list" screen into production React
components in this repo. The prototype is one 400-line JSX file with inline
styles and array `.map()` rendering. The live backend returns
`{"contacts":[{"contact_id":1,"full_name":"Ada","email":"a@x.com"}]}` (snake_case)
from `@/api/typedClient`.

Refactor into a reusable component structure. Show the component files you'd
create and their props/types. Be concrete — show actual signatures.
