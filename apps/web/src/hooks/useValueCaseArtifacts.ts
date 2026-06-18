import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch, apiPost } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { useGenerateNarrative } from "./useNarratives";

export interface ValueCaseArtifactsInput {
  account_id: string;
  account_name: string;
  stakeholders: string[];
  accepted_evidence: string[];
  scenario_assumptions: string[];
  roi_metrics: {
    three_year_value: string;
    roi: string;
    payback: string;
  };
  risk_notes: string[];
}

export interface ValueCaseSection {
  id: string;
  type: string;
  title: string;
  content: string;
  order?: number;
}

export interface ValueCaseStakeholderFraming {
  persona: string;
  priorities?: string[];
  pains?: string[];
  decision_role?: string | null;
}

export interface ValueCaseContent {
  inputs: ValueCaseArtifactsInput;
  selected_scenario_id?: string | null;
  sections: ValueCaseSection[];
  assumption_ids: string[];
  evidence_ids: string[];
  stakeholder_framing: ValueCaseStakeholderFraming[];
  claim_ids: string[];
  roi_snapshot?: Record<string, unknown> | null;
}

export interface ValueCaseArtifactVersion {
  id: string;
  account_id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  status: string;
  inputs: ValueCaseArtifactsInput;
  narrative: {
    id: string;
    title: string;
    sections: ValueCaseSection[];
    created_at: string;
    updated_at: string;
  };
  business_case: {
    summary: string;
    metrics: ValueCaseArtifactsInput["roi_metrics"];
    risks: string[];
  };
  value_case?: ValueCaseContent;
}

interface ApiBusinessCase {
  id: string;
  account_id: string;
  title: string;
  status: string;
  audit: {
    created_at: string;
    updated_at: string;
  };
  executive_summary?: string;
  value_narrative?: string;
  value_case?: ValueCaseContent;
  assumptions?: string[];
  risks?: string[];
}

function apiCaseToArtifactVersion(
  apiCase: ApiBusinessCase
): ValueCaseArtifactVersion {
  const vc = apiCase.value_case;
  const inputs = vc?.inputs ?? {
    account_id: apiCase.account_id,
    account_name: "",
    stakeholders: [],
    accepted_evidence: [],
    scenario_assumptions: [],
    roi_metrics: { three_year_value: "", roi: "", payback: "" },
    risk_notes: apiCase.risks ?? [],
  };
  return {
    id: apiCase.id,
    account_id: apiCase.account_id,
    // The API gateway does not yet version value-case artifacts, so the UI
    // treats each saved artifact as version 1 until a version field is added.
    version: 1,
    created_at: apiCase.audit.created_at,
    updated_at: apiCase.audit.updated_at,
    title: apiCase.title,
    status: apiCase.status,
    inputs,
    narrative: {
      id: apiCase.id,
      title: apiCase.title,
      sections: vc?.sections ?? [],
      created_at: apiCase.audit.created_at,
      updated_at: apiCase.audit.updated_at,
    },
    business_case: {
      summary: apiCase.executive_summary ?? "",
      metrics: inputs.roi_metrics,
      risks: apiCase.risks ?? [],
    },
    value_case: vc,
  };
}

export function useValueCaseArtifacts(accountId: string | null) {
  const queryClient = useQueryClient();
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null
  );
  const generateNarrative = useGenerateNarrative();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: accountId ? QK.valueCases.account(accountId) : QK.valueCases.all,
    queryFn: async () => {
      if (!accountId) return [];
      const response = await apiGet<ApiBusinessCase[]>(
        "api",
        `/accounts/${encodeURIComponent(accountId)}/value-cases`
      );
      const items = Array.isArray(response.data) ? response.data : [];
      return items.map(apiCaseToArtifactVersion);
    },
    enabled: Boolean(accountId),
  });

  const selectedVersion = useMemo(() => {
    const versions = data ?? [];
    if (!versions.length) return null;
    if (!selectedVersionId) return versions[versions.length - 1] ?? null;
    return versions.find(item => item.id === selectedVersionId) ?? null;
  }, [data, selectedVersionId]);

  const generateArtifact = useMutation({
    mutationFn: async (input: ValueCaseArtifactsInput) => {
      const narrative = await generateNarrative.mutateAsync({
        account_id: input.account_id,
        title: `Value case narrative — ${input.account_name}`,
        audience: "evaluation_committee",
        tone: "financial",
        sections: [
          "executive_summary",
          "stakeholder_mapping",
          "roi_overview",
          "risk_and_mitigation",
        ],
      });

      const content: ValueCaseContent = {
        inputs: input,
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
        stakeholder_framing: input.stakeholders.map(persona => ({ persona })),
        claim_ids: [],
        roi_snapshot: null,
      };

      const response = await apiPost<ApiBusinessCase>(
        "api",
        `/accounts/${encodeURIComponent(input.account_id)}/value-case`,
        {
          title: `Value Case — ${input.account_name}`,
          value_case: content,
        }
      );
      return apiCaseToArtifactVersion(response.data);
    },
    onSuccess: artifact => {
      setSelectedVersionId(artifact.id);
      queryClient.invalidateQueries({
        queryKey: QK.valueCases.account(artifact.account_id),
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
      if (!accountId)
        throw new Error("Account ID is required to update a value case");
      const response = await apiPatch<ApiBusinessCase>(
        "api",
        `/accounts/${encodeURIComponent(accountId)}/value-cases/${encodeURIComponent(caseId)}`,
        { value_case: fields }
      );
      return apiCaseToArtifactVersion(response.data);
    },
    onSuccess: _artifact => {
      if (accountId) {
        queryClient.invalidateQueries({
          queryKey: QK.valueCases.account(accountId),
        });
      }
    },
  });

  const publishArtifact = useMutation({
    mutationFn: async (caseId: string) => {
      if (!accountId)
        throw new Error("Account ID is required to publish a value case");
      const response = await apiPost<ApiBusinessCase>(
        "api",
        `/accounts/${encodeURIComponent(accountId)}/value-cases/${encodeURIComponent(caseId)}/publish`,
        {}
      );
      return apiCaseToArtifactVersion(response.data);
    },
    onSuccess: _artifact => {
      if (accountId) {
        queryClient.invalidateQueries({
          queryKey: QK.valueCases.account(accountId),
        });
      }
    },
  });

  return {
    versions: data ?? [],
    isLoadingVersions: isLoading,
    versionsError: error,
    refetch,
    selectedVersion,
    setSelectedVersionId,
    generateArtifact,
    updateArtifact,
    publishArtifact,
  };
}
