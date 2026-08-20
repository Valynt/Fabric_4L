/**
 * Value Case Domain Models
 *
 * Immutable camelCase domain structures representing verified Value Case entities.
 */

export type ValueCaseScope = Readonly<{
  fabricTenantId: string;
  tenantSlug: string;
  accountId: string;
}>;

export interface ValueCaseStakeholderFraming {
  readonly persona: string;
  readonly role?: string;
  readonly priorities: readonly string[];
  readonly pains: readonly string[];
  readonly decisionRole: string | null;
  readonly valueMessage?: string;
}

export interface ValueCaseSection {
  readonly id: string;
  readonly type: string;
  readonly title: string;
  readonly content: string;
  readonly order: number;
}

export interface ValueCaseMetrics {
  readonly threeYearValue: string;
  readonly roi: string;
  readonly payback: string;
}

export interface ValueCaseInputs {
  readonly accountId?: string;
  readonly accountName?: string;
  readonly stakeholders: readonly string[];
  readonly acceptedEvidence: readonly string[];
  readonly scenarioAssumptions: readonly string[];
  readonly roiMetrics: ValueCaseMetrics;
  readonly riskNotes: readonly string[];
}

export interface ValueCaseNarrative {
  readonly id: string;
  readonly title: string;
  readonly sections: readonly ValueCaseSection[];
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface ValueCaseBusinessCase {
  readonly summary: string;
  readonly metrics: ValueCaseMetrics;
  readonly risks: readonly string[];
}

export interface ValueCaseContent {
  readonly inputs: ValueCaseInputs;
  readonly selectedScenarioId: string | null;
  readonly sections: readonly ValueCaseSection[];
  readonly assumptionIds: readonly string[];
  readonly evidenceIds: readonly string[];
  readonly stakeholderFraming: readonly ValueCaseStakeholderFraming[];
  readonly claimIds: readonly string[];
  readonly roiSnapshot: Readonly<Record<string, unknown>> | null;
}

export interface ValueCaseArtifactVersion {
  readonly id: string;
  readonly accountId: string;
  readonly version: number;
  readonly createdAt: string;
  readonly updatedAt: string;
  readonly title: string;
  readonly status: "draft" | "published" | "archived" | string;
  readonly inputs: ValueCaseInputs;
  readonly narrative: ValueCaseNarrative;
  readonly businessCase: ValueCaseBusinessCase;
  readonly stakeholderFraming: ReadonlyArray<{
    readonly role: string;
    readonly priorities: readonly string[];
    readonly pains?: readonly string[];
    readonly decisionRole?: string | null;
    readonly valueMessage: string;
  }>;
  readonly valueCase?: ValueCaseContent;
}

export interface InputProvenance {
  readonly source:
    | "workspace_stakeholder"
    | "l5_truth"
    | "roi_calculation"
    | "workspace_tab"
    | "manual";
  readonly id?: string;
}

export interface SourceAvailability {
  readonly stakeholdersAvailable: boolean;
  readonly groundTruthAvailable: boolean;
  readonly roiAvailable: boolean;
  readonly partialSourcesMessage: string | null;
  readonly hasPartialFailures: boolean;
  readonly failedSources: readonly string[];
  readonly statusMessage: string | null;
}

export interface GenerationDraft {
  accountId: string;
  accountName: string;
  stakeholders: string[];
  acceptedEvidence: string[];
  scenarioAssumptions: string[];
  roiMetrics: {
    threeYearValue: string;
    roi: string;
    payback: string;
  };
  riskNotes: string[];
}

export type ValueCaseGenerationInputsDraft = Partial<GenerationDraft> & {
  stakeholders: string[];
  acceptedEvidence: string[];
  scenarioAssumptions: string[];
  roiMetrics: {
    threeYearValue: string;
    roi: string;
    payback: string;
  };
  riskNotes: string[];
};

export type ValueCaseInputProvenance = InputProvenance;

export interface ValueCaseInputProvenanceMap {
  readonly stakeholders?: readonly ValueCaseInputProvenance[];
  readonly acceptedEvidence?: readonly ValueCaseInputProvenance[];
  readonly scenarioAssumptions?: readonly ValueCaseInputProvenance[];
  readonly roiMetrics?: readonly ValueCaseInputProvenance[];
  readonly riskNotes?: readonly ValueCaseInputProvenance[];
}

export type ValueCaseInputAvailability = SourceAvailability;

export interface GenerationSubmissionSnapshot {
  readonly submissionScope: ValueCaseScope;
  readonly accountName: string;
  readonly draft: GenerationDraft;
  readonly stakeholders: readonly string[];
  readonly acceptedEvidence: readonly string[];
  readonly scenarioAssumptions: readonly string[];
  readonly roiMetrics: ValueCaseMetrics;
  readonly riskNotes: readonly string[];
  readonly capturedAt: string;
}
