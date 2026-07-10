# ADR-032: UI Route/State Progression Contract Ratification

## Status: ACCEPTED

Date: 2026-07-10  
Author: Platform Engineering Staff  
Approver: Architecture Review Board  
Supersedes: ADR-012 (Imperative Navigation), ADR-015 (Browser History as State Source)

---

## Context

### The Problem

Fabric 4L's UI is a multi-step workflow application where users progress through setup, configuration, execution, and analysis phases. Navigation between these phases is currently managed through a mix of imperative router calls, direct URL manipulation, and browser history — none of which enforce workflow constraints. The result is users landing in invalid states, data dependencies being violated, and analytics that misattribute user actions to wrong workflow stages.

**Pattern A: Imperative Router Calls** (used in `apps/web/src/pages/`, `apps/web/src/components/workflows/`)
Navigation is triggered by `router.push("/path")` or `history.push("/path")` calls scattered through click handlers, effect hooks, and callback functions. These calls bypass any workflow validation: a user can navigate directly from `/setup` to `/analyze` without completing configuration, causing the analysis page to crash when it attempts to access configuration state that was never set. During a recent user study, 12% of sessions ended in a blank screen due to invalid navigation sequences.

**Pattern B: Browser History as State Source** (used in `apps/web/src/hooks/use-workflow-state.ts`)
Application workflow state is derived from `window.location.pathname` and `URLSearchParams`. The browser back button becomes the primary mechanism for returning to previous steps. This breaks workflow semantics: "back" from analysis should return to run (the previous workflow step), but browser history might contain an external URL or a different application route. It also makes it impossible to implement workflow-specific guard logic: the browser doesn't know that leaving `/configure` with unsaved changes should trigger a confirmation dialog.

**Pattern C: Direct URL Parsing in Components** (used in `apps/web/src/components/shared/`, legacy components)
Components read routing information directly from `useRouter()` or `window.location`, making routing decisions based on string parsing of URL segments. This couples components to URL structure, making route changes high-touch refactors. When the platform restructured URLs from `/workflows/:id/run` to `/run/:workflowId`, 34 components required manual updates because they parsed the URL to extract the workflow ID.

**Pattern D: Route Guards with Side Effects** (used in `apps/web/src/guards/legacy/`)
Route guard functions perform API calls, database mutations, and analytics tracking as side effects of navigation decisions. These side effects make guards non-deterministic, untestable, and prone to race conditions. A guard that fetches user permissions to decide navigation might execute the fetch after navigation has already completed, resulting in a flash of unauthorized content.

### Operational Impact

| Incident ID | Root Cause | Date |
|-------------|-----------|------|
| INC-2026-0218 | User navigated from `/setup` to `/analyze` via URL bar; analysis page crashed on missing config state; 200+ error reports | 2026-02-18 |
| INC-2026-0401 | Browser back button from analysis took user to external site (previous history entry); workflow state lost, user had to restart | 2026-04-01 |
| INC-2026-0515 | Component parsed `router.query.id` after route change to `/run/:workflowId`; extracted undefined, passed to API causing 500 | 2026-05-15 |
| INC-2026-0610 | Route guard made permission API call; navigation proceeded before response; unauthorized user saw admin UI for 2 seconds | 2026-06-10 |

### Decision Forces

1. **Workflow enforcement:** Navigation must respect workflow constraints. Invalid transitions are prevented, not just discouraged.
2. **State machine clarity:** UI state progression is modeled as an explicit finite state machine with known states and transitions.
3. **Declarative routes:** Route definitions declare their requirements (context, data dependencies, allowed transitions) rather than encoding them imperatively.
4. **Guard purity:** Route guards are pure functions with no side effects. They read context and return boolean/navigation-result.
5. **History abstraction:** Workflow history is managed by the state machine, not the browser. Back navigation respects workflow semantics.
6. **Deep linking:** URLs map to states and support bookmarking, but invalid deep links redirect to valid entry points.
7. **Analytics integrity:** Every navigation event is logged with from-state, to-state, transition name, and validation result.
8. **Testability:** Navigation logic is testable without browser environment or router mocking.

---

## Decision

We will adopt a **single canonical pattern: State-Machine-Driven Navigation with Declarative Route Manifests**. UI state progression is modeled as a finite state machine where states correspond to application screens and transitions correspond to user actions or workflow events. Every route is declared in a manifest that specifies its requirements, guards, and allowed transitions.

### Specification

#### 1. The Four Canonical UI Modes

All Fabric 4L workflows follow the same four-mode progression:

| Mode | State ID | Purpose | Data Dependencies |
|------|----------|---------|-------------------|
| `setup` | `workflow_setup` | Initial configuration, connection testing | Tenant context, feature flags |
| `configure` | `workflow_configure` | Detailed parameter configuration | Setup completion, schema definitions |
| `run` | `workflow_run` | Execute workflow, monitor progress | Configuration validation, resource allocation |
| `analyze` | `workflow_analyze` | Review results, export, schedule | Run completion, output data |

Transitions between modes are validated by the state machine. The only valid transitions are:

```
setup → configure → run → analyze
setup → configure → setup (reconfigure)
run   → configure (edit while paused)
analyze → run (rerun with same config)
analyze → configure (modify and rerun)
```

All other transitions are rejected with a warning and a redirect to the last valid state.

#### 2. Route Manifest

Every route is declared in the route manifest:

```typescript
// apps/web/src/routes/manifest.ts
import { defineRouteManifest } from "@fabric/platform/ui";
import {
  requireTenantContext,
  requireActiveSession,
  requireSetupComplete,
  requireConfigurationValid,
  requireRunComplete,
} from "./guards";

export const routeManifest = defineRouteManifest({
  "/": {
    state: "landing",
    guards: [requireTenantContext],
    onEnter: [trackPageView("landing")],
    transitions: {
      "NAVIGATE_SETUP": "/setup",
    },
  },
  "/setup": {
    state: "workflow_setup",
    guards: [requireTenantContext, requireActiveSession],
    onEnter: [trackPageView("setup"), fetchSetupSchema],
    transitions: {
      "SETUP_COMPLETE": "/configure",
      "SETUP_CANCEL": "/",
    },
  },
  "/configure": {
    state: "workflow_configure",
    guards: [requireTenantContext, requireActiveSession, requireSetupComplete],
    onEnter: [trackPageView("configure"), fetchConfigurationSchema],
    transitions: {
      "CONFIG_SAVE": "/run",
      "CONFIG_BACK": "/setup",
      "CONFIG_CANCEL": "/",
    },
  },
  "/run": {
    state: "workflow_run",
    guards: [
      requireTenantContext,
      requireActiveSession,
      requireSetupComplete,
      requireConfigurationValid,
    ],
    onEnter: [trackPageView("run"), initializeRun],
    transitions: {
      "RUN_COMPLETE": "/analyze",
      "RUN_PAUSE": "/configure",
      "RUN_CANCEL": "/configure",
    },
  },
  "/analyze": {
    state: "workflow_analyze",
    guards: [
      requireTenantContext,
      requireActiveSession,
      requireSetupComplete,
      requireConfigurationValid,
      requireRunComplete,
    ],
    onEnter: [trackPageView("analyze"), fetchResults],
    transitions: {
      "ANALYZE_RERUN": "/run",
      "ANALYZE_MODIFY": "/configure",
      "ANALYZE_DONE": "/",
    },
  },
});
```

#### 3. State Machine

The state machine manages workflow progression:

```typescript
// platform/ui/state-machine.ts
interface StateMachineConfig<S extends string, T extends string> {
  initial: S;
  states: Record<S, {
    on?: Partial<Record<T, S>>;
    onEnter?: Array<(ctx: NavigationContext) => void>;
    onExit?: Array<(ctx: NavigationContext) => void>;
  }>;
}

class StateMachine<S extends string, T extends string> {
  private current: S;
  private history: S[] = [];

  constructor(private config: StateMachineConfig<S, T>) {
    this.current = config.initial;
  }

  canTransition(event: T): boolean {
    const transitions = this.config.states[this.current]?.on;
    return transitions?.[event] !== undefined;
  }

  transition(event: T): S {
    if (!this.canTransition(event)) {
      const warning = `Invalid transition: ${this.current} → ${event}`;
      console.warn(warning);
      telemetry.recordEvent("ui.invalid_transition", {
        from_state: this.current,
        event,
      });
      // Redirect to current state (no-op with warning)
      return this.current;
    }

    const next = this.config.states[this.current].on![event]!;
    this.history.push(this.current);
    this.current = next;
    return next;
  }

  goBack(): S {
    const previous = this.history.pop();
    if (previous) {
      this.current = previous;
    }
    return this.current;
  }
}
```

#### 4. Navigation API

All navigation goes through the `navigate()` function:

```typescript
// platform/ui/navigation.ts
async function navigate(
  transition: string,
  params?: Record<string, string>,
): Promise<NavigationResult> {
  const currentState = stateMachine.getCurrent();
  const route = routeManifest.getRouteForState(currentState);

  // 1. Check if transition is valid
  if (!route.transitions[transition]) {
    return {
      success: false,
      error: `Transition "${transition}" not allowed from state "${currentState}"`,
    };
  }

  // 2. Run guards (pure functions, no side effects)
  const guardResults = await runGuards(route.guards, navigationContext);
  const failedGuard = guardResults.find(r => !r.passed);
  if (failedGuard) {
    return {
      success: false,
      error: failedGuard.reason,
      redirect: failedGuard.redirectTo,
    };
  }

  // 3. Execute transition
  const nextState = route.transitions[transition];
  const nextRoute = routeManifest.getRoute(nextState);

  // 4. Run onExit for current state
  await runLifecycleHooks(currentRoute.onExit, navigationContext);

  // 5. Update state machine
  stateMachine.transition(transition);

  // 6. Run onEnter for next state
  await runLifecycleHooks(nextRoute.onEnter, navigationContext);

  // 7. Update URL (for deep linking and browser sync)
  updateBrowserUrl(nextRoute.path, params);

  // 8. Log navigation event
  telemetry.recordEvent("ui.navigation", {
    from_state: currentState,
    to_state: nextState,
    transition,
    guard_duration_ms: guardResults.totalDuration,
  });

  return { success: true, state: nextState };
}
```

#### 5. Route Guards

Guards are pure functions that read context and return a result:

```typescript
// apps/web/src/routes/guards.ts
import { NavigationContext, GuardResult } from "@fabric/platform/ui";

export const requireTenantContext = (ctx: NavigationContext): GuardResult => {
  if (!ctx.tenantContext) {
    return {
      passed: false,
      reason: "Tenant context required",
      redirectTo: "/login",
    };
  }
  return { passed: true };
};

export const requireSetupComplete = (ctx: NavigationContext): GuardResult => {
  if (!ctx.workflowState?.setupCompletedAt) {
    return {
      passed: false,
      reason: "Setup must be completed before accessing this page",
      redirectTo: "/setup",
    };
  }
  return { passed: true };
};

// Guards are pure — no API calls, no mutations, no side effects
```

#### 6. Deep Linking

When a user navigates directly to a URL:

1. The router resolves the URL to a state using the route manifest.
2. All guards for that state are executed.
3. If guards pass, the state machine is initialized to that state.
4. If guards fail, the user is redirected to the appropriate entry point (with the failure reason logged).
5. Browser history synchronization is one-directional: state machine → URL. URL changes do not directly affect state.

```typescript
// On initial load
function handleDeepLink(url: string): void {
  const state = routeManifest.resolveUrlToState(url);
  if (!state) {
    navigateTo("/");  // Unknown URL → landing
    return;
  }

  const route = routeManifest.getRoute(state);
  const guardResults = runGuards(route.guards, buildNavigationContext());

  if (guardResults.allPassed) {
    stateMachine.initialize(state);
    runLifecycleHooks(route.onEnter, navigationContext);
  } else {
    const failedGuard = guardResults.find(r => !r.passed);
    navigateTo(failedGuard?.redirectTo ?? "/");
  }
}
```

### Why State Machine over alternatives

| Alternative | Reason for rejection |
|-------------|---------------------|
| Imperative router (React Router, Vue Router) | No workflow enforcement; any navigation is allowed |
| Browser history as source of truth | Breaks workflow semantics; back button behavior unpredictable |
| Centralized state management (Redux, Zustand) | Good for data but doesn't model navigation constraints |
| URL-based route guards | Guards run after navigation starts; flash of unauthorized content |
| Breadcrumb navigation | Visual only; doesn't enforce transitions |

A finite state machine explicitly models valid and invalid transitions, making workflow constraints enforceable at the code level rather than relying on convention or documentation.

---

## Consequences

### Positive

- **Workflow enforcement:** Invalid transitions are impossible by construction. Users cannot navigate to analysis without completing setup and configuration.
- **Deterministic behavior:** Given the same state and transition, the outcome is always the same. No race conditions, no side-effect ordering issues.
- **Testability:** State machines and pure guards are trivially unit testable. Navigation logic tests require no browser or router mocking.
- **Analytics integrity:** Every navigation event is logged with from-state, to-state, and transition name. Funnel analysis is accurate.
- **Deep linking:** URLs support bookmarking and sharing while maintaining workflow integrity through guard validation.
- **Guard purity:** Pure function guards are deterministic, fast, and cacheable. No API race conditions.
- **History abstraction:** Workflow back-navigation respects semantic workflow steps, not browser history chronology.
- **Error prevention:** The 12% of sessions that previously ended in blank screens due to invalid navigation are eliminated.
- **Refactoring safety:** Changing a route path requires updating only the manifest; components reference states, not URLs.

### Negative

- **Learning curve:** Developers must learn the state machine model and manifest syntax. Documentation and code generation mitigate this.
- **Boilerplate:** Every route requires a manifest entry with guards and transitions. A CLI generator (`fabric generate route`) scaffolds the boilerplate.
- **Edge case handling:** Some workflows have complex branching (e.g., setup can skip to run if a template is used). The state machine supports conditional transitions via guard-evaluated transition predicates.
- **Migration cost:** All imperative `router.push()` calls must be replaced with `navigate()` transitions. All browser-history-dependent code must be refactored.
- **Integration with existing routers:** The state machine wraps React Router / Vue Router; it doesn't replace them. URL sync is handled by an adapter.

---

## Compliance

### Automated Enforcement (Three Layers)

**IDE / Local Development:**
- ESLint rule `no-imperative-navigation`: Error on `router.push()`, `history.push()`, `navigate("/path")` (string literal navigation) outside the `navigate()` wrapper.
- ESLint rule `no-url-concatenation`: Error on string concatenation producing URL-like paths (e.g., `"/workflows/" + id`).
- ESLint rule `no-direct-url-parse`: Error on components reading `window.location.pathname` or `useRouter().query` to make routing decisions.
- ESLint rule `no-guard-side-effects`: Error on API calls, mutations, or `console.log` inside guard functions.

**Pre-commit:**
- `lint-staged` runs ESLint on changed files.
- `route-manifest-check` warns if a route is added without a manifest entry.

**CI Gate:**
- `check_ui_route_state` job runs on every PR:
  - ESLint rules are errors
  - Route manifest validation: all declared states have valid transitions, no dead states, no unreachable states
  - Guard purity check: guards contain no async API calls, no mutations, no console statements
  - Transition coverage: integration test navigates all valid transitions
  - Dead transition detection: transitions declared in manifest but never triggered in tests are flagged

### Runtime Enforcement
- `navigate()` rejects invalid transitions with a logged warning.
- State machine throws if initialized to an unreachable state.
- URL changes triggered by browser back/forward are intercepted and routed through `handleDeepLink()`.

### Manual Verification
- Quarterly review: 3 random user flows audited for navigation correctness.
- UX review: new features must include state machine diagram in design doc.

---

## Migration

### Timeline

| Phase | Version | Date | Behavior |
|-------|---------|------|----------|
| Soft deprecation | v1.2.0 | 2026-07-10 | ESLint warnings, `navigate()` available, new routes use manifest |
| Hard enforcement | v1.3.0 | 2026-10-10 | ESLint errors, CI fails, all navigation must use state machine |
| Removal | v1.4.0 | 2027-01-10 | Legacy router adapters removed, all routes must have manifest entries |

### Codemod: `migrate-navigation`

```bash
npx @fabric/codemod migrate-navigation --target ./apps/web/src --write
```

**Before (imperative navigation):**
```typescript
// apps/web/src/components/setup/SetupForm.tsx
import { useRouter } from "next/router";

export function SetupForm() {
  const router = useRouter();

  const handleComplete = async () => {
    await saveSetup(config);
    // Imperative navigation — no workflow validation
    router.push("/configure");
  };

  const handleCancel = () => {
    // Direct URL manipulation
    window.location.href = "/";
  };

  return (
    <form>
      {/* ... */}
      <button onClick={handleComplete}>Continue</button>
      <button onClick={handleCancel}>Cancel</button>
    </form>
  );
}
```

**After (state machine navigation):**
```typescript
// apps/web/src/components/setup/SetupForm.tsx
import { useNavigation } from "@fabric/platform/ui";

export function SetupForm() {
  const { navigate, canTransition } = useNavigation();

  const handleComplete = async () => {
    await saveSetup(config);
    // Validated state machine transition
    await navigate("SETUP_COMPLETE");
  };

  const handleCancel = () => {
    navigate("SETUP_CANCEL");
  };

  return (
    <form>
      {/* ... */}
      <button onClick={handleComplete} disabled={!canTransition("SETUP_COMPLETE")}>
        Continue
      </button>
      <button onClick={handleCancel}>Cancel</button>
    </form>
  );
}
```

**Before (URL parsing in component):**
```typescript
// apps/web/src/components/shared/WorkflowHeader.tsx
import { useRouter } from "next/router";

export function WorkflowHeader() {
  const router = useRouter();
  // Fragile URL parsing — breaks when route changes
  const workflowId = router.query.id as string;
  const isRunPage = router.pathname.startsWith("/run");

  return (
    <header>
      <h1>Workflow {workflowId}</h1>
      {isRunPage && <RunStatusBadge workflowId={workflowId} />}
    </header>
  );
}
```

**After (state-based rendering):**
```typescript
// apps/web/src/components/shared/WorkflowHeader.tsx
import { useNavigationState } from "@fabric/platform/ui";

export function WorkflowHeader() {
  const { currentState, params } = useNavigationState();
  // Stable — reads from state machine, not URL
  const workflowId = params.workflowId;
  const isRunPage = currentState === "workflow_run";

  return (
    <header>
      <h1>Workflow {workflowId}</h1>
      {isRunPage && <RunStatusBadge workflowId={workflowId} />}
    </header>
  );
}
```

**Before (route guard with side effects):**
```typescript
// apps/web/src/guards/legacy/require-permissions.ts
export async function requirePermissions(router) {
  // SIDE EFFECT: API call inside guard
  const response = await fetch("/api/permissions");
  const { permissions } = await response.json();

  // SIDE EFFECT: Analytics tracking
  analytics.track("guard_check", { permissions });

  if (!permissions.includes("workflow:run")) {
    router.push("/unauthorized");
    return false;
  }
  return true;
}
```

**After (pure guard):**
```typescript
// apps/web/src/routes/guards.ts
import { NavigationContext, GuardResult } from "@fabric/platform/ui";

export const requireWorkflowRunPermission = (
  ctx: NavigationContext,
): GuardResult => {
  // Pure function — reads from context only, no API calls
  if (!ctx.permissions.includes("workflow:run")) {
    return {
      passed: false,
      reason: "Missing workflow:run permission",
      redirectTo: "/unauthorized",
    };
  }
  return { passed: true };
};

// API calls happen in onEnter hooks, not guards
const fetchPermissions = async (ctx: NavigationContext) => {
  const response = await fetch("/api/permissions");
  ctx.setPermissions(await response.json());
};
```

### Page-by-Page Rollout

| Page | Pattern Before | Migration Effort | Owner | Target Completion |
|------|---------------|-----------------|-------|-------------------|
| `/setup` | Imperative router | Medium | @team-web | 2026-08-15 |
| `/configure` | Imperative router + URL parse | Medium | @team-web | 2026-08-30 |
| `/run` | Browser history deps | High | @team-web | 2026-09-15 |
| `/analyze` | Imperative router | Medium | @team-web | 2026-09-01 |
| Shared components | Direct URL parse | High (34 components) | @team-web | 2026-09-30 |

### Checklist Per Page

- [ ] Add route manifest entry with state, guards, transitions
- [ ] Replace all `router.push()` with `navigate("TRANSITION_NAME")`
- [ ] Replace all `window.location` manipulation with `navigate()`
- [ ] Replace URL parsing with `useNavigationState()` hook
- [ ] Convert route guards to pure functions (no side effects)
- [ ] Add `onEnter` hooks for data fetching and analytics
- [ ] Verify deep linking works (direct URL → correct state)
- [ ] Verify back navigation uses state machine history
- [ ] Run integration tests: all transitions execute correctly
- [ ] Tag PR with `contract-adr-032`

---

## Appendix: State Machine Diagram

```
                    +---------+
                    | landing |
                    +----+----+
                         |
                    NAVIGATE_SETUP
                         |
                         v
+-------+    SETUP_CANCEL   +--------+   SETUP_COMPLETE   +------------+
|   /   |<------------------+ setup  +------------------->+ configure  |
+-------+                   +---+----+                   +----+-------+
                                ^                             |
                                |                             | CONFIG_SAVE
                          CONFIG_BACK                         |
                                |                             v
+----------+  ANALYZE_MODIFY   +---+----+   RUN_COMPLETE    +----+-------+
| configure |<------------------+  run   +------------------>+  analyze   |
+----------+                   +---+----+                   +----+-------+
     ^                             |                             |
     |                      RUN_PAUSE/RUN_CANCEL          ANALYZE_RERUN
     |                             |                             |
     +-----------------------------+                             |
                                                                 |
                     ANALYZE_DONE                                |
     +-----------------------+                                   |
     |                       |                                   |
     v                       |                                   |
+----+----+                  |                                   |
|    /    |<-----------------+-----------------------------------+
+---------+
```

---

## References

- CONTRACT.md Section 2.7: UI State Progression and Route Model
- ADR-029: Middleware and Auth Flow Contract Ratification
- `examples/canonical/ui/route-manifest.ts`: Reference implementation
- `examples/canonical/ui/guards.ts`: Example route guards
- `test/ui-state-machine.spec.ts`: Compliance test
- INC-2026-0218, INC-2026-0401, INC-2026-0515, INC-2026-0610: Incident reports
