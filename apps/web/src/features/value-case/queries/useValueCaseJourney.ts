/**
 * useValueCaseJourney
 *
 * Feature hook orchestrating verified-scope authorization, isolated query caches,
 * deterministic generation input aggregation, and safe mutation reconciliation.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthorizationSnapshot } from "@/auth/AuthorizationProvider";
import { useStakeholdersData } from "@/features/intelligence-workspace/tabs/_shared/useWorkspaceData";
import { useTruths } from "@/hooks/useGroundTruthGovernance";
import { useROICalculations } from "@/hooks/useROICalculator";
import { useCanonicalCaseId } from "@/hooks/useWorkspaceCase";
import { useGenerateNarrative } from "@/hooks/useNarratives";
import {
  fetchAccountApi,
  fetchValueCasesApi,
  createValueCaseApi,
  updateValueCaseApi,
  publishValueCaseApi,
} from "../api/valueCaseApi";
import {
  adaptApiBusinessCaseToDomain,
  domainDraftToApiArtifactsInput,
} from "../domain/valueCaseAdapters";
import {
  aggregateGenerationInputs,
  createImmutableSubmissionSnapshot,
} from "../domain/generationInputs";
import type {
  GenerationDraft,
  ValueCaseArtifactVersion,
  ValueCaseContent,
  ValueCaseScope,
  ValueCaseGenerationInputsDraft,
  ValueCaseInputProvenanceMap,
  ValueCaseInputAvailability,
} from "../domain/valueCaseModels";
import {
  buildResultViewModel,
  buildVersionSummaryViewModels,
  buildVersionDiffViewModel,
  buildMetricCardViewModels,
} from "../presentation/valueCaseViewModels";
import { valueCaseKeys } from "./valueCaseKeys";
import type { ApiValueCaseContent, ValueCaseBoundaryError } from "../api/valueCaseSchemas";

export type ValueCaseJourneyState =
  | "resolving-identity"
  | "denied"
  | "expired"
  | "loading"
  | "empty"
  | "ready"
  | "boundary-error";

export function useValueCaseJourney(
  routeAccountId: string | undefined,
  fallbackAccountName = "Account"
) {
  const queryClient = useQueryClient();
  const authorization = useAuthorizationSnapshot();
  const generateNarrative = useGenerateNarrative();

  // 1. Verify Scope
  const verifiedScope: ValueCaseScope | null = useMemo(() => {
    if (authorization.status !== "verified") return null;
    const snapshot = authorization.snapshot;
    if (!routeAccountId) return null;

    // Route parameter must match verified account scope
    const isAccountScope =
      snapshot.accountScope.scopeType === "account" &&
      snapshot.accountScope.accountId === routeAccountId;

    if (!isAccountScope) return null;

    return Object.freeze({
      fabricTenantId: snapshot.tenant.fabricTenantId,
      tenantSlug: snapshot.tenant.tenantSlug ?? "",
      accountId: routeAccountId,
    });
  }, [authorization, routeAccountId]);

  const scopeKey = verifiedScope
    ? `${verifiedScope.fabricTenantId}:${verifiedScope.accountId}`
    : null;

  // Track active scope key to reset local presentation state on scope switch
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [liveAnnouncement, setLiveAnnouncement] = useState<string>("");
  const previousScopeKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (previousScopeKeyRef.current !== scopeKey) {
      previousScopeKeyRef.current = scopeKey;
      setSelectedVersionId(null);
      setLiveAnnouncement("");
    }
  }, [scopeKey]);

  // 2. Scoped Account Query
  const accountQuery = useQuery({
    queryKey: verifiedScope
      ? valueCaseKeys.account(verifiedScope)
      : ["value-case", "disabled-account"],
    queryFn: async () => {
      if (!verifiedScope) throw new Error("Verified scope is required");
      return fetchAccountApi(verifiedScope.accountId);
    },
    enabled: Boolean(verifiedScope),
    placeholderData: undefined,
    retry: false,
    staleTime: 30_000,
  });

  // 3. Scoped Value Case Versions Query
  const versionsQuery = useQuery({
    queryKey: verifiedScope
      ? valueCaseKeys.scope(verifiedScope)
      : ["value-case", "disabled-scope"],
    queryFn: async () => {
      if (!verifiedScope) return [];
      const apiCases = await fetchValueCasesApi(verifiedScope.accountId);
      return apiCases.map(apiCase =>
        adaptApiBusinessCaseToDomain(apiCase, verifiedScope)
      );
    },
    enabled: Boolean(verifiedScope),
    placeholderData: undefined,
    retry: false,
    staleTime: 10_000,
  });

  // 4. Upstream Generation Sources
  const { data: canonicalCaseId } = useCanonicalCaseId(
    verifiedScope?.accountId ?? null
  );

  const stakeholdersQuery = useStakeholdersData(canonicalCaseId ?? null);

  const validatedTruthsQuery = useTruths(
    { status: "validated", applies_to_opportunity: verifiedScope?.accountId },
    { enabled: Boolean(verifiedScope) }
  );

  const disputedTruthsQuery = useTruths(
    { status: "disputed", applies_to_opportunity: verifiedScope?.accountId },
    { enabled: Boolean(verifiedScope) }
  );

  const roiQuery = useROICalculations(
    verifiedScope ? { account_id: verifiedScope.accountId } : {}
  );

  // 5. Aggregate Generation Inputs
  const aggregatedInputs = useMemo(() => {
    if (!verifiedScope) return null;
    const stakeholders = (stakeholdersQuery.items ?? []).map(s => ({
      id: s.id,
      name: s.name,
      role: s.role,
    }));
    const validatedTruths = (validatedTruthsQuery.data?.items ?? []).map(t => ({
      id: t.id,
      claim: t.claim,
      status: t.status,
    }));
    const disputedTruths = (disputedTruthsQuery.data?.items ?? []).map(t => ({
      id: t.id,
      claim: t.claim,
      status: t.status,
    }));
    const roiCalcs = roiQuery.data?.calculations ?? [];
    const latestROI = roiCalcs[0] ?? null;

    return aggregateGenerationInputs(verifiedScope.accountId, {
      accountName: accountQuery.data?.name || fallbackAccountName,
      stakeholders,
      validatedTruths,
      disputedTruths,
      roiCalculation: latestROI
        ? {
            id: latestROI.id,
            npv: latestROI.npv,
            total_roi_pct: latestROI.total_roi_pct,
            payback_months: latestROI.payback_months,
          }
        : null,
      isStakeholdersLoading: stakeholdersQuery.isLoading,
      isStakeholdersError: stakeholdersQuery.isError,
      isTruthsLoading: validatedTruthsQuery.isLoading,
      isTruthsError: validatedTruthsQuery.isError,
      isRoiLoading: roiQuery.isLoading,
      isRoiError: roiQuery.isError,
    });
  }, [
    verifiedScope,
    accountQuery.data?.name,
    fallbackAccountName,
    stakeholdersQuery.items,
    stakeholdersQuery.isLoading,
    stakeholdersQuery.isError,
    validatedTruthsQuery.data?.items,
    validatedTruthsQuery.isLoading,
    validatedTruthsQuery.isError,
    disputedTruthsQuery.data?.items,
    disputedTruthsQuery.isLoading,
    disputedTruthsQuery.isError,
    roiQuery.data?.calculations,
    roiQuery.isLoading,
    roiQuery.isError,
  ]);

  // 6. Selected Version Selection
  const versions = versionsQuery.data ?? [];
  const selectedVersion = useMemo(() => {
    if (!versions.length) return null;
    if (!selectedVersionId) return versions[versions.length - 1] ?? null;
    return versions.find(item => item.id === selectedVersionId) ?? versions[versions.length - 1] ?? null;
  }, [versions, selectedVersionId]);

  const previousVersion = useMemo(() => {
    if (!selectedVersion) return null;
    const idx = versions.findIndex(item => item.id === selectedVersion.id);
    if (idx <= 0) return null;
    return versions[idx - 1] ?? null;
  }, [versions, selectedVersion]);

  // 7. Mutations with exact scope capture
  const generateArtifact = useMutation({
    mutationFn: async (draft: GenerationDraft | ValueCaseGenerationInputsDraft) => {
      if (!verifiedScope) throw new Error("Verified authorization scope is required");
      const submissionScope = { ...verifiedScope };
      const fullDraft: GenerationDraft = {
        accountId: draft.accountId || submissionScope.accountId,
        accountName: draft.accountName || accountQuery.data?.name || fallbackAccountName,
        stakeholders: draft.stakeholders ? [...draft.stakeholders] : [],
        acceptedEvidence: draft.acceptedEvidence ? [...draft.acceptedEvidence] : [],
        scenarioAssumptions: draft.scenarioAssumptions ? [...draft.scenarioAssumptions] : [],
        roiMetrics: {
          threeYearValue: draft.roiMetrics?.threeYearValue ?? "",
          roi: draft.roiMetrics?.roi ?? "",
          payback: draft.roiMetrics?.payback ?? "",
        },
        riskNotes: draft.riskNotes ? [...draft.riskNotes] : [],
      };
      const submissionSnapshot = createImmutableSubmissionSnapshot(fullDraft);

      const narrative = await generateNarrative.mutateAsync({
        account_id: submissionSnapshot.accountId || submissionScope.accountId,
        title: `Value case narrative — ${submissionSnapshot.accountName}`,
        audience: "evaluation_committee",
        tone: "financial",
        sections: [
          "executive_summary",
          "stakeholder_mapping",
          "roi_overview",
          "risk_and_mitigation",
        ],
      });

      const content: ApiValueCaseContent = {
        inputs: domainDraftToApiArtifactsInput(fullDraft),
        selected_scenario_id: null,
        sections: (narrative.sections ?? []).map((section, index) => ({
          id: `${narrative.id}-section-${index}`,
          type: section.section_type,
          title: section.title,
          content: section.summary,
          order: index,
        })),
        assumption_ids: [],
        evidence_ids: [],
        stakeholder_framing: submissionSnapshot.stakeholders.map(persona => ({ persona })),
        claim_ids: [],
        roi_snapshot: null,
      };

      const targetAccountId = submissionSnapshot.accountId || submissionScope.accountId;
      const apiResult = await createValueCaseApi(targetAccountId, {
        title: `Value Case — ${submissionSnapshot.accountName}`,
        value_case: content,
      });

      const domainResult = adaptApiBusinessCaseToDomain(apiResult, submissionScope);
      return { domainResult, submissionScope };
    },
    onSuccess: ({ domainResult, submissionScope }) => {
      // Reconcile exact scope cache
      queryClient.setQueryData<ValueCaseArtifactVersion[]>(
        valueCaseKeys.scope(submissionScope),
        prev => {
          const existing = prev ?? [];
          const filtered = existing.filter(item => item.id !== domainResult.id);
          return [...filtered, domainResult];
        }
      );

      // Only select if active scope still equals captured scope
      if (
        verifiedScope?.fabricTenantId === submissionScope.fabricTenantId &&
        verifiedScope?.accountId === submissionScope.accountId
      ) {
        setSelectedVersionId(domainResult.id);
        setLiveAnnouncement(`Value Case generated successfully: v${domainResult.version}`);
      }

      void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });
    },
  });

  const updateArtifact = useMutation({
    mutationFn: async ({
      caseId,
      fields,
    }: {
      caseId: string;
      fields: Partial<ValueCaseContent>;
    }) => {
      if (!verifiedScope) throw new Error("Verified authorization scope is required");
      const submissionScope = { ...verifiedScope };

      const apiResult = await updateValueCaseApi(
        submissionScope.accountId,
        caseId,
        { value_case: fields as unknown as Partial<ApiValueCaseContent> }
      );

      const domainResult = adaptApiBusinessCaseToDomain(apiResult, submissionScope);
      return { domainResult, submissionScope };
    },
    onSuccess: ({ domainResult, submissionScope }) => {
      queryClient.setQueryData<ValueCaseArtifactVersion[]>(
        valueCaseKeys.scope(submissionScope),
        prev => (prev ?? []).map(item => (item.id === domainResult.id ? domainResult : item))
      );
      void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });
    },
  });

  const publishArtifact = useMutation({
    mutationFn: async (caseId: string) => {
      if (!verifiedScope) throw new Error("Verified authorization scope is required");
      const submissionScope = { ...verifiedScope };

      const apiResult = await publishValueCaseApi(
        submissionScope.accountId,
        caseId
      );

      const domainResult = adaptApiBusinessCaseToDomain(apiResult, submissionScope);
      return { domainResult, submissionScope };
    },
    onSuccess: ({ domainResult, submissionScope }) => {
      queryClient.setQueryData<ValueCaseArtifactVersion[]>(
        valueCaseKeys.scope(submissionScope),
        prev => (prev ?? []).map(item => (item.id === domainResult.id ? domainResult : item))
      );
      if (
        verifiedScope?.fabricTenantId === submissionScope.fabricTenantId &&
        verifiedScope?.accountId === submissionScope.accountId
      ) {
        setLiveAnnouncement(`Value Case published successfully.`);
      }
      void queryClient.invalidateQueries({
        queryKey: valueCaseKeys.scope(submissionScope),
        exact: true,
      });
    },
  });

  // 8. Lifecycle State Resolution
  const lifecycleState: ValueCaseJourneyState = useMemo(() => {
    if (authorization.status === "loading") return "resolving-identity";
    if (authorization.status === "expired") return "expired";
    if (authorization.status === "denied" || !verifiedScope) return "denied";
    if (accountQuery.isLoading || versionsQuery.isLoading) return "loading";
    if (accountQuery.isError || versionsQuery.isError) return "boundary-error";
    if (!versions.length) return "empty";
    return "ready";
  }, [
    authorization.status,
    verifiedScope,
    accountQuery.isLoading,
    accountQuery.isError,
    versionsQuery.isLoading,
    versionsQuery.isError,
    versions.length,
  ]);

  // 9. Derived Presentation View Models
  const activeResultViewModel = useMemo(
    () => buildResultViewModel(selectedVersion),
    [selectedVersion]
  );

  const versionSummaries = useMemo(
    () => buildVersionSummaryViewModels(versions),
    [versions]
  );

  const versionDiff = useMemo(
    () => buildVersionDiffViewModel(selectedVersion, previousVersion),
    [selectedVersion, previousVersion]
  );

  const latestMetricsViewModels = useMemo(() => {
    if (selectedVersion) {
      return buildMetricCardViewModels(selectedVersion.businessCase.metrics);
    }
    return buildMetricCardViewModels(aggregatedInputs?.draft?.roiMetrics);
  }, [selectedVersion, aggregatedInputs?.draft?.roiMetrics]);

  const fallbackDraft: ValueCaseGenerationInputsDraft = useMemo(
    () => ({
      accountId: routeAccountId ?? "",
      accountName: accountQuery.data?.name || fallbackAccountName,
      stakeholders: [],
      acceptedEvidence: [],
      scenarioAssumptions: [],
      roiMetrics: { threeYearValue: "", roi: "", payback: "" },
      riskNotes: [],
    }),
    [routeAccountId, accountQuery.data?.name, fallbackAccountName]
  );

  const generationInputsDraft = aggregatedInputs?.draft ?? fallbackDraft;
  const inputProvenance: ValueCaseInputProvenanceMap = aggregatedInputs?.provenance ?? {
    stakeholders: [],
    acceptedEvidence: [],
    scenarioAssumptions: [],
    roiMetrics: [],
    riskNotes: [],
  };
  const inputAvailability: ValueCaseInputAvailability = aggregatedInputs?.availability ?? {
    hasPartialFailures: false,
    failedSources: [],
    statusMessage: null,
    stakeholdersAvailable: true,
    groundTruthAvailable: true,
    roiAvailable: true,
    partialSourcesMessage: null,
  };

  const isLoadingInputs = Boolean(
    stakeholdersQuery.isLoading ||
      validatedTruthsQuery.isLoading ||
      disputedTruthsQuery.isLoading ||
      roiQuery.isLoading
  );

  const inputsError = (stakeholdersQuery.error ||
    validatedTruthsQuery.error ||
    disputedTruthsQuery.error ||
    roiQuery.error) as ValueCaseBoundaryError | null;

  return {
    verifiedScope,
    lifecycleState,
    account: accountQuery.data ?? null,
    accountLoading: accountQuery.isLoading,
    versions,
    isLoadingVersions: versionsQuery.isLoading,
    isRefreshing: versionsQuery.isFetching && !versionsQuery.isLoading,
    versionsError: (versionsQuery.error ?? accountQuery.error) as Error | null,
    selectedVersion,
    selectedVersionId,
    previousVersion,
    setSelectedVersionId,
    aggregatedInputs,
    activeResultViewModel,
    versionSummaries,
    versionDiff,
    latestMetricsViewModels,
    generationInputsDraft,
    inputProvenance,
    inputAvailability,
    isLoadingInputs,
    inputsError,
    generateArtifact,
    updateArtifact,
    publishArtifact,
    isGenerating: generateArtifact.isPending,
    isPublishing: publishArtifact.isPending,
    generateError: generateArtifact.error as Error | null,
    publishError: publishArtifact.error as Error | null,
    lastMutationMessage: liveAnnouncement,
    liveAnnouncement,
    generateCase: (draft?: Partial<GenerationDraft>) => {
      const targetDraft = draft ? { ...generationInputsDraft, ...draft } : generationInputsDraft;
      return generateArtifact.mutateAsync(targetDraft);
    },
    publishCase: (caseId?: string) => {
      const targetCaseId = caseId || selectedVersion?.id;
      if (!targetCaseId) return Promise.reject(new Error("No case ID selected for publication"));
      return publishArtifact.mutateAsync(targetCaseId);
    },
    refetchVersions: () => versionsQuery.refetch(),
    refetch: () => {
      void accountQuery.refetch();
      void versionsQuery.refetch();
    },
  };
}
