import { useMemo } from "react";
import { useStakeholdersData } from "@/features/intelligence-workspace/tabs/_shared/useWorkspaceData";
import { useTruths } from "@/hooks/useGroundTruthGovernance";
import { useROICalculations } from "@/hooks/useROICalculator";
import type { ValueCaseArtifactsInput } from "@/hooks/useValueCaseArtifacts";

export interface ValueCaseInputProvenance {
  source:
    | "workspace_stakeholder"
    | "l5_truth"
    | "roi_calculation"
    | "workspace_tab"
    | "manual";
  id?: string;
}

export interface ValueCaseGenerationInputsResult {
  draft: ValueCaseArtifactsInput;
  provenance: Record<keyof ValueCaseArtifactsInput, ValueCaseInputProvenance[]>;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isReady: boolean;
}

function formatThreeYearValue(npv: number): string {
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

export function useValueCaseGenerationInputs(
  accountId: string,
  accountName: string,
  caseId: string | null
): ValueCaseGenerationInputsResult {
  const stakeholdersQuery = useStakeholdersData(caseId);
  const validatedTruthsQuery = useTruths(
    { status: "validated", applies_to_opportunity: accountId },
    { enabled: Boolean(accountId) }
  );
  const disputedTruthsQuery = useTruths(
    { status: "disputed", applies_to_opportunity: accountId },
    { enabled: Boolean(accountId) }
  );
  const roiQuery = useROICalculations({ account_id: accountId });

  const stakeholders = stakeholdersQuery.items ?? [];
  const validatedTruths = validatedTruthsQuery.data?.items ?? [];
  const disputedTruths = disputedTruthsQuery.data?.items ?? [];
  const roiCalculations = roiQuery.data?.calculations ?? [];

  const latestROI = roiCalculations[0] ?? null;

  const isLoading =
    stakeholdersQuery.isLoading ||
    validatedTruthsQuery.isLoading ||
    disputedTruthsQuery.isLoading ||
    roiQuery.isLoading;

  const isError =
    stakeholdersQuery.isError ||
    validatedTruthsQuery.isError ||
    disputedTruthsQuery.isError ||
    roiQuery.isError;

  const error = (stakeholdersQuery.error ??
    validatedTruthsQuery.error ??
    disputedTruthsQuery.error ??
    roiQuery.error) as Error | null;

  return useMemo(() => {
    const selectedStakeholders = stakeholders.slice(0, 5);
    const selectedEvidence = validatedTruths.slice(0, 5);
    const selectedRisks = disputedTruths.slice(0, 5);

    const draft: ValueCaseArtifactsInput = {
      account_id: accountId,
      account_name: accountName,
      stakeholders: selectedStakeholders.map(s => s.name),
      accepted_evidence: selectedEvidence.map(t => t.claim),
      scenario_assumptions: [],
      roi_metrics: latestROI
        ? {
            three_year_value: formatThreeYearValue(latestROI.npv),
            roi: `${latestROI.total_roi_pct.toFixed(0)}%`,
            payback: `${latestROI.payback_months} months`,
          }
        : { three_year_value: "", roi: "", payback: "" },
      risk_notes: selectedRisks.map(t => t.claim),
    };

    const provenance: Record<
      keyof ValueCaseArtifactsInput,
      ValueCaseInputProvenance[]
    > = {
      account_id: [{ source: "manual" }],
      account_name: [{ source: "manual" }],
      stakeholders: selectedStakeholders.map(s => ({
        source: "workspace_stakeholder",
        id: s.id,
      })),
      accepted_evidence: selectedEvidence.map(t => ({
        source: "l5_truth",
        id: t.id,
      })),
      scenario_assumptions: [{ source: "manual" }],
      roi_metrics: latestROI
        ? [{ source: "roi_calculation", id: latestROI.id }]
        : [],
      risk_notes: selectedRisks.map(t => ({
        source: "l5_truth",
        id: t.id,
      })),
    };

    return {
      draft,
      provenance,
      isLoading,
      isError,
      error,
      isReady: !isLoading && !isError,
    };
  }, [
    accountId,
    accountName,
    stakeholders,
    validatedTruths,
    disputedTruths,
    latestROI,
    isLoading,
    isError,
    error,
  ]);
}
