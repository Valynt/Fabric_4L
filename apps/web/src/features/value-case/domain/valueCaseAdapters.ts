/**
 * Value Case Domain Adapters
 *
 * Maps transport DTOs to pure immutable domain entities and vice versa.
 */
import {
  ValueCaseBoundaryError,
  type ApiBusinessCase,
  type ApiValueCaseArtifactsInput,
  type ApiValueCaseContent,
  type ApiValueCaseSection,
  type ApiValueCaseStakeholderFraming,
} from "../api/valueCaseSchemas";
import type {
  ValueCaseArtifactVersion,
  ValueCaseContent,
  ValueCaseInputs,
  ValueCaseMetrics,
  ValueCaseNarrative,
  ValueCaseScope,
  ValueCaseSection,
  ValueCaseStakeholderFraming,
  GenerationDraft,
} from "./valueCaseModels";

// ── DTO to Domain Mappers ─────────────────────────────────────────────────────

export function adaptApiSectionToDomain(
  dto: ApiValueCaseSection,
  index = 0
): ValueCaseSection {
  return Object.freeze({
    id: dto.id || `section-${index}`,
    type: dto.type || "general",
    title: dto.title || "Section",
    content: dto.content || "",
    order: typeof dto.order === "number" ? dto.order : index,
  });
}

export function adaptApiStakeholderFramingToDomain(
  dto: ApiValueCaseStakeholderFraming
): ValueCaseStakeholderFraming {
  return Object.freeze({
    persona: dto.persona || "Stakeholder",
    priorities: Object.freeze(dto.priorities ? [...dto.priorities] : []),
    pains: Object.freeze(dto.pains ? [...dto.pains] : []),
    decisionRole: dto.decision_role ?? null,
  });
}

export function adaptApiInputsToDomain(
  dto?: ApiValueCaseArtifactsInput,
  fallbackAccountId = ""
): ValueCaseInputs {
  return Object.freeze({
    accountId: dto?.account_id ?? fallbackAccountId,
    accountName: dto?.account_name ?? "",
    stakeholders: Object.freeze(dto?.stakeholders ? [...dto.stakeholders] : []),
    acceptedEvidence: Object.freeze(
      dto?.accepted_evidence ? [...dto.accepted_evidence] : []
    ),
    scenarioAssumptions: Object.freeze(
      dto?.scenario_assumptions ? [...dto.scenario_assumptions] : []
    ),
    roiMetrics: Object.freeze({
      threeYearValue: dto?.roi_metrics?.three_year_value ?? "",
      roi: dto?.roi_metrics?.roi ?? "",
      payback: dto?.roi_metrics?.payback ?? "",
    }),
    riskNotes: Object.freeze(dto?.risk_notes ? [...dto.risk_notes] : []),
  });
}

export function adaptApiContentToDomain(
  dto: ApiValueCaseContent | undefined,
  fallbackAccountId: string
): ValueCaseContent {
  const inputs = adaptApiInputsToDomain(dto?.inputs, fallbackAccountId);
  const sections = (dto?.sections ?? []).map(adaptApiSectionToDomain);
  const stakeholderFraming = (dto?.stakeholder_framing ?? []).map(
    adaptApiStakeholderFramingToDomain
  );

  return Object.freeze({
    inputs,
    selectedScenarioId: dto?.selected_scenario_id ?? null,
    sections: Object.freeze(sections),
    assumptionIds: Object.freeze(
      dto?.assumption_ids ? [...dto.assumption_ids] : []
    ),
    evidenceIds: Object.freeze(
      dto?.evidence_ids ? [...dto.evidence_ids] : []
    ),
    stakeholderFraming: Object.freeze(stakeholderFraming),
    claimIds: Object.freeze(dto?.claim_ids ? [...dto.claim_ids] : []),
    roiSnapshot: dto?.roi_snapshot
      ? Object.freeze({ ...dto.roi_snapshot })
      : null,
  });
}

export function createVerifiedValueCaseScope(
  routeAccountId: string | undefined | null,
  authSnapshot: any
): ValueCaseScope | null {
  if (!routeAccountId || !authSnapshot) return null;

  // Standard AuthorizationResolution ({ status: "verified", snapshot: { tenant: { fabricTenantId }, accountScope: ... } })
  if (authSnapshot.status === "verified" && authSnapshot.snapshot) {
    const { snapshot } = authSnapshot;
    const isAccountScope =
      snapshot.accountScope &&
      snapshot.accountScope.scopeType === "account" &&
      snapshot.accountScope.accountId === routeAccountId;
    if (!isAccountScope) return null;

    return Object.freeze({
      fabricTenantId: snapshot.tenant.fabricTenantId,
      tenantSlug: snapshot.tenant.tenantSlug ?? "",
      accountId: routeAccountId,
    });
  }

  // Flat auth state mock ({ state: "authenticated", tenantId: "...", accountScope: { scopeType: "account", accountId: "..." } })
  if (
    (authSnapshot.state === "authenticated" || authSnapshot.status === "authenticated") &&
    authSnapshot.tenantId
  ) {
    const isAccountScope =
      authSnapshot.accountScope &&
      authSnapshot.accountScope.scopeType === "account" &&
      authSnapshot.accountScope.accountId === routeAccountId;
    if (!isAccountScope) return null;

    return Object.freeze({
      fabricTenantId: authSnapshot.tenantId,
      tenantSlug: authSnapshot.tenantSlug ?? "",
      accountId: routeAccountId,
    });
  }

  return null;
}

export function apiCaseToArtifactVersion(
  apiCase: ApiBusinessCase,
  versionNumberOrScope?: number | ValueCaseScope,
  expectedScope?: ValueCaseScope
): ValueCaseArtifactVersion {
  let versionNumber = 1;
  let targetScope: ValueCaseScope | undefined = expectedScope;

  if (typeof versionNumberOrScope === "number") {
    versionNumber = versionNumberOrScope;
  } else if (versionNumberOrScope && typeof versionNumberOrScope === "object") {
    targetScope = versionNumberOrScope;
    versionNumber = apiCase.version ?? 1;
  } else {
    versionNumber = apiCase.version ?? 1;
  }

  if (targetScope && apiCase.account_id !== targetScope.accountId) {
    throw new ValueCaseBoundaryError(
      `Account mismatch: expected ${targetScope.accountId}, received ${apiCase.account_id}`,
      "IDENTITY_MISMATCH"
    );
  }

  const valueCaseContent = apiCase.value_case
    ? adaptApiContentToDomain(apiCase.value_case, apiCase.account_id)
    : undefined;

  const inputs: ValueCaseInputs =
    valueCaseContent?.inputs ??
    adaptApiInputsToDomain(undefined, apiCase.account_id);

  const metrics: ValueCaseMetrics = Object.freeze({
    threeYearValue: inputs.roiMetrics.threeYearValue || "",
    roi: inputs.roiMetrics.roi || "",
    payback: inputs.roiMetrics.payback || "",
  });

  const narrative: ValueCaseNarrative = Object.freeze({
    id: apiCase.id,
    title: apiCase.title || "Value Case Narrative",
    sections: valueCaseContent?.sections ?? Object.freeze([]),
    createdAt: apiCase.audit.created_at,
    updatedAt: apiCase.audit.updated_at,
  });

  const businessCase = Object.freeze({
    summary: apiCase.executive_summary ?? "",
    metrics,
    risks: Object.freeze(apiCase.risks && apiCase.risks.length > 0 ? [...apiCase.risks] : inputs.riskNotes),
  });

  const stakeholderFraming = (valueCaseContent?.stakeholderFraming ?? []).map(
    sf => ({
      role: sf.persona,
      priorities: sf.priorities,
      pains: sf.pains,
      decisionRole: sf.decisionRole,
      valueMessage: sf.priorities.length > 0 ? `Priorities: ${sf.priorities.join(", ")}` : (sf.pains.join(", ") || ""),
    })
  );

  return Object.freeze({
    id: apiCase.id,
    accountId: apiCase.account_id,
    version: versionNumber,
    createdAt: apiCase.audit.created_at,
    updatedAt: apiCase.audit.updated_at,
    title: apiCase.title || "Value Case",
    status: apiCase.status || "draft",
    inputs,
    narrative,
    businessCase,
    stakeholderFraming: Object.freeze(stakeholderFraming),
    valueCase: valueCaseContent,
  });
}

export const adaptApiBusinessCaseToDomain = apiCaseToArtifactVersion;

// ── Domain to DTO Mappers ─────────────────────────────────────────────────────

export function domainDraftToApiInput(
  draft: any,
  scope?: ValueCaseScope,
  accountName?: string
): ApiValueCaseArtifactsInput {
  return {
    account_id: draft.accountId ?? scope?.accountId ?? "",
    account_name: draft.accountName ?? accountName ?? "",
    stakeholders: draft.stakeholders ? [...draft.stakeholders] : [],
    accepted_evidence: draft.acceptedEvidence ? [...draft.acceptedEvidence] : [],
    scenario_assumptions: draft.scenarioAssumptions ? [...draft.scenarioAssumptions] : [],
    roi_metrics: {
      three_year_value: draft.roiMetrics?.threeYearValue ?? "",
      roi: draft.roiMetrics?.roi ?? "",
      payback: draft.roiMetrics?.payback ?? "",
    },
    risk_notes: draft.riskNotes ? [...draft.riskNotes] : [],
  };
}

export const domainDraftToApiArtifactsInput = domainDraftToApiInput;

export function domainInputsToDraft(inputs: ValueCaseInputs): GenerationDraft {
  return {
    accountId: inputs.accountId ?? "",
    accountName: inputs.accountName ?? "",
    stakeholders: [...inputs.stakeholders],
    acceptedEvidence: [...inputs.acceptedEvidence],
    scenarioAssumptions: [...inputs.scenarioAssumptions],
    roiMetrics: {
      threeYearValue: inputs.roiMetrics.threeYearValue,
      roi: inputs.roiMetrics.roi,
      payback: inputs.roiMetrics.payback,
    },
    riskNotes: [...inputs.riskNotes],
  };
}
