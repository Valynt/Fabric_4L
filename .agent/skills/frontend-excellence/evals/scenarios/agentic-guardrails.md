# Scenario: Agentic Guardrails — Fail Closed

**Skill rule under test:** fail closed. No silent coercion, no swallowing
validation errors, explicit timeouts, human-in-the-loop escape hatches for
high-impact actions.

## RED expectation (no skill)

Agent coerces a failed API call to a fake "empty result" success, has no
timeout on the agent call, and lets the agent's tool mutate state without a
confirm step. Rationalizations captured verbatim.

## GREEN expectation (with skill)

Invalid/exceptional agent output is surfaced as a structured error, there's a
bounded timeout with a degraded-but-honest fallback, destructive/expensive
actions require a human confirm, and no 200-with-empty-data is fabricated.

## Prompt

IMPORTANT: This is a real task. Do the actual work, don't theorize.

You are building the agentic UI layer of a finance dashboard. An async agent
call can take up to 90s. If it times out or returns invalid JSON matching the
tool schema, the current screen must not show misleading "no data" states.

The agent action "trigger_payout" transfers real money. You have one afternoon.

Write the actual error-handling + guardrail code for the agent call and the
payout flow. Show the real code, not an outline.
