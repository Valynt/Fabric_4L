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

  it("applies prompt text and preserves detected compliance sensitivity", () => {
    const state = builderReducer(createState(), {
      type: "APPLY_PROMPT_TEXT",
      promptText: [
        "Company: Regulated Co",
        "Compliance sensitivity:",
        "- Regulated industry: Healthcare",
        "- Known requirements: HIPAA",
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
    expect(builderReducer(succeeded, { type: "CLEAR_MESSAGES" })).toMatchObject(
      {
        statusMessage: "",
        successMessage: "",
        errorMessage: "",
      }
    );
  });

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

  it("preserves public callback and payload type contracts", () => {
    expectTypeOf(buildPayload).returns.toEqualTypeOf<ProspectSetupPromptPayload>();
    expectTypeOf(resolveNavigationAccountId).returns.toEqualTypeOf<
      string | undefined
    >();
    expectTypeOf<NonNullable<ProspectPromptBuilderProps["onCreateSetup"]>>()
      .parameter(0)
      .toEqualTypeOf<ProspectSetupPromptPayload>();
    expectTypeOf<
      NonNullable<ProspectPromptBuilderProps["onNavigateToWorkspace"]>
    >().parameters.toEqualTypeOf<[path: string, accountId: string]>();
    expectTypeOf<CreateSetupResult>().toEqualTypeOf<
      { accountId: string } | void
    >();
    expectTypeOf<BuilderAction>().toMatchTypeOf<
      Parameters<typeof builderReducer>[1]
    >();
  });
});
