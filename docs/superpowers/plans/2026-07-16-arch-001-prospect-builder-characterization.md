# ARCH-001 Prospect Builder Characterization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic state, type-contract, and page-level characterization tests for `ProspectPromptBuilder` without changing production behavior.

**Architecture:** Place pure reducer/helper coverage beside `ProspectPromptBuilder.state.ts` and extend the existing page behavior suite for public user workflows. Use typed test-local builders, accessible queries, exact payload assertions, and no snapshots or production test seams.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, user-event, React Router, TanStack Query, pnpm 10.18.1.

## Global Constraints

- Do not change production code, UI, styling, state-machine behavior, workflow behavior, API contracts, or business rules.
- Do not add snapshots, `any`, unsafe casts, generated-file changes, or new dependencies.
- Use pnpm only; never use npm or yarn.
- Preserve public props, callback signatures, payload fields, navigation paths, accessibility semantics, and error copy.
- Record surprising behavior as a follow-up rather than correcting it in this PR.
- If a production test seam becomes unavoidable, stop and obtain approval before adding it.

---

### Task 1: Characterize reducer, state invariants, payloads, and type contracts

**Files:**
- Create: `apps/web/src/components/workspace/ProspectPromptBuilder.state.test.ts`
- Inspect only: `apps/web/src/components/workspace/ProspectPromptBuilder.state.ts`
- Inspect only: `apps/web/src/components/workspace/promptParser.ts`

**Interfaces:**
- Consumes: `getInitialState`, `builderReducer`, `buildPayload`, `canSubmit`, `getValidationIssues`, `resolveNavigationAccountId`, `formatSubmitError`, and the exported builder types.
- Produces: direct executable contracts for pure state behavior and compile-time public type compatibility.

- [ ] **Step 1: Add typed fixtures and initial-state tests**

Create the test file with imports and a state builder that always starts from production initialization:

```ts
import { describe, expect, expectTypeOf, it } from "vitest";
import type { ProspectPromptBuilderProps } from "./ProspectPromptBuilder";
import {
  buildPayload,
  builderReducer,
  canSubmit,
  formatSubmitError,
  getInitialState,
  getValidationIssues,
  resolveNavigationAccountId,
  type BuilderAction,
  type BuilderState,
  type CompanyOption,
  type CreateSetupResult,
  type ProspectSetupPromptPayload,
} from "./ProspectPromptBuilder.state";

const ACME: CompanyOption = {
  id: "company-acme",
  name: "Acme Corp",
  domain: "acme.example",
  industry: "Manufacturing",
  accountId: "account-acme",
};

function createState(overrides: Partial<BuilderState> = {}): BuilderState {
  return { ...getInitialState(""), ...overrides };
}

describe("ProspectPromptBuilder state contract", () => {
  it("initializes stable defaults and seeds a selected company", () => {
    const empty = getInitialState("");
    expect(empty).toMatchObject({
      promptText: "",
      mode: "Balanced",
      primaryDeliverable: "account_brief",
      enrichmentDepth: "standard",
      useUploadedFiles: true,
      usePriorAccountContext: true,
      runWebEnrichment: true,
      complianceSensitive: false,
      attachments: [],
      isSubmitting: false,
    });

    const seeded = getInitialState("", ACME);
    expect(seeded.selectedCompany).toEqual(ACME);
    expect(seeded.draft).toMatchObject({
      companyName: "Acme Corp",
      companyDomain: "acme.example",
      industry: "Manufacturing",
    });
    expect(seeded.visibleSections.company).toBe(true);
    expect(seeded.promptText).toContain("Company: Acme Corp");
  });
```

- [ ] **Step 2: Add reducer transition and invariant tests**

Within the same `describe`, add tests that dispatch real actions:

```ts
  it("applies prompt text and preserves detected compliance sensitivity", () => {
    const state = builderReducer(createState(), {
      type: "APPLY_PROMPT_TEXT",
      promptText: [
        "Company: Regulated Co",
        "Compliance:",
        "- Regulated Industry: Healthcare",
        "- Known Requirements: HIPAA",
      ].join("\n"),
    });
    expect(state.draft.companyName).toBe("Regulated Co");
    expect(state.draft.compliance.knownRequirements).toEqual(["HIPAA"]);
    expect(state.complianceSensitive).toBe(true);
  });

  it("selects and then clears a matched company on manual edits", () => {
    const selected = builderReducer(createState(), {
      type: "SELECT_COMPANY",
      company: ACME,
    });
    expect(selected.selectedCompany).toEqual(ACME);
    expect(selected.searchOpen).toBe(false);
    expect(selected.promptText).toContain("Website: acme.example");

    const edited = builderReducer(selected, {
      type: "SET_COMPANY_FIELD",
      field: "companyName",
      value: "Acme Holdings",
    });
    expect(edited.selectedCompany).toBeUndefined();
    expect(edited.draft.companyName).toBe("Acme Holdings");
  });

  it("strengthens missing core sections and enables deep research defaults", () => {
    const strengthened = builderReducer(createState(), {
      type: "STRENGTHEN_PROMPT",
    });
    expect(strengthened.visibleSections).toMatchObject({
      company: true,
      buyingContext: true,
      stakeholders: true,
      businessPain: true,
      deliverable: true,
    });
    expect(strengthened.draft.desiredOutputs).toEqual(["account_brief"]);

    const deep = builderReducer(strengthened, {
      type: "ENABLE_DEEP_RESEARCH",
    });
    expect(deep.mode).toBe("Deep");
    expect(deep.enrichmentDepth).toBe("deep");
    expect(deep.visibleSections.researchFocus).toBe(true);
    expect(deep.draft.researchFocus).toHaveLength(5);
  });

  it("accumulates attachments and preserves submit lifecycle messages", () => {
    const attached = builderReducer(createState(), {
      type: "ATTACHMENTS_ADDED",
      attachments: [{ id: "attachment-1", name: "brief.pdf" }],
    });
    expect(attached.attachments).toEqual([
      { id: "attachment-1", name: "brief.pdf" },
    ]);
    expect(attached.statusMessage).toBe("1 attachment added.");

    const submitting = builderReducer(attached, { type: "START_SUBMIT" });
    expect(submitting).toMatchObject({
      isSubmitting: true,
      statusMessage: "Launching intelligence...",
      successMessage: "",
      errorMessage: "",
    });
    const succeeded = builderReducer(submitting, {
      type: "SUBMIT_SUCCESS",
      message: "New value case created.",
    });
    expect(succeeded).toMatchObject({
      isSubmitting: false,
      statusMessage: "",
      successMessage: "New value case created.",
      errorMessage: "",
    });
    expect(builderReducer(succeeded, { type: "CLEAR_MESSAGES" })).toMatchObject({
      statusMessage: "",
      successMessage: "",
      errorMessage: "",
    });
  });
```

- [ ] **Step 3: Add exact payload, navigation, validation, and error tests**

```ts
  it("builds the exact setup payload from current state", () => {
    const selected = builderReducer(createState(), {
      type: "SELECT_COMPANY",
      company: ACME,
    });
    const state: BuilderState = {
      ...selected,
      promptText: "Company: Acme Corp\nBuying context: Renewal risk",
      draft: {
        ...selected.draft,
        buyingContext: "Renewal risk",
        whyNow: "Q4 planning",
        businessPain: ["Manual reporting"],
        desiredOutcomes: ["Faster decisions"],
        stakeholders: {
          ...selected.draft.stakeholders,
          economicBuyer: "CFO",
        },
      },
      attachments: [{ id: "attachment-1", name: "brief.pdf" }],
    };

    expect(buildPayload(state)).toEqual({
      companyName: "Acme Corp",
      companyDomain: "acme.example",
      industry: "Manufacturing",
      accountContext: "Renewal risk | Q4 planning",
      buyingContext: "Renewal risk",
      whyNow: "Q4 planning",
      knownInitiative: undefined,
      businessPain: ["Manual reporting"],
      currentFriction: [],
      desiredOutcomes: ["Faster decisions"],
      stakeholders: { economicBuyer: "CFO" },
      sourceArtifacts: [{ id: "attachment-1", name: "brief.pdf" }],
      outputType: "account_brief",
      desiredOutputs: ["account_brief"],
      mode: "Balanced",
      enrichmentDepth: "standard",
      useUploadedFiles: true,
      usePriorAccountContext: true,
      runWebEnrichment: true,
      complianceSensitive: false,
      deepResearch: false,
      freeformPrompt: "Company: Acme Corp\nBuying context: Renewal risk",
    });
  });

  it("uses result account IDs before selected-company account IDs", () => {
    expect(resolveNavigationAccountId({ accountId: "created" }, ACME)).toBe(
      "created"
    );
    expect(resolveNavigationAccountId(undefined, ACME)).toBe("account-acme");
    expect(resolveNavigationAccountId(undefined)).toBeUndefined();
  });

  it("reports current validation invariants and submit eligibility", () => {
    const empty = createState();
    expect(canSubmit(empty)).toBe(false);
    expect(
      getValidationIssues(empty)
        .filter(issue => issue.priority === "required")
        .map(issue => [issue.id, issue.resolved])
    ).toEqual([
      ["identity", false],
      ["context", false],
    ]);

    const identified = builderReducer(empty, {
      type: "SELECT_COMPANY",
      company: ACME,
    });
    expect(canSubmit(identified)).toBe(true);
    expect(
      getValidationIssues(identified).find(issue => issue.id === "identity")
        ?.resolved
    ).toBe(true);
  });

  it("normalizes duplicate and generic submission errors", () => {
    expect(
      formatSubmitError({
        statusCode: 409,
        responseData: {
          error: "duplicate account",
          duplicate_candidates: [{ name: "Acme Corp" }],
          suggested_action: "merge",
        },
      })
    ).toBe(
      "Duplicate account detected for Acme Corp. Review and merge before launching."
    );
    expect(formatSubmitError(new Error("provider detail"))).toBe(
      "Unable to launch intelligence. Please review the input and try again."
    );
  });
```

- [ ] **Step 4: Add compile-time public contract assertions**

```ts
  it("preserves public callback and payload type contracts", () => {
    expectTypeOf(buildPayload).returns.toEqualTypeOf<ProspectSetupPromptPayload>();
    expectTypeOf(resolveNavigationAccountId).returns.toEqualTypeOf<
      string | undefined
    >();
    expectTypeOf<NonNullable<ProspectPromptBuilderProps["onCreateSetup"]>>()
      .parameter(0)
      .toEqualTypeOf<ProspectSetupPromptPayload>();
    expectTypeOf<NonNullable<ProspectPromptBuilderProps["onNavigateToWorkspace"]>>()
      .parameters.toEqualTypeOf<[path: string, accountId: string]>();
    expectTypeOf<CreateSetupResult>().toEqualTypeOf<
      { accountId: string } | void
    >();

    expectTypeOf<BuilderAction>().toMatchTypeOf<
      Parameters<typeof builderReducer>[1]
    >();
  });
});
```

- [ ] **Step 5: Run the state characterization file**

Run:

```bash
pnpm --dir apps/web exec vitest run src/components/workspace/ProspectPromptBuilder.state.test.ts
```

Expected: all state and type-contract tests pass. If dependencies are absent,
record the exact missing executable or package error and proceed only after a
pnpm frozen-lockfile install is authorized and succeeds.

- [ ] **Step 6: Commit the state contract tests**

```bash
git add apps/web/src/components/workspace/ProspectPromptBuilder.state.test.ts
git commit -m "test(frontend): characterize prospect builder state"
```

---

### Task 2: Expand page-level user workflow characterization

**Files:**
- Modify: `apps/web/src/components/ProspectSetup.behavior.test.tsx`
- Inspect only: `apps/web/src/pages/ProspectSetup.tsx`
- Inspect only: `apps/web/src/components/workspace/ProspectPromptBuilder.tsx`

**Interfaces:**
- Consumes: `ProspectSetupPage`, `ProspectPromptBuilderProps`, the existing router/query harness, and public callbacks.
- Produces: explicit user-visible contracts for submission, navigation, keyboard operation, validation, and errors.

- [ ] **Step 1: Add a valid prompt fixture and success-path test**

Add near the existing `MODES` constant:

```ts
const VALID_PROMPT = [
  "Company: Acme Corp",
  "Website: acme.example",
  "Buying context: Renewal risk",
  "Why this account now: Q4 planning",
].join("\n");
```

Add this page test:

```ts
  it.each(MODES)(
    "submits the current payload and navigates to the tenant-aware workspace (%s)",
    async mode => {
      const user = userEvent.setup();
      const onCreateSetup = vi.fn().mockResolvedValue({ accountId: "account-123" });
      const onNavigateToWorkspace = vi.fn();
      renderProspectSetup(
        <ProspectSetupPage
          mode={mode}
          onCreateSetup={onCreateSetup}
          onNavigateToWorkspace={onNavigateToWorkspace}
        />
      );

      await user.type(screen.getByLabelText("New value case prompt"), VALID_PROMPT);
      await user.click(screen.getByRole("button", { name: "Launch Intelligence" }));

      expect(onCreateSetup).toHaveBeenCalledTimes(1);
      expect(onCreateSetup).toHaveBeenCalledWith(
        expect.objectContaining({
          companyName: "Acme Corp",
          companyDomain: "acme.example",
          buyingContext: "Renewal risk",
          whyNow: "Q4 planning",
          outputType: "account_brief",
          mode: "Balanced",
          freeformPrompt: VALID_PROMPT,
        })
      );
      expect(onNavigateToWorkspace).toHaveBeenCalledWith(
        "/t/default/accounts/account-123/intelligence/signals",
        "account-123"
      );
    }
  );
```

- [ ] **Step 2: Add keyboard and duplicate-error behavior tests**

```ts
  it("submits with Ctrl+Enter through the same callback contract", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockResolvedValue({ accountId: "account-123" });
    renderProspectSetup(<ProspectSetupPage onCreateSetup={onCreateSetup} />);

    const prompt = screen.getByLabelText("New value case prompt");
    await user.type(prompt, VALID_PROMPT);
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(onCreateSetup).toHaveBeenCalledTimes(1);
  });

  it("renders the normalized duplicate-account error", async () => {
    const user = userEvent.setup();
    const onCreateSetup = vi.fn().mockRejectedValue({
      statusCode: 409,
      responseData: {
        error: "duplicate account",
        duplicate_candidates: [{ name: "Acme Corp" }],
        suggested_action: "merge",
      },
    });
    renderProspectSetup(<ProspectSetupPage onCreateSetup={onCreateSetup} />);

    await user.type(screen.getByLabelText("New value case prompt"), VALID_PROMPT);
    await user.click(screen.getByRole("button", { name: "Launch Intelligence" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Duplicate account detected for Acme Corp. Review and merge before launching."
    );
  });
```

- [ ] **Step 3: Add explicit validation guidance assertions**

```ts
  it.each(MODES)("shows required validation guidance before submission (%s)", mode => {
    renderProspectSetup(<ProspectSetupPage mode={mode} />);
    expect(
      screen.getByText("Add a company name, domain, or attachment to identify the account")
    ).toBeVisible();
    expect(
      screen.getByText("Write at least a few sentences describing the context")
    ).toBeVisible();
  });
```

- [ ] **Step 4: Run page and parser characterization together**

Run:

```bash
pnpm --dir apps/web exec vitest run \
  src/components/ProspectSetup.behavior.test.tsx \
  src/components/workspace/ProspectPromptBuilder.state.test.ts \
  src/components/workspace/promptParser.test.ts
```

Expected: all selected tests pass with no snapshot updates.

- [ ] **Step 5: Commit page characterization**

```bash
git add apps/web/src/components/ProspectSetup.behavior.test.tsx
git commit -m "test(frontend): characterize prospect setup workflows"
```

---

### Task 3: Validate the frontend contract baseline and publish the PR

**Files:**
- Verify only: `apps/web/src/components/workspace/ProspectPromptBuilder.tsx`
- Verify only: `apps/web/src/components/workspace/ProspectPromptBuilder.state.ts`
- Verify only: added and modified test files

**Interfaces:**
- Consumes: Tasks 1 and 2 test coverage.
- Produces: validation evidence and a one-finding ARCH-001 PR with coverage map, risks, rollback, and residual gaps.

- [ ] **Step 1: Run frontend type and lint gates**

```bash
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run lint
```

Expected: both commands exit 0. Report pre-existing or environment failures by exact command and message.

- [ ] **Step 2: Run the broader frontend unit suite if feasible**

```bash
pnpm --dir apps/web run test
```

Expected: all frontend unit/component tests pass. If runtime or resource limits prevent completion, retain the focused passing evidence and record the residual risk.

- [ ] **Step 3: Review scope and diff hygiene**

```bash
git diff origin/main...HEAD --check
git diff --name-only origin/main...HEAD
git status --short --branch
```

Expected changed files:

```text
apps/web/src/components/ProspectSetup.behavior.test.tsx
apps/web/src/components/workspace/ProspectPromptBuilder.state.test.ts
docs/superpowers/plans/2026-07-16-arch-001-prospect-builder-characterization.md
docs/superpowers/specs/2026-07-16-arch-001-prospect-builder-characterization-design.md
```

No production, lockfile, generated, contract, migration, or snapshot files may change.

- [ ] **Step 4: Push and open the one-finding PR**

Push `audit/arch-001c-prospect-builder-characterization` and create an ARCH-001 PR containing:

- finding ID and current hotspot evidence;
- files inspected and changed;
- exact pass/warning/fail validation results;
- the coverage map from the design spec;
- confirmation that production behavior and public contracts are unchanged;
- any ambiguous behavior discovered as a separate follow-up, not a fix;
- rollback by reverting test commits;
- residual gaps, including any validation blocked by missing pnpm dependencies.
