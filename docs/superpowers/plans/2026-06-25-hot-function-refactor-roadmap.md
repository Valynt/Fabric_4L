# Hot-Function Refactor Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce complexity, churn, and defect risk in the 15 reported hot functions by decomposing them into smaller, tested units while preserving all public contracts.

**Architecture:** Refactor from the outside-in: first extract pure helper modules and add unit tests, then thin the hooks/components to orchestration-only shells. Backend hotspots follow the same pattern — extract validation/parsing logic, add tests, then simplify the call site.

**Tech Stack:** React 19 + TypeScript + Vitest (frontend); Python + pytest (backend/scripts).

---

## Phase 1 — Critical Frontend Hooks (highest user-facing blast radius)

### Task 1: Extract `useAgentEvents` event reducer into a pure module

**Files:**
- Create: `apps/web/src/agui/agentEventReducer.ts`
- Modify: `apps/web/src/agui/useAgentEvents.ts:337-453`
- Test: `apps/web/src/agui/agentEventReducer.test.ts`

**Why:** `useAgentEvents` is 551 lines and its `processEvent` callback has 12+ branches. A pure reducer is testable without React and removes the huge dependency array that currently drives `sendMessage`.

- [ ] **Step 1: Write the reducer test first**

```typescript
// apps/web/src/agui/agentEventReducer.test.ts
import { describe, it, expect } from 'vitest';
import { reduceAgentEvent, createInitialAgentState } from './agentEventReducer';
import { AgentEventType } from './events';

describe('reduceAgentEvent', () => {
  it('handles RUN_STARTED', () => {
    const state = createInitialAgentState();
    const next = reduceAgentEvent(state, {
      type: AgentEventType.RUN_STARTED,
      runId: 'run-1',
      expectedSteps: [{ id: 's1', label: 'Step 1' }],
    });
    expect(next.runState).toBe('running');
    expect(next.currentRunId).toBe('run-1');
    expect(next.steps).toHaveLength(1);
  });

  it('appends text message deltas to the same message', () => {
    const state = createInitialAgentState();
    const withPlaceholder = reduceAgentEvent(state, {
      type: AgentEventType.TEXT_MESSAGE_START,
      messageId: 'm1',
      timestamp: new Date().toISOString(),
    });
    const withContent = reduceAgentEvent(withPlaceholder, {
      type: AgentEventType.TEXT_MESSAGE_CONTENT,
      messageId: 'm1',
      delta: 'hello',
      timestamp: new Date().toISOString(),
    });
    expect(withContent.messages).toHaveLength(1);
    expect(withContent.messages[0].content).toBe('hello');
  });
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `pnpm --dir apps/web exec vitest run src/agui/agentEventReducer.test.ts`
Expected: FAIL — `agentEventReducer` module not found.

- [ ] **Step 3: Create the reducer module**

Move the following functions and the switch statement out of `useAgentEvents.ts` into `apps/web/src/agui/agentEventReducer.ts`:

```typescript
export interface AgentState {
  messages: AgentMessage[];
  steps: StepSnapshot[];
  runState: RunState;
  currentRunId: string | null;
  lastError: string | null;
  metadata: RunMetadata | null;
}

export function createInitialAgentState(): AgentState { ... }
export function reduceAgentEvent(state: AgentState, event: AgentEvent): AgentState { ... }
```

Keep the existing helper functions (`initializeExpectedSteps`, `updateStep`, `appendOrUpdateAgentMessage`, etc.) as private helpers inside the new module.

- [ ] **Step 4: Wire `useAgentEvents` to the reducer**

Replace the `processEvent` useCallback and state setter calls with:

```typescript
const processEvent = useCallback((event: AgentEvent) => {
  setStateRef.current((prev) => reduceAgentEvent(prev, event));
}, []);
```

`useAgentEvents` now only manages state refs, the abort controller, `sendMessage`, and derived values (`suggestedActions`, `missingActionContextMessage`).

- [ ] **Step 5: Run focused tests + typecheck**

Run:
```bash
pnpm --dir apps/web exec vitest run src/agui/agentEventReducer.test.ts
pnpm --dir apps/web run check
```
Expected: PASS + no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/agui/agentEventReducer.ts apps/web/src/agui/agentEventReducer.test.ts apps/web/src/agui/useAgentEvents.ts
git commit -m "refactor(agui): extract pure agent event reducer from useAgentEvents"
```

---

### Task 2: Extract message/context builders from `useAgentEvents`

**Files:**
- Create: `apps/web/src/agui/agentConversationContext.ts`
- Modify: `apps/web/src/agui/useAgentEvents.ts:472-484`
- Test: `apps/web/src/agui/agentConversationContext.test.ts`

**Why:** `sendMessage` builds the system prompt and conversation context inline, making the dependency array huge and the function hard to unit test.

- [ ] **Step 1: Write the builder test**

```typescript
// apps/web/src/agui/agentConversationContext.test.ts
import { describe, it, expect } from 'vitest';
import { buildConversationContext } from './agentConversationContext';

describe('buildConversationContext', () => {
  it('uses the active tab system prompt', () => {
    const result = buildConversationContext({
      activeTab: 'signals',
      accountName: 'Acme',
      userInput: 'Summarize',
      recentMessages: [],
    });
    expect(result[0].role).toBe('system');
    expect(result[0].content).toContain('signals');
  });

  it('includes the last 10 messages', () => {
    const recentMessages = Array.from({ length: 15 }, (_, i) => ({
      id: `m${i}`,
      role: 'agent' as const,
      content: `msg-${i}`,
      timestamp: '12:00',
    }));
    const result = buildConversationContext({
      activeTab: 'drivers',
      accountName: 'Acme',
      userInput: 'go',
      recentMessages,
    });
    expect(result).toHaveLength(12); // system + 10 recent + user
    expect(result[1].content).toBe('msg-5');
  });
});
```

- [ ] **Step 2: Create the builder module**

```typescript
// apps/web/src/agui/agentConversationContext.ts
import { TAB_SYSTEM_PROMPTS } from './systemPrompts';
import type { AgentMessage } from '@/components/workspace/RightRail';

export interface ConversationMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export function buildConversationContext(args: {
  activeTab: string;
  accountName: string;
  userInput: string;
  recentMessages: AgentMessage[];
}): ConversationMessage[] {
  const systemPrompt =
    TAB_SYSTEM_PROMPTS[args.activeTab] ??
    'You are ValuePilot, an AI co-pilot for value selling. Keep responses concise.';

  return [
    { role: 'system', content: systemPrompt },
    ...args.recentMessages.slice(-10).map((m) => ({
      role: (m.role === 'agent' ? 'assistant' : 'user') as 'system' | 'user' | 'assistant',
      content: m.content,
    })),
    { role: 'user', content: args.userInput },
  ];
}
```

Move `TAB_SYSTEM_PROMPTS` into `apps/web/src/agui/systemPrompts.ts` so both `useAgentEvents.tsx` and the builder can import it.

- [ ] **Step 3: Replace inline context construction in `sendMessage`**

```typescript
const conversationMessages = buildConversationContext({
  activeTab,
  accountName,
  userInput,
  recentMessages: messages,
});
```

- [ ] **Step 4: Run tests + typecheck**

```bash
pnpm --dir apps/web exec vitest run src/agui/agentConversationContext.test.ts
pnpm --dir apps/web run check
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/agui/agentConversationContext.ts apps/web/src/agui/agentConversationContext.test.ts apps/web/src/agui/systemPrompts.ts apps/web/src/agui/useAgentEvents.ts
git commit -m "refactor(agui): extract conversation context builder from useAgentEvents"
```

---

### Task 3: Simplify `useJobStream` by extracting SSE lifecycle helpers

**Files:**
- Create: `apps/web/src/hooks/useJobStream.utils.ts`
- Modify: `apps/web/src/hooks/useJobStream.ts:192-565`
- Test: `apps/web/src/hooks/useJobStream.utils.test.ts`

**Why:** `useJobStream` is 566 lines. The pure event parsing/application logic can live outside the hook and be unit tested without browser APIs.

- [ ] **Step 1: Write tests for event parsing/application**

```typescript
// apps/web/src/hooks/useJobStream.utils.test.ts
import { describe, it, expect } from 'vitest';
import { applyJobStreamEvent, parseJobStreamEventJson, mapJobStatus } from './useJobStream.utils';

describe('applyJobStreamEvent', () => {
  const base = { progress: 0, status: 'created' as const, logs: [], entities: [] };

  it('updates progress', () => {
    const next = applyJobStreamEvent(base, { type: 'progress', data: 42 });
    expect(next.progress).toBe(42);
  });

  it('ignores unknown status strings', () => {
    const next = applyJobStreamEvent(base, { type: 'status', data: 'UNKNOWN' });
    expect(next.status).toBe('created');
  });
});
```

- [ ] **Step 2: Extract pure helpers into `useJobStream.utils.ts`**

Move out:
- `parseJobStreamEvent`
- `parseJobStreamEventJson`
- `parseLogEntry`
- `parseEntityEntry`
- `applyJobStreamEvent`
- `mapJobStatus`
- the Zod schemas (`JobStreamEventSchema`, etc.)

Keep only React/effect/SSE-specific code in `useJobStream.ts`.

- [ ] **Step 3: Update `useJobStream.ts` imports**

```typescript
import {
  parseJobStreamEventJson,
  applyJobStreamEvent,
  mapJobStatus,
} from './useJobStream.utils';
```

- [ ] **Step 4: Run tests + typecheck**

```bash
pnpm --dir apps/web exec vitest run src/hooks/useJobStream.utils.test.ts
pnpm --dir apps/web run check
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useJobStream.utils.ts apps/web/src/hooks/useJobStream.utils.test.ts apps/web/src/hooks/useJobStream.ts
git commit -m "refactor(hooks): extract pure job-stream helpers"
```

---

## Phase 2 — Medium Frontend Hotspots

### Task 4: Extract C1 stream parsing from `thesysClient.ts`

**Files:**
- Modify: `apps/web/src/api/thesysClient.ts`
- Create: `apps/web/src/api/c1SseParser.ts`
- Test: `apps/web/src/api/c1SseParser.test.ts`

**Why:** `streamC1Response` mixes fetch I/O, stream reading, and SSE parsing. Extracting the parser makes the generator shorter and testable.

- [ ] **Step 1: Move `parseSseDataLine` and `parseFinalBufferedSseChunk` to `c1SseParser.ts`.**
- [ ] **Step 2: Add tests for valid/invalid SSE lines.**
- [ ] **Step 3: Update `thesysClient.ts` to import from `c1SseParser.ts`.**
- [ ] **Step 4: Run `pnpm --dir apps/web exec vitest run src/api/c1SseParser.test.ts && pnpm --dir apps/web run check`.**

---

### Task 5: Extract `useC1Stream` component-update logic

**Files:**
- Create: `apps/web/src/hooks/useC1Stream.utils.ts`
- Modify: `apps/web/src/hooks/useC1Stream.ts:166-199`
- Test: `apps/web/src/hooks/useC1Stream.utils.test.ts`

**Why:** `handleSliderChange` contains label-based card matching that is pure and can be tested without React.

- [ ] **Step 1: Extract `applyWhatIfResult(components, result)` helper.**
- [ ] **Step 2: Test ROI, payback, and value card updates.**
- [ ] **Step 3: Replace the inline `.map()` in `handleSliderChange` with the helper.**

---

### Task 6: Simplify `userTierStore.ts` route matching

**Files:**
- Modify: `apps/web/src/stores/userTierStore.ts`
- Test: `apps/web/src/stores/userTierStore.test.ts` (or extend if it exists)

**Why:** `ROUTE_TIER_MAP` is 170+ lines of hardcoded routes and `getRouteTier` has duplicated prefix scans.

- [ ] **Step 1: Group routes by tier and build the map programmatically.**
- [ ] **Step 2: Extract `matchRouteTier(normalizedPath)` helper.**
- [ ] **Step 3: Add tests for exact, tenant-scoped, and unknown routes.**

---

### Task 7: Split `GraphExplorer.tsx` into container + presentational components

**Files:**
- Create: `apps/web/src/features/graph/components/GraphExplorerLayout.tsx`
- Create: `apps/web/src/features/graph/components/GraphExplorerControls.tsx`
- Modify: `apps/web/src/pages/GraphExplorer.tsx`

**Why:** The page currently mixes data loading, search handling, and JSX layout.

- [ ] **Step 1: Move control panel JSX to `GraphExplorerControls.tsx`.**
- [ ] **Step 2: Move layout shell (3-panel grid) to `GraphExplorerLayout.tsx`.**
- [ ] **Step 3: Keep only hook orchestration in `GraphExplorer.tsx`.**

---

## Phase 3 — Backend / Script Hotspots

### Task 8: Simplify `tenant_routes` in `scripts/ci/check_layer5_tenant_isolation_matrix.py`

**Files:**
- Modify: `scripts/ci/check_layer5_tenant_isolation_matrix.py`
- Test: add or extend tests under `tests/ci/`

**Why:** Complex conditional flagged as high risk.

- [ ] **Step 1: Read the function and identify the conditional branches.**
- [ ] **Step 2: Extract predicate helpers (e.g., `is_tenant_route(...)`, `is_public_route(...)`).**
- [ ] **Step 3: Replace nested conditionals with early returns using helpers.**
- [ ] **Step 4: Add unit tests for each predicate.**

---

### Task 9: Refactor `_find_vector_candidates` in `services/layer3-knowledge/src/services/entity_resolution.py`

**Files:**
- Modify: `services/layer3-knowledge/src/services/entity_resolution.py`
- Test: extend `services/layer3-knowledge/tests/`

**Why:** Critical complex conditional in entity resolution.

- [ ] **Step 1: Identify the candidate-filtering branches.**
- [ ] **Step 2: Extract small pure helpers (`_candidate_score`, `_is_vector_match`, etc.).**
- [ ] **Step 3: Write tests for each helper with mocked vector/embeddings.**
- [ ] **Step 4: Replace the monolithic conditional with composed helper calls.**

---

### Task 10: Refactor `resolve_oidc_config` and `_get_tenant_tier_from_db`

**Files:**
- Modify: `packages/shared/src/value_fabric/shared/identity/providers.py`
- Modify: `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py`
- Test: extend existing shared package tests

**Why:** Both are flagged as high-complexity functions.

- [ ] **Step 1: Split `resolve_oidc_config` into parsing, validation, and HTTP steps.**
- [ ] **Step 2: Split `_get_tenant_tier_from_db` into query builder and result mapper.**
- [ ] **Step 3: Add tests for each extracted helper.**

---

## Validation gates for every phase

After each commit, run the focused gate for the area touched:

```bash
# Frontend hooks/components
pnpm --dir apps/web run check
pnpm --dir apps/web exec vitest run <path-to-new-test>
pnpm --dir apps/web run test:frontend-hygiene

# Backend / scripts
pytest <path-to-new-or-updated-test> -q
python -m ruff check <modified-files>
python -m black --check <modified-files>

# Cross-cutting contract package
pnpm --dir packages/platform-contract run contract:test
```

Stop and fix any failure before moving to the next task.

## Completion criteria

- [ ] `useAgentEvents` reducer and context builder are extracted and covered by unit tests.
- [ ] `useJobStream` pure helpers are extracted and covered by unit tests.
- [ ] `thesysClient.ts` SSE parser is extracted and tested.
- [ ] `useC1Stream` slider-update logic is extracted and tested.
- [ ] `userTierStore.ts` route lookup is simplified and tested.
- [ ] `GraphExplorer.tsx` is split into container + presentational components.
- [ ] `tenant_routes`, `_find_vector_candidates`, `resolve_oidc_config`, and `_get_tenant_tier_from_db` are decomposed and tested.
- [ ] All modified areas pass `pnpm --dir apps/web run check`, `pytest`, `ruff`, `black`, and the platform-contract test suite.
