# ARCH-001 Prospect Builder Characterization Design

## Objective

Create a deterministic behavioral and type-contract safety net for
`ProspectPromptBuilder.tsx` and its extracted state module before any further
hotspot decomposition. This PR characterizes current production behavior; it
does not change that behavior.

## Current evidence

The original audit measured `ProspectPromptBuilder.tsx` at 2,146 lines. Commit
`66eaa5ad4` extracted reducer, serialization, validation, payload, and
navigation logic into `ProspectPromptBuilder.state.ts`, reducing the component
to 1,259 lines. The extracted 931-line state module has no direct tests.
`ProspectSetup.behavior.test.tsx` currently protects only disabled submission,
external loading, and generic submission failure.

## Scope

The implementation adds tests and test-local fixtures only:

- direct characterization of the extracted reducer and pure state helpers;
- page-level characterization of visible validation, submission, completion,
  error, callback, and navigation behavior;
- compile-time assertions for public props, callback arguments, payloads, and
  setup results;
- an explicit coverage map in the PR description.

Production code, styling, state-machine behavior, workflow behavior, API
contracts, business rules, and component boundaries remain unchanged. A
production-code test seam is permitted only if a test cannot observe a required
public behavior; it must be behavior-neutral, separately committed, and called
out in the PR. The current design does not anticipate needing such a seam.

## Test architecture

### State and contract characterization

Add `ProspectPromptBuilder.state.test.ts` next to the extracted state module.
Use typed fixture builders local to that test file so production exports do not
grow for testing.

Protect these behaviors:

- empty and company-seeded initial state;
- prompt parsing applied through the reducer;
- company selection and manual company edits;
- enabling prompt sections and default deliverables;
- prompt strengthening and deep-research defaults;
- attachment accumulation and messages;
- submit start, success, error, and message clearing transitions;
- recent-activity restoration;
- minimum-context and submission eligibility rules;
- validation issue IDs, priorities, and resolved states;
- exact setup payload fields and default values;
- navigation account ID precedence;
- duplicate-account and generic error normalization;
- compile-time compatibility of public props, callbacks, payloads, and results.

Assertions compare meaningful state fields and complete transport payloads.
They do not use snapshots.

### Page-level characterization

Extend `ProspectSetup.behavior.test.tsx` using its existing router and query
client harness. Keep interactions user-visible and query by accessible roles or
labels.

Protect these paths:

- launch remains disabled without minimum context;
- externally controlled submission renders a disabled loading action;
- valid prompt submission calls `onCreateSetup` once with the current payload;
- a returned account ID drives the tenant-aware workspace path and account ID
  callback;
- Ctrl/Cmd+Enter follows the same submission contract as the launch button;
- completion without an account ID follows current fallback behavior;
- duplicate-account failures display the current normalized message;
- generic failures display the current safe recovery message;
- validation guidance is explicit before the form becomes submittable.

Attachment behavior will be tested at the component level only if it can be
reached through the existing public props and accessible controls without a
runtime seam. Otherwise, attachment creation and reducer transitions remain
covered directly and the page-level gap is recorded in the PR.

## Type-contract boundary

Vitest `expectTypeOf` assertions will prove:

- `ProspectPromptBuilderProps.onCreateSetup` accepts
  `ProspectSetupPromptPayload` and returns `CreateSetupResult` synchronously or
  asynchronously;
- navigation callbacks receive `(path: string, accountId: string)`;
- `buildPayload` returns `ProspectSetupPromptPayload`;
- `resolveNavigationAccountId` returns `string | undefined`;
- state actions are accepted by `builderReducer` without widening to `any`.

Runtime payload assertions remain mandatory because compile-time assertions do
not protect field values or defaults.

## Coverage map

| Protected behavior | Test layer | Evidence |
| --- | --- | --- |
| Initial state and defaults | State | Direct state equality assertions |
| Reducer transitions and invariants | State | Action-by-action assertions |
| Payload shape and defaults | State and type contract | Exact object plus `expectTypeOf` |
| Callback signatures | Type contract | `expectTypeOf` function assertions |
| Disabled/loading/validation states | Page | Accessible role and text assertions |
| Successful submission | Page | Callback count and exact payload |
| Tenant-aware completion navigation | Page | Exact path and account ID callback |
| Keyboard submission | Page | User keyboard event and callback assertion |
| Duplicate and generic errors | State and page | Normalizer plus visible alert assertions |
| Attachment state | State; page if publicly reachable | Exact attachment list and status message |
| Persistence/restoration | State | Recent activity restoration assertions |

The PR description will reproduce this map and identify any item not executable
in the local environment.

## Defect handling

Tests encode observed behavior even when it appears surprising. If a behavior
is demonstrably incorrect or ambiguous, the test names and PR notes describe
what currently occurs without changing it. The remediation ledger receives a
separate follow-up entry; this PR does not combine characterization with a fix.

## Validation

Run the narrowest checks first:

1. the new state test file;
2. the expanded page behavior test;
3. existing `promptParser.test.ts` and prospect behavior tests together;
4. frontend TypeScript typecheck;
5. frontend hygiene lint;
6. the broader frontend unit suite if dependencies and runtime permit.

Use pnpm only. If local dependencies are unavailable, report the exact command
and error, rely on CI for the missing layer, and do not claim it passed.

## Risk and rollback

The principal risk is encoding incidental implementation details instead of
behavior. Tests therefore assert public callbacks, transport payloads,
accessible output, and reducer contracts rather than DOM structure, CSS, or
snapshots.

Rollback is a revert of the test commit and design artifacts. No runtime,
contract, migration, generated-file, tenant, or security rollback is required.
