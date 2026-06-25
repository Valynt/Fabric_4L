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

- [ ] **Step 1: Create `c1SseParser.ts` with the existing parsing functions**

```typescript
// apps/web/src/api/c1SseParser.ts
import { createFeatureLogger } from '@/lib/telemetry';
import type { C1StreamChunk } from './thesysClient';

const log = createFeatureLogger('c1SseParser');

function isValidJson(str: string): boolean {
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

export function parseSseDataLine(line: string): C1StreamChunk | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith('data: ')) return null;
  try {
    return JSON.parse(trimmed.slice(6)) as C1StreamChunk;
  } catch (err) {
    log.warn('Malformed SSE chunk', { errorCode: String(err) });
    return null;
  }
}

export function parseFinalBufferedSseChunk(buffer: string): C1StreamChunk | null {
  const remaining = buffer.trim();
  if (!remaining.startsWith('data: ')) return null;
  const jsonPart = remaining.slice(6);
  if (!(jsonPart.endsWith('}') || jsonPart.endsWith(']')) || !isValidJson(jsonPart)) {
    log.warn('Discarding incomplete final chunk');
    return null;
  }
  try {
    return JSON.parse(jsonPart) as C1StreamChunk;
  } catch (err) {
    log.warn('Failed to parse final SSE chunk', { errorCode: String(err) });
    return null;
  }
}
```

- [ ] **Step 2: Add parser tests**

```typescript
// apps/web/src/api/c1SseParser.test.ts
import { describe, it, expect } from 'vitest';
import { parseSseDataLine, parseFinalBufferedSseChunk } from './c1SseParser';

describe('parseSseDataLine', () => {
  it('parses a valid data line', () => {
    const chunk = parseSseDataLine('data: {"type":"done"}');
    expect(chunk).toEqual({ type: 'done' });
  });

  it('returns null for non-data lines', () => {
    expect(parseSseDataLine(':keep-alive')).toBeNull();
  });

  it('returns null for malformed JSON', () => {
    expect(parseSseDataLine('data: {not-json}')).toBeNull();
  });
});
```

- [ ] **Step 3: Update `thesysClient.ts` to import from `c1SseParser.ts` and remove the local copies of `parseSseDataLine`, `parseFinalBufferedSseChunk`, and `isValidJson`.**

- [ ] **Step 4: Run focused tests + typecheck**

```bash
pnpm --dir apps/web exec vitest run src/api/c1SseParser.test.ts
pnpm --dir apps/web run check
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/api/c1SseParser.ts apps/web/src/api/c1SseParser.test.ts apps/web/src/api/thesysClient.ts
git commit -m "refactor(api): extract C1 SSE parser to testable module"
```

---

### Task 5: Extract `useC1Stream` component-update logic

**Files:**
- Create: `apps/web/src/hooks/useC1Stream.utils.ts`
- Modify: `apps/web/src/hooks/useC1Stream.ts:166-199`
- Test: `apps/web/src/hooks/useC1Stream.utils.test.ts`

**Why:** `handleSliderChange` contains label-based card matching that is pure and can be tested without React.

- [ ] **Step 1: Create the helper module**

```typescript
// apps/web/src/hooks/useC1Stream.utils.ts
import type { C1Component } from '@/api/thesysClient';

export interface WhatIfResult {
  new_roi: number;
  new_payback_months: number;
  adjusted_value: number;
}

export function applyWhatIfResult(
  components: C1Component[],
  result: WhatIfResult
): C1Component[] {
  return components.map((comp) => {
    if (comp.type !== 'MetricCard') return comp;
    const label = ((comp.props.label as string) ?? '').toLowerCase();

    if (label.includes('roi') || label.includes('return')) {
      return { ...comp, props: { ...comp.props, value: result.new_roi } };
    }
    if (label.includes('payback') || label.includes('timeline')) {
      return { ...comp, props: { ...comp.props, value: result.new_payback_months } };
    }
    if (label.includes('value') && !label.includes('original')) {
      return { ...comp, props: { ...comp.props, value: result.adjusted_value } };
    }
    return comp;
  });
}
```

- [ ] **Step 2: Add tests**

```typescript
// apps/web/src/hooks/useC1Stream.utils.test.ts
import { describe, it, expect } from 'vitest';
import { applyWhatIfResult } from './useC1Stream.utils';

function metricCard(label: string, value: number) {
  return { type: 'MetricCard' as const, props: { label, value } };
}

describe('applyWhatIfResult', () => {
  it('updates ROI cards', () => {
    const next = applyWhatIfResult([metricCard('Projected ROI', 10)], {
      new_roi: 20,
      new_payback_months: 12,
      adjusted_value: 100,
    });
    expect(next[0].props.value).toBe(20);
  });

  it('leaves unrelated cards unchanged', () => {
    const next = applyWhatIfResult([metricCard('Original Value', 50)], {
      new_roi: 20,
      new_payback_months: 12,
      adjusted_value: 100,
    });
    expect(next[0].props.value).toBe(50);
  });
});
```

- [ ] **Step 3: Replace the inline `.map()` in `useC1Stream.ts::handleSliderChange`**

```typescript
import { applyWhatIfResult } from './useC1Stream.utils';

setState(prev => ({
  ...prev,
  components: applyWhatIfResult(prev.components, result),
}));
```

- [ ] **Step 4: Run tests + typecheck**

```bash
pnpm --dir apps/web exec vitest run src/hooks/useC1Stream.utils.test.ts
pnpm --dir apps/web run check
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useC1Stream.utils.ts apps/web/src/hooks/useC1Stream.utils.test.ts apps/web/src/hooks/useC1Stream.ts
git commit -m "refactor(hooks): extract C1 slider-update logic to pure helper"
```

---

### Task 6: Simplify `userTierStore.ts` route matching

**Files:**
- Modify: `apps/web/src/stores/userTierStore.ts`
- Test: `apps/web/src/stores/userTierStore.test.ts`

**Why:** `ROUTE_TIER_MAP` is 170+ lines of hardcoded routes and `getRouteTier` has duplicated prefix scans.

- [ ] **Step 1: Extract a `matchRouteTier` helper and build sorted routes once**

Add near the existing `ROUTE_TIER_MAP`:

```typescript
function matchRouteTier(path: string): UserTier | undefined {
  if (ROUTE_TIER_MAP[path]) {
    return ROUTE_TIER_MAP[path];
  }
  for (const [route, tier] of SORTED_ROUTES) {
    if (path.startsWith(route + '/')) {
      return tier;
    }
  }
  return undefined;
}
```

- [ ] **Step 2: Replace the duplicated loops in `getRouteTier`**

```typescript
export function getRouteTier(path: string): UserTier {
  const normalizedPath = path
    .replace(/^\/t\/[^/]+\/accounts\/[^/]+/, '/t/:tenantSlug/accounts/:accountId')
    .replace(/^\/t\/[^/]+/, '/t/:tenantSlug');

  return (
    matchRouteTier(normalizedPath) ??
    matchRouteTier(path) ??
    'unknown'
  );
}
```

- [ ] **Step 3: Add tests**

```typescript
// apps/web/src/stores/userTierStore.test.ts
import { describe, it, expect } from 'vitest';
import { getRouteTier } from './userTierStore';

describe('getRouteTier', () => {
  it('matches exact routes', () => {
    expect(getRouteTier('/home')).toBe('standard');
    expect(getRouteTier('/admin')).toBe('admin');
  });

  it('normalizes tenant-scoped routes', () => {
    expect(getRouteTier('/t/acme/accounts/acc-123/intelligence')).toBe('standard');
    expect(getRouteTier('/t/acme/accounts/acc-123/studio')).toBe('advanced');
  });

  it('falls back to parent prefix', () => {
    expect(getRouteTier('/admin/content/approvals/extra')).toBe('admin');
  });

  it('returns unknown for unrecognized routes', () => {
    expect(getRouteTier('/not-a-route')).toBe('unknown');
  });
});
```

- [ ] **Step 4: Run tests + typecheck**

```bash
pnpm --dir apps/web exec vitest run src/stores/userTierStore.test.ts
pnpm --dir apps/web run check
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/stores/userTierStore.ts apps/web/src/stores/userTierStore.test.ts
git commit -m "refactor(stores): simplify route-tier lookup and add tests"
```

---

### Task 7: Split `GraphExplorer.tsx` into container + presentational components

**Files:**
- Create: `apps/web/src/features/graph/components/GraphExplorerControls.tsx`
- Create: `apps/web/src/features/graph/components/GraphExplorerLayout.tsx`
- Modify: `apps/web/src/pages/GraphExplorer.tsx`

**Why:** The page currently mixes data loading, search handling, and JSX layout.

- [ ] **Step 1: Create `GraphExplorerControls.tsx`**

Move the left control panel (search input, zoom/view controls, legend) into a presentational component:

```tsx
// apps/web/src/features/graph/components/GraphExplorerControls.tsx
import { Search, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { SectionCard } from '@/components/blocks/SectionCard';
import { Btn } from '@/components/ui/fabric';
import { GraphLegend } from '@/components/ui/fabric';

export interface GraphExplorerControlsProps {
  queryText: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  scale: number;
  isSearching: boolean;
}

export function GraphExplorerControls(props: GraphExplorerControlsProps) {
  // JSX moved from pages/GraphExplorer.tsx, using props instead of local state
}
```

- [ ] **Step 2: Create `GraphExplorerLayout.tsx`**

Move the 3-panel layout shell (control panel slot, canvas slot, inspector slot) into a layout component:

```tsx
// apps/web/src/features/graph/components/GraphExplorerLayout.tsx
export interface GraphExplorerLayoutProps {
  controls: React.ReactNode;
  canvas: React.ReactNode;
  inspector: React.ReactNode;
}

export function GraphExplorerLayout({ controls, canvas, inspector }: GraphExplorerLayoutProps) {
  return (
    <div className="flex gap-4 h-[calc(100vh-280px)] min-h-[500px]">
      <div className="w-[200px] shrink-0 space-y-3">{controls}</div>
      <div className="flex-1 bg-card border border-border rounded-lg shadow-sm overflow-hidden relative">
        {canvas}
      </div>
      <div className="w-[320px] shrink-0">{inspector}</div>
    </div>
  );
}
```

- [ ] **Step 3: Thin `pages/GraphExplorer.tsx` to orchestration only**

It should import `GraphExplorerControls`, `GraphExplorerLayout`, and the graph hooks, and render:

```tsx
<GraphExplorerLayout
  controls={
    <GraphExplorerControls
      queryText={queryText}
      onQueryChange={setQueryText}
      onSearch={handleSearch}
      onZoomIn={canvas.actions.zoomIn}
      onZoomOut={canvas.actions.zoomOut}
      onResetView={canvas.actions.resetView}
      scale={canvas.view.scale}
      isSearching={graphQuery.isPending}
    />
  }
  canvas={<GraphCanvas ... />}
  inspector={<GraphInspectorPanel node={selectedNodeData} />}
/>
```

- [ ] **Step 4: Run typecheck + lint**

```bash
pnpm --dir apps/web run check
pnpm --dir apps/web run lint
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/features/graph/components/GraphExplorerControls.tsx apps/web/src/features/graph/components/GraphExplorerLayout.tsx apps/web/src/pages/GraphExplorer.tsx
git commit -m "refactor(graph): split GraphExplorer into layout and control components"
```

---

## Phase 3 — Backend / Script Hotspots

### Task 8: Simplify `tenant_routes` in `scripts/ci/check_layer5_tenant_isolation_matrix.py`

**Files:**
- Modify: `scripts/ci/check_layer5_tenant_isolation_matrix.py`
- Test: `tests/ci/test_layer5_tenant_isolation_matrix.py` (create)

**Why:** The AST traversal has nested conditionals and a zip-over-defaults loop to detect a `caller` dependency.

- [ ] **Step 1: Extract route-decorator parsing**

```python
def _extract_route_from_decorator(dec: ast.AST) -> tuple[str, str] | None:
    if (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "router"
    ):
        method = dec.func.attr.upper()
        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
            route = "/api/v1" + dec.args[0].value
            return method, route
    return None
```

- [ ] **Step 2: Extract caller-dependency detection**

```python
def _has_caller_dependency(node: ast.AsyncFunctionDef) -> bool:
    for arg, default in zip(node.args.args[-len(node.args.defaults):], node.args.defaults):
        if arg.arg != "caller":
            continue
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
            and default.args[0].id == "get_current_user"
        ):
            return True
    return False
```

- [ ] **Step 3: Replace `tenant_routes` body with the helpers**

```python
def tenant_routes(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[tuple[str, str]] = set()
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        extracted = None
        for dec in node.decorator_list:
            extracted = _extract_route_from_decorator(dec)
            if extracted:
                break
        if extracted is None or not _has_caller_dependency(node):
            continue
        out.add(extracted)
    return out
```

- [ ] **Step 4: Add unit tests**

```python
# tests/ci/test_layer5_tenant_isolation_matrix.py
from scripts.ci.check_layer5_tenant_isolation_matrix import _extract_route_from_decorator, _has_caller_dependency

def test_extract_route_from_decorator():
    source = """
@router.get("/entities")
async def list_entities(): ...
"""
    tree = ast.parse(source)
    dec = tree.body[0].decorator_list[0]
    assert _extract_route_from_decorator(dec) == ("GET", "/api/v1/entities")

def test_has_caller_dependency():
    source = """
async def read_entity(entity_id: str, caller: User = Depends(get_current_user)): ...
"""
    tree = ast.parse(source)
    node = tree.body[0]
    assert _has_caller_dependency(node) is True
```

- [ ] **Step 5: Run tests + lint**

```bash
pytest tests/ci/test_layer5_tenant_isolation_matrix.py -q
python -m ruff check scripts/ci/check_layer5_tenant_isolation_matrix.py
python -m black --check scripts/ci/check_layer5_tenant_isolation_matrix.py
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/ci/check_layer5_tenant_isolation_matrix.py tests/ci/test_layer5_tenant_isolation_matrix.py
git commit -m "refactor(ci): decompose layer5 tenant route AST scanner"
```

---

### Task 9: Refactor `_find_vector_candidates` in `services/layer3-knowledge/src/services/entity_resolution.py`

**Files:**
- Modify: `services/layer3-knowledge/src/services/entity_resolution.py`
- Test: `services/layer3-knowledge/tests/test_entity_resolution_vector.py` (create)

**Why:** The function mixes input validation, Cypher query construction, and result metadata tagging.

- [ ] **Step 1: Extract entity-type label validation**

```python
import re

_ENTITY_TYPE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_entity_type_label(entity_type: str | None) -> str:
    if not entity_type or not _ENTITY_TYPE_RE.match(entity_type):
        raise ValueError(f"Invalid entity_type label: {entity_type!r}")
    return entity_type
```

- [ ] **Step 2: Extract vector query construction**

```python
def _build_vector_query(entity_type: str) -> str:
    return f"""
    CALL db.index.vector.queryNodes($index_name, $k, $embedding)
    YIELD node, score
    WHERE node:{entity_type} AND node.tenant_id = $tenant_id AND score >= $threshold
    OPTIONAL MATCH (node)--()
    WITH node, score, count(*) as reference_count
    RETURN node.id as id, node as properties, score as vector_score, reference_count
    ORDER BY score DESC, id ASC
    LIMIT $k
    """
```

- [ ] **Step 3: Extract metadata tagging**

```python
def _annotate_vector_scores(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        record.setdefault("retrieval_metadata", {})
        record["retrieval_metadata"]["vector_similarity"] = float(record.get("vector_score", 0.0))
    return records
```

- [ ] **Step 4: Replace `_find_vector_candidates` body**

```python
async def _find_vector_candidates(
    self, session, request: EntityResolutionRequest
) -> list[dict[str, Any]]:
    embedding = request.query_attributes.get("embedding")
    if not embedding or not isinstance(embedding, list):
        return []

    threshold = float(request.query_attributes.get("vector_threshold", _DEFAULT_VECTOR_THRESHOLD))
    index_name = request.query_attributes.get("vector_index_name", "entity_embeddings")
    entity_type = _validate_entity_type_label(request.entity_type)

    result = await run_validated_query(
        session,
        _build_vector_query(entity_type),
        {
            "index_name": index_name,
            "k": _CANDIDATE_LIMIT,
            "embedding": embedding,
            "tenant_id": request.tenant_id,
            "threshold": threshold,
        },
        tenant_id=request.tenant_id,
        require_explicit_tenant_id=True,
        query_name="entity_resolution.find_vector_candidates",
    )
    records = await result.data()
    return _annotate_vector_scores(records)
```

- [ ] **Step 5: Add unit tests for the pure helpers**

```python
# services/layer3-knowledge/tests/test_entity_resolution_vector.py
import pytest
from services.layer3_knowledge.src.services.entity_resolution import (
    _validate_entity_type_label,
    _build_vector_query,
    _annotate_vector_scores,
)

def test_validate_entity_type_label_accepts_valid():
    assert _validate_entity_type_label("Account") == "Account"

def test_validate_entity_type_label_rejects_invalid():
    with pytest.raises(ValueError):
        _validate_entity_type_label("1Account")

def test_build_vector_query_includes_label():
    assert ":Account" in _build_vector_query("Account")

def test_annotate_vector_scores():
    records = [{"id": "a", "vector_score": 0.9}]
    out = _annotate_vector_scores(records)
    assert out[0]["retrieval_metadata"]["vector_similarity"] == 0.9
```

- [ ] **Step 6: Run tests + lint**

```bash
pytest services/layer3-knowledge/tests/test_entity_resolution_vector.py -q
python -m ruff check services/layer3-knowledge/src/services/entity_resolution.py
python -m black --check services/layer3-knowledge/src/services/entity_resolution.py
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/layer3-knowledge/src/services/entity_resolution.py services/layer3-knowledge/tests/test_entity_resolution_vector.py
git commit -m "refactor(l3): decompose entity-resolution vector candidate search"
```

---

### Task 10: Refactor `resolve_oidc_config` and `_get_tenant_tier_from_db`

**Files:**
- Modify: `packages/shared/src/value_fabric/shared/identity/providers.py`
- Modify: `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py`
- Test: create/extend tests in the shared package

**Why:** `resolve_oidc_config` chains provider-specific `if/elif` blocks; `_get_tenant_tier_from_db` mixes driver import, query execution, and tier mapping.

#### 10a — OIDC provider defaults

- [ ] **Step 1: Replace the `if/elif` ladder with a provider-defaults table**

```python
# packages/shared/src/value_fabric/shared/identity/providers.py
from __future__ import annotations

import os
from typing import Callable

from .oidc_config import OIDCProviderConfig

OIDC_PROVIDER_DEFAULTS: dict[
    str,
    dict[str, Callable[[OIDCProviderConfig], None]],
] = {}


def _set_google_defaults(config: OIDCProviderConfig) -> None:
    if not config.issuer_url:
        config.issuer_url = "https://accounts.google.com"
    if not config.scopes:
        config.scopes = ["openid", "email", "profile"]


def _set_microsoft_defaults(config: OIDCProviderConfig) -> None:
    if not config.scopes:
        config.scopes = ["openid", "email", "profile", "offline_access"]


def _set_apple_defaults(config: OIDCProviderConfig) -> None:
    if not config.scopes:
        config.scopes = ["name", "email"]


def _set_clerk_defaults(config: OIDCProviderConfig) -> None:
    if not config.issuer_url:
        clerk_domain = os.getenv("CLERK_JWT_ISSUER", "").replace("https://", "")
        if clerk_domain:
            config.issuer_url = f"https://{clerk_domain}"
    if not config.scopes:
        config.scopes = ["openid", "email", "profile", "org"]
    if not config.jwks_uri:
        clerk_jwks = os.getenv("CLERK_JWKS_URL")
        if clerk_jwks:
            config.jwks_uri = clerk_jwks


OIDC_PROVIDER_DEFAULTS = {
    "google": _set_google_defaults,
    "microsoft": _set_microsoft_defaults,
    "apple": _set_apple_defaults,
    "clerk": _set_clerk_defaults,
}


def resolve_oidc_config(config: OIDCProviderConfig) -> OIDCProviderConfig:
    provider = (config.provider_name or "").strip().lower()
    defaults_fn = OIDC_PROVIDER_DEFAULTS.get(provider)
    if defaults_fn:
        defaults_fn(config)
    return config
```

- [ ] **Step 2: Add tests for each provider default**

```python
# packages/shared/tests/identity/test_oidc_providers.py (create if missing)
import pytest
from value_fabric.shared.identity.providers import resolve_oidc_config
from value_fabric.shared.identity.oidc_config import OIDCProviderConfig

def test_google_defaults():
    config = resolve_oidc_config(OIDCProviderConfig(provider_name="google"))
    assert config.issuer_url == "https://accounts.google.com"
    assert "email" in config.scopes

def test_unknown_provider_left_untouched():
    config = resolve_oidc_config(OIDCProviderConfig(provider_name="unknown", issuer_url="https://example.com"))
    assert config.issuer_url == "https://example.com"
```

#### 10b — Tenant tier lookup

- [ ] **Step 3: Extract driver factory resolution**

```python
def _resolve_driver_factory(driver_factory: Any | None = None) -> Any | None:
    if driver_factory is not None:
        return driver_factory
    try:
        from db.driver import get_driver as _get_driver  # noqa: PLC0415
        return _get_driver
    except ImportError:
        return None
```

- [ ] **Step 4: Extract tier value mapping**

```python
_TIER_VALUE_MAP = {
    "shared": TenantTier.SHARED,
    "dedicated": TenantTier.DEDICATED,
    "enterprise": TenantTier.ENTERPRISE,
    "standard": TenantTier.SHARED,
    "isolated": TenantTier.DEDICATED,
}


def _map_tier_value(tier_value: Any, tenant_id: UUID) -> TenantTier:
    tier_str = str(tier_value).lower()
    tier = _TIER_VALUE_MAP.get(tier_str)
    if tier is None:
        raise ValueError(f"Unknown tenant tier value: {tier_value}")
    return tier
```

- [ ] **Step 5: Replace `_get_tenant_tier_from_db` body**

```python
async def _get_tenant_tier_from_db(
    tenant_id: UUID,
    driver_factory: Any | None = None,
) -> TenantTier | None:
    resolved_factory = _resolve_driver_factory(driver_factory)
    if resolved_factory is None:
        logger.warning("Neo4j driver not available for tenant tier lookup, falling back to SHARED for tenant_id=%s", tenant_id)
        return None

    try:
        driver = await resolved_factory()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Tenant {id: $tenant_id})
                RETURN t.tier as tier, t.isolation_tier as isolation_tier
                """,
                tenant_id=str(tenant_id),
            )
            record = await result.single()
            if not record:
                logger.warning("Tenant %s not found in database, falling back to SHARED tier", tenant_id)
                return None

            tier_value = record.get("tier") or record.get("isolation_tier")
            if not tier_value:
                logger.warning("Tenant %s has no tier/isolation_tier property, falling back to SHARED", tenant_id)
                return None

            return _map_tier_value(tier_value, tenant_id)
    except Exception as e:
        logger.error("Failed to query tenant tier from database for %s: %s. Falling back to SHARED", tenant_id, e)
        return None
```

- [ ] **Step 6: Add tests for `_map_tier_value` and `_resolve_driver_factory`**

```python
# packages/shared/tests/rate_limiting/test_admin_api_tier.py (create if missing)
import pytest
from uuid import uuid4
from value_fabric.shared.rate_limiting.admin_api import _map_tier_value, _resolve_driver_factory
from value_fabric.shared.rate_limiting.tenant_rate_limiter import TenantTier

def test_map_tier_value():
    assert _map_tier_value("dedicated", uuid4()) == TenantTier.DEDICATED
    assert _map_tier_value("isolated", uuid4()) == TenantTier.DEDICATED

    with pytest.raises(ValueError):
        _map_tier_value("unknown", uuid4())

def test_resolve_driver_factory_uses_injected():
    def fake_factory():
        return None
    assert _resolve_driver_factory(fake_factory) is fake_factory
```

- [ ] **Step 7: Run tests + lint**

```bash
pytest packages/shared/tests/identity/test_oidc_providers.py packages/shared/tests/rate_limiting/test_admin_api_tier.py -q
python -m ruff check packages/shared/src/value_fabric/shared/identity/providers.py packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py
python -m black --check packages/shared/src/value_fabric/shared/identity/providers.py packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/shared/src/value_fabric/shared/identity/providers.py packages/shared/tests/identity/test_oidc_providers.py packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py packages/shared/tests/rate_limiting/test_admin_api_tier.py
git commit -m "refactor(shared): decompose OIDC provider defaults and tenant tier lookup"
```

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
