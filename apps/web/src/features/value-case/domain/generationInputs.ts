/**
 * Deterministic Generation Inputs Aggregator
 *
 * Aggregates upstream workspace sources (stakeholders, truths, ROI) into a deterministic
 * generation draft with provenance tracking, stable ordering, deduplication, and source availability.
 */
import type {
  GenerationDraft,
  GenerationSubmissionSnapshot,
  InputProvenance,
  SourceAvailability,
  ValueCaseInputs,
  ValueCaseScope,
} from "./valueCaseModels";

export interface RawStakeholderItem {
  id?: string;
  name?: string;
  role?: string;
  created_at?: string;
  createdAt?: string;
}

export interface RawTruthItem {
  id?: string;
  claim?: string;
  status?: string;
  created_at?: string;
  createdAt?: string;
}

export interface RawROICalculation {
  id?: string;
  npv?: number;
  total_roi_pct?: number;
  payback_months?: number;
  created_at?: string;
  createdAt?: string;
}

export interface GenerationInputsSourceData {
  scope?: ValueCaseScope;
  accountId?: string;
  accountName?: string;
  stakeholders?: RawStakeholderItem[] | null;
  validatedTruths?: RawTruthItem[] | null;
  disputedTruths?: RawTruthItem[] | null;
  roiCalculation?: RawROICalculation | null;
  roiCalculations?: RawROICalculation[] | null;
  isStakeholdersLoading?: boolean;
  isStakeholdersError?: boolean;
  isTruthsLoading?: boolean;
  isTruthsError?: boolean;
  isRoiLoading?: boolean;
  isRoiError?: boolean;
}

export interface AggregatedGenerationInputs {
  draft: GenerationDraft;
  provenance: Record<keyof GenerationDraft, readonly InputProvenance[]>;
  availability: SourceAvailability;
  isReady: boolean;
}

export const TOP_LIMIT = 5;

export function formatThreeYearValue(npv: number): string {
  if (typeof npv !== "number" || isNaN(npv)) return "";
  const sign = npv < 0 ? "-" : "";
  const absNpv = Math.abs(npv);
  if (absNpv >= 1_000_000) {
    return `${sign}$${(absNpv / 1_000_000).toFixed(1)}M`;
  }
  if (absNpv >= 1_000) {
    return `${sign}$${(absNpv / 1_000).toFixed(1)}K`;
  }
  return `${sign}$${absNpv}`;
}

export function aggregateGenerationInputs(
  accountIdOrSources: string | GenerationInputsSourceData,
  maybeSources?: GenerationInputsSourceData
): AggregatedGenerationInputs {
  const sources: GenerationInputsSourceData =
    typeof accountIdOrSources === "string"
      ? maybeSources ?? { accountName: "" }
      : accountIdOrSources;

  const accountId =
    typeof accountIdOrSources === "string"
      ? accountIdOrSources
      : sources.scope?.accountId ?? sources.accountId ?? "";

  // 1. Stable sorting for stakeholders alphabetically by name, then id
  const rawStakeholders = sources.stakeholders ?? [];
  const sortedStakeholders = [...rawStakeholders].sort((a, b) => {
    const nameA = a.name?.trim() ?? "";
    const nameB = b.name?.trim() ?? "";
    const cmp = nameA.localeCompare(nameB, undefined, { sensitivity: "base" });
    if (cmp !== 0) return cmp;
    const idA = a.id ?? "";
    const idB = b.id ?? "";
    if (idA !== idB) return idA.localeCompare(idB);
    return nameA.localeCompare(nameB);
  });

  // Deduplicate by name preserving earliest provenance
  const seenStakeholderNames = new Set<string>();
  const uniqueStakeholders: Array<{ name: string; id?: string }> = [];
  for (const s of sortedStakeholders) {
    const name = s.name?.trim();
    if (name && !seenStakeholderNames.has(name.toLowerCase())) {
      seenStakeholderNames.add(name.toLowerCase());
      uniqueStakeholders.push({ name, id: s.id });
    }
  }
  const selectedStakeholders = uniqueStakeholders.slice(0, TOP_LIMIT);

  // 2. Stable sorting for validated truths by claim
  const rawValidatedTruths = sources.validatedTruths ?? [];
  const sortedValidatedTruths = [...rawValidatedTruths].sort((a, b) => {
    const claimA = a.claim?.trim() ?? "";
    const claimB = b.claim?.trim() ?? "";
    if (claimA !== claimB) return claimA.localeCompare(claimB);
    const idA = a.id ?? "";
    const idB = b.id ?? "";
    return idA.localeCompare(idB);
  });

  const seenEvidenceClaims = new Set<string>();
  const uniqueEvidence: Array<{ claim: string; id?: string }> = [];
  for (const t of sortedValidatedTruths) {
    const claim = t.claim?.trim();
    if (claim && !seenEvidenceClaims.has(claim.toLowerCase())) {
      seenEvidenceClaims.add(claim.toLowerCase());
      uniqueEvidence.push({ claim, id: t.id });
    }
  }
  const selectedEvidence = uniqueEvidence.slice(0, TOP_LIMIT);

  // 3. Stable sorting for disputed truths (risks) by claim
  const rawDisputedTruths = sources.disputedTruths ?? [];
  const sortedDisputedTruths = [...rawDisputedTruths].sort((a, b) => {
    const claimA = a.claim?.trim() ?? "";
    const claimB = b.claim?.trim() ?? "";
    if (claimA !== claimB) return claimA.localeCompare(claimB);
    const idA = a.id ?? "";
    const idB = b.id ?? "";
    return idA.localeCompare(idB);
  });

  const seenRiskClaims = new Set<string>();
  const uniqueRisks: Array<{ claim: string; id?: string }> = [];
  for (const t of sortedDisputedTruths) {
    const claim = t.claim?.trim();
    if (claim && !seenRiskClaims.has(claim.toLowerCase())) {
      seenRiskClaims.add(claim.toLowerCase());
      uniqueRisks.push({ claim, id: t.id });
    }
  }
  const selectedRisks = uniqueRisks.slice(0, TOP_LIMIT);

  // 4. ROI calculation
  const roi = sources.roiCalculation ?? sources.roiCalculations?.[0] ?? null;
  const roiMetrics = roi && typeof roi.npv === "number"
    ? {
        threeYearValue: formatThreeYearValue(roi.npv),
        roi: typeof roi.total_roi_pct === "number" ? `${roi.total_roi_pct.toFixed(0)}%` : "",
        payback: typeof roi.payback_months === "number" ? `${roi.payback_months} months` : "",
      }
    : { threeYearValue: "", roi: "", payback: "" };

  const draft: GenerationDraft = {
    accountId,
    accountName: sources.accountName || "",
    stakeholders: selectedStakeholders.map(s => s.name),
    acceptedEvidence: selectedEvidence.map(e => e.claim),
    scenarioAssumptions: [],
    roiMetrics,
    riskNotes: selectedRisks.map(r => r.claim),
  };

  const provenance: Record<keyof GenerationDraft, readonly InputProvenance[]> = {
    accountId: Object.freeze([{ source: "manual" }]),
    accountName: Object.freeze([{ source: "manual" }]),
    stakeholders: Object.freeze(
      selectedStakeholders.map(s => ({
        source: "workspace_stakeholder" as const,
        id: s.id,
      }))
    ),
    acceptedEvidence: Object.freeze(
      selectedEvidence.map(e => ({
        source: "l5_truth" as const,
        id: e.id,
      }))
    ),
    scenarioAssumptions: Object.freeze([{ source: "manual" }]),
    roiMetrics: Object.freeze(
      roi?.id ? [{ source: "roi_calculation" as const, id: roi.id }] : []
    ),
    riskNotes: Object.freeze(
      selectedRisks.map(r => ({
        source: "l5_truth" as const,
        id: r.id,
      }))
    ),
  };

  // 5. Source availability
  const stakeholdersAvailable = !sources.isStakeholdersError && !sources.isStakeholdersLoading;
  const groundTruthAvailable = !sources.isTruthsError && !sources.isTruthsLoading;
  const roiAvailable = !sources.isRoiError && !sources.isRoiLoading;

  const failedSources: string[] = [];
  if (sources.isStakeholdersError) failedSources.push("stakeholders");
  if (sources.isTruthsError) failedSources.push("truths");
  if (sources.isRoiError) failedSources.push("roi");

  const hasPartialFailures = failedSources.length > 0;
  const statusMessage = hasPartialFailures
    ? `Some workspace inputs could not be loaded: ${failedSources.join(", ")}. You can enter them manually.`
    : null;

  const partialSourcesMessage = statusMessage;

  const availability: SourceAvailability = Object.freeze({
    stakeholdersAvailable,
    groundTruthAvailable,
    roiAvailable,
    partialSourcesMessage,
    hasPartialFailures,
    failedSources: Object.freeze(failedSources),
    statusMessage,
  });

  const isLoading =
    Boolean(sources.isStakeholdersLoading) ||
    Boolean(sources.isTruthsLoading) ||
    Boolean(sources.isRoiLoading);

  return {
    draft,
    provenance,
    availability,
    isReady: !isLoading,
  };
}

export function createGenerationSubmissionSnapshot(
  draft: GenerationDraft,
  scope: ValueCaseScope,
  accountName?: string
): GenerationSubmissionSnapshot {
  const immutableDraft: GenerationDraft = Object.freeze({
    accountId: draft.accountId,
    accountName: draft.accountName,
    stakeholders: Object.freeze([...(draft.stakeholders || [])]) as unknown as string[],
    acceptedEvidence: Object.freeze([...(draft.acceptedEvidence || [])]) as unknown as string[],
    scenarioAssumptions: Object.freeze([...(draft.scenarioAssumptions || [])]) as unknown as string[],
    roiMetrics: Object.freeze({ ...draft.roiMetrics }),
    riskNotes: Object.freeze([...(draft.riskNotes || [])]) as unknown as string[],
  });

  return Object.freeze({
    submissionScope: Object.freeze({ ...scope }),
    accountName: accountName || draft.accountName || scope.accountId,
    draft: immutableDraft,
    stakeholders: Object.freeze([...(draft.stakeholders || [])]),
    acceptedEvidence: Object.freeze([...(draft.acceptedEvidence || [])]),
    scenarioAssumptions: Object.freeze([...(draft.scenarioAssumptions || [])]),
    roiMetrics: Object.freeze({ ...draft.roiMetrics }),
    riskNotes: Object.freeze([...(draft.riskNotes || [])]),
    capturedAt: new Date().toISOString(),
  });
}

export function createImmutableSubmissionSnapshot(
  draft: GenerationDraft
): ValueCaseInputs {
  return Object.freeze({
    accountId: draft.accountId,
    accountName: draft.accountName,
    stakeholders: Object.freeze([...draft.stakeholders]),
    acceptedEvidence: Object.freeze([...draft.acceptedEvidence]),
    scenarioAssumptions: Object.freeze([...draft.scenarioAssumptions]),
    roiMetrics: Object.freeze({ ...draft.roiMetrics }),
    riskNotes: Object.freeze([...draft.riskNotes]),
  });
}
