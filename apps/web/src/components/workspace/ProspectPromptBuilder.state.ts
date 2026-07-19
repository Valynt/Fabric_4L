import {
  parsePromptText,
  type DeliverableType,
  type ProspectSetupDraft,
  type SectionKey,
  type Stakeholders,
} from "./promptParser";

export type PromptMode = "Fast" | "Balanced" | "Deep";
export type EnrichmentDepth = "light" | "standard" | "deep";

export type AttachmentItem = { id: string; name: string };
export type CreateSetupResult = { accountId: string } | void;

export type ProspectSetupPromptPayload = {
  companyName?: string;
  companyDomain?: string;
  industry?: string;
  accountContext?: string;
  buyingContext?: string;
  whyNow?: string;
  knownInitiative?: string;
  businessPain?: string[];
  currentFriction?: string[];
  desiredOutcomes?: string[];
  stakeholders?: Partial<Stakeholders>;
  sourceArtifacts?: AttachmentItem[];
  outputType: DeliverableType;
  desiredOutputs: DeliverableType[];
  mode: PromptMode;
  enrichmentDepth: EnrichmentDepth;
  useUploadedFiles: boolean;
  usePriorAccountContext: boolean;
  runWebEnrichment: boolean;
  complianceSensitive: boolean;
  deepResearch: boolean;
  freeformPrompt: string;
};

export type CompanyOption = {
  id: string;
  name: string;
  domain?: string;
  industry?: string;
  accountId?: string;
};

export type ActivityItem = {
  id: string;
  title: string;
  updatedAt: string;
  prompt: string;
};
export type AttachResult = void | null | AttachmentItem | AttachmentItem[];

export const MODE_OPTIONS: PromptMode[] = ["Fast", "Balanced", "Deep"];
export const MESSAGE_CLEAR_TIMEOUT_MS = 5000;

export const DELIVERABLE_OPTIONS: { label: string; value: DeliverableType }[] =
  [
    { label: "Account brief", value: "account_brief" },
    { label: "Discovery prep", value: "discovery_prep" },
    { label: "Value hypotheses", value: "value_hypotheses" },
    { label: "Executive summary", value: "executive_summary" },
  ];

export const ENRICHMENT_OPTIONS: { label: string; value: EnrichmentDepth }[] = [
  { label: "Light", value: "light" },
  { label: "Standard", value: "standard" },
  { label: "Deep", value: "deep" },
];

type DuplicateAccountErrorPayload = {
  error?: unknown;
  existing_account_id?: unknown;
  duplicate_candidates?: Array<{ name?: unknown; domain?: unknown }>;
  suggested_action?: unknown;
};

export function formatSubmitError(error: unknown): string {
  const maybeApiError = error as {
    statusCode?: unknown;
    responseData?: unknown;
  } | null;
  const responseData = maybeApiError?.responseData as
    | DuplicateAccountErrorPayload
    | undefined;
  const errorText =
    typeof responseData?.error === "string"
      ? responseData.error
      : error instanceof Error
        ? error.message
        : String(error);
  const isDuplicate =
    maybeApiError?.statusCode === 409 ||
    /duplicate|already exists|existing account/i.test(errorText);

  if (isDuplicate) {
    const candidate = responseData?.duplicate_candidates?.find(
      item => typeof item.name === "string"
    );
    const candidateName =
      typeof candidate?.name === "string"
        ? candidate.name
        : "an existing account";
    const action =
      responseData?.suggested_action === "merge"
        ? " Review and merge before launching."
        : "";
    return `Duplicate account detected for ${candidateName}.${action}`;
  }

  return "Unable to launch intelligence. Please review the input and try again.";
}

export const UI_BUTTON_STYLES = {
  pill: "h-10 rounded-2xl border border-border/60 bg-background px-4 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-foreground",
  icon: "h-10 w-10 rounded-2xl border border-transparent bg-transparent text-muted-foreground shadow-none transition-all hover:border-border/60 hover:bg-muted hover:text-foreground hover:shadow-sm",
  accentIcon:
    "h-10 w-10 rounded-2xl border border-transparent bg-transparent text-primary shadow-none transition-all hover:border-primary/30 hover:bg-primary/10 hover:text-primary hover:shadow-sm dark:text-primary dark:hover:border-primary/40 dark:hover:bg-primary/10 dark:hover:text-primary",
  option:
    "h-10 rounded-2xl border border-border/60 bg-background px-3 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-foreground",
  primary:
    "h-10 rounded-2xl bg-foreground px-4 text-sm font-medium text-background shadow-sm transition-opacity hover:opacity-90 disabled:pointer-events-none disabled:opacity-50",
  chip: "min-h-11 w-full justify-start rounded-2xl border border-border/60 bg-background px-3 py-3 text-left text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground",
  badge:
    "rounded-2xl border border-border/60 bg-muted/40 px-2.5 py-1 text-xs font-medium",
} as const;

const CORE_SECTIONS: SectionKey[] = [
  "company",
  "buyingContext",
  "stakeholders",
  "businessPain",
  "deliverable",
];

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

export type BuilderState = {
  draft: ProspectSetupDraft;
  promptText: string;
  visibleSections: Record<SectionKey, boolean>;
  mode: PromptMode;
  primaryDeliverable: DeliverableType;
  enrichmentDepth: EnrichmentDepth;
  useUploadedFiles: boolean;
  usePriorAccountContext: boolean;
  runWebEnrichment: boolean;
  complianceSensitive: boolean;
  attachments: AttachmentItem[];
  selectedCompany?: CompanyOption;
  isSubmitting: boolean;
  isRecording: boolean;
  searchOpen: boolean;
  statusMessage: string;
  successMessage: string;
  errorMessage: string;
};

export type BuilderAction =
  | { type: "APPLY_PROMPT_TEXT"; promptText: string }
  | { type: "SELECT_COMPANY"; company: CompanyOption }
  | { type: "SYNC_SELECTED_COMPANY"; company?: CompanyOption }
  | { type: "ENABLE_SECTION"; section: SectionKey }
  | {
      type: "SET_COMPANY_FIELD";
      field: "companyName" | "companyDomain";
      value: string;
    }
  | { type: "SET_MODE"; mode: PromptMode }
  | { type: "SET_PRIMARY_DELIVERABLE"; deliverable: DeliverableType }
  | { type: "SET_ENRICHMENT_DEPTH"; enrichmentDepth: EnrichmentDepth }
  | {
      type: "SET_FLAG";
      key:
        | "useUploadedFiles"
        | "usePriorAccountContext"
        | "runWebEnrichment"
        | "complianceSensitive";
      value: boolean;
    }
  | { type: "SET_SEARCH_OPEN"; open: boolean }
  | { type: "SET_RECORDING"; value: boolean }
  | {
      type: "ATTACHMENTS_ADDED";
      attachments: AttachmentItem[];
      statusMessage?: string;
    }
  | { type: "STRENGTHEN_PROMPT" }
  | { type: "ENABLE_DEEP_RESEARCH" }
  | { type: "RESTORE_ACTIVITY"; activity: ActivityItem }
  | { type: "START_SUBMIT" }
  | { type: "SUBMIT_SUCCESS"; message: string }
  | { type: "SUBMIT_ERROR"; message: string }
  | { type: "CLEAR_MESSAGES" };

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

export function createEmptyDraft(): ProspectSetupDraft {
  return {
    companyName: "",
    companyDomain: "",
    industry: "",
    buyingContext: "",
    whyNow: "",
    knownInitiative: "",
    stakeholders: {
      economicBuyer: "",
      champion: "",
      evaluator: "",
      compliance: "",
    },
    businessPain: [],
    currentFriction: [],
    desiredOutcomes: [],
    desiredOutputs: [],
    compliance: {
      regulatedIndustry: "",
      knownRequirements: [],
      securityReviewExpected: "",
    },
    researchFocus: [],
    notes: "",
  };
}

export function createEmptyVisibleSections(): Record<SectionKey, boolean> {
  return {
    company: false,
    buyingContext: false,
    stakeholders: false,
    businessPain: false,
    deliverable: false,
    compliance: false,
    researchFocus: false,
    notes: false,
  };
}

export function hasContent(value: string | string[]) {
  return Array.isArray(value)
    ? value.some(item => item.trim().length > 0)
    : value.trim().length > 0;
}

export function deliverableLabel(value: DeliverableType) {
  return (
    DELIVERABLE_OPTIONS.find(option => option.value === value)?.label ?? value
  );
}

export function serializeBulletSection(
  title: string,
  items: string[],
  placeholder = ""
) {
  const filteredItems = items.filter(item => item.trim().length > 0);
  const lines =
    filteredItems.length > 0
      ? filteredItems.map(item => `- ${item}`)
      : placeholder
        ? [`- ${placeholder}`]
        : ["-"];
  return `${title}:\n${lines.join("\n")}`;
}

export function serializeDraft(
  draft: ProspectSetupDraft,
  visibleSections: Record<SectionKey, boolean>,
  primaryDeliverable: DeliverableType
) {
  const sections: string[] = [];

  const showCompany =
    visibleSections.company ||
    hasContent(draft.companyName) ||
    hasContent(draft.companyDomain) ||
    hasContent(draft.industry);
  if (showCompany) {
    sections.push(
      [
        `Company: ${draft.companyName}`,
        `Website: ${draft.companyDomain}`,
        `Industry: ${draft.industry}`,
      ].join("\n")
    );
  }

  const showBuyingContext =
    visibleSections.buyingContext ||
    hasContent(draft.buyingContext) ||
    hasContent(draft.whyNow) ||
    hasContent(draft.knownInitiative);
  if (showBuyingContext) {
    sections.push(
      [
        `Buying context: ${draft.buyingContext}`,
        `Why this account now: ${draft.whyNow}`,
        `Known initiative or trigger: ${draft.knownInitiative}`,
      ].join("\n")
    );
  }

  const showStakeholders =
    visibleSections.stakeholders ||
    Object.values(draft.stakeholders).some(value => value.trim().length > 0);
  if (showStakeholders) {
    sections.push(
      [
        "Stakeholders:",
        `- Economic buyer: ${draft.stakeholders.economicBuyer}`,
        `- Business champion: ${draft.stakeholders.champion}`,
        `- Technical evaluator: ${draft.stakeholders.evaluator}`,
        `- Compliance / legal: ${draft.stakeholders.compliance}`,
      ].join("\n")
    );
  }

  const showBusinessPain =
    visibleSections.businessPain ||
    hasContent(draft.businessPain) ||
    hasContent(draft.currentFriction) ||
    hasContent(draft.desiredOutcomes);
  if (showBusinessPain) {
    sections.push(
      [
        serializeBulletSection(
          "Known or suspected business pains",
          draft.businessPain
        ),
        serializeBulletSection("Current friction", draft.currentFriction),
        serializeBulletSection(
          "Desired business outcome",
          draft.desiredOutcomes
        ),
      ].join("\n\n")
    );
  }

  const outputs =
    draft.desiredOutputs.length > 0
      ? draft.desiredOutputs
      : visibleSections.deliverable
        ? [primaryDeliverable]
        : [];
  const showDeliverable = visibleSections.deliverable || outputs.length > 0;
  if (showDeliverable) {
    sections.push(
      serializeBulletSection(
        "Desired output",
        outputs.map(item => deliverableLabel(item)),
        deliverableLabel(primaryDeliverable)
      )
    );
  }

  const showCompliance =
    visibleSections.compliance ||
    hasContent(draft.compliance.regulatedIndustry) ||
    hasContent(draft.compliance.knownRequirements) ||
    hasContent(draft.compliance.securityReviewExpected);
  if (showCompliance) {
    sections.push(
      [
        "Compliance sensitivity:",
        `- Regulated industry: ${draft.compliance.regulatedIndustry}`,
        `- Known requirements: ${draft.compliance.knownRequirements.join("; ")}`,
        `- Security / legal review expected: ${draft.compliance.securityReviewExpected}`,
      ].join("\n")
    );
  }

  const showResearchFocus =
    visibleSections.researchFocus || hasContent(draft.researchFocus);
  if (showResearchFocus) {
    sections.push(
      serializeBulletSection(
        "Research focus",
        draft.researchFocus,
        "Company overview and current priorities"
      )
    );
  }

  const showNotes = visibleSections.notes || hasContent(draft.notes);
  if (showNotes) {
    sections.push(`Additional notes:\n${draft.notes}`.trim());
  }

  return sections.join("\n\n").trim();
}

export function buildStrengthenedState(state: BuilderState): BuilderState {
  const visibleSections = { ...state.visibleSections };
  for (const section of CORE_SECTIONS) visibleSections[section] = true;
  const nextDraft =
    state.draft.desiredOutputs.length === 0
      ? { ...state.draft, desiredOutputs: [state.primaryDeliverable] }
      : state.draft;
  return {
    ...state,
    draft: nextDraft,
    visibleSections,
    promptText: serializeDraft(
      nextDraft,
      visibleSections,
      state.primaryDeliverable
    ),
    statusMessage: "Prompt strengthened with missing value case sections.",
    successMessage: "",
    errorMessage: "",
  };
}

export function enableDeepResearchState(state: BuilderState): BuilderState {
  const visibleSections = { ...state.visibleSections, researchFocus: true };
  const nextDraft: ProspectSetupDraft = {
    ...state.draft,
    researchFocus:
      state.draft.researchFocus.length > 0
        ? state.draft.researchFocus
        : [
            "Company overview and current priorities",
            "Likely stakeholders and buying committee",
            "Business pain signals",
            "Industry and compliance considerations",
            "Initial value hypotheses",
          ],
  };
  return {
    ...state,
    draft: nextDraft,
    visibleSections,
    mode: "Deep",
    enrichmentDepth: "deep",
    promptText: serializeDraft(
      nextDraft,
      visibleSections,
      state.primaryDeliverable
    ),
    statusMessage:
      "Deep research enabled. Research focus added to the analysis.",
    successMessage: "",
    errorMessage: "",
  };
}

export function builderReducer(
  state: BuilderState,
  action: BuilderAction
): BuilderState {
  switch (action.type) {
    case "APPLY_PROMPT_TEXT": {
      const parsed = parsePromptText(action.promptText);
      return {
        ...state,
        draft: parsed.draft,
        visibleSections: parsed.visibleSections,
        promptText: action.promptText,
        complianceSensitive:
          state.complianceSensitive ||
          Boolean(
            parsed.visibleSections.compliance ||
            parsed.draft.compliance.regulatedIndustry ||
            parsed.draft.compliance.knownRequirements.length ||
            parsed.draft.compliance.securityReviewExpected
          ),
        successMessage: "",
        errorMessage: "",
      };
    }
    case "SELECT_COMPANY": {
      const nextDraft: ProspectSetupDraft = {
        ...state.draft,
        companyName: action.company.name,
        companyDomain: action.company.domain ?? state.draft.companyDomain,
        industry: action.company.industry ?? state.draft.industry,
      };
      const visibleSections = { ...state.visibleSections, company: true };
      return {
        ...state,
        draft: nextDraft,
        visibleSections,
        selectedCompany: action.company,
        searchOpen: false,
        promptText: serializeDraft(
          nextDraft,
          visibleSections,
          state.primaryDeliverable
        ),
        statusMessage: `${action.company.name} added to the value case.`,
        successMessage: "",
        errorMessage: "",
      };
    }
    case "SYNC_SELECTED_COMPANY":
      return { ...state, selectedCompany: action.company };
    case "ENABLE_SECTION": {
      const visibleSections = {
        ...state.visibleSections,
        [action.section]: true,
      };
      let nextDraft = state.draft;
      if (
        action.section === "deliverable" &&
        nextDraft.desiredOutputs.length === 0
      ) {
        nextDraft = {
          ...nextDraft,
          desiredOutputs: [state.primaryDeliverable],
        };
      }
      return {
        ...state,
        draft: nextDraft,
        visibleSections,
        promptText: serializeDraft(
          nextDraft,
          visibleSections,
          state.primaryDeliverable
        ),
        statusMessage: `${sectionTitle(action.section)} added to the prompt.`,
        successMessage: "",
        errorMessage: "",
      };
    }
    case "SET_COMPANY_FIELD": {
      const nextDraft: ProspectSetupDraft = {
        ...state.draft,
        [action.field]: action.value,
      };
      const visibleSections = { ...state.visibleSections, company: true };
      return {
        ...state,
        draft: nextDraft,
        visibleSections,
        selectedCompany: undefined,
        promptText: serializeDraft(
          nextDraft,
          visibleSections,
          state.primaryDeliverable
        ),
        successMessage: "",
        errorMessage: "",
      };
    }
    case "SET_MODE":
      return {
        ...state,
        mode: action.mode,
        statusMessage: `${action.mode} analysis depth selected.`,
        successMessage: "",
        errorMessage: "",
      };
    case "SET_PRIMARY_DELIVERABLE": {
      const desiredOutputs = state.draft.desiredOutputs.includes(
        action.deliverable
      )
        ? state.draft.desiredOutputs
        : [action.deliverable, ...state.draft.desiredOutputs];
      const nextDraft = { ...state.draft, desiredOutputs };
      const nextVisibleSections = {
        ...state.visibleSections,
        deliverable: true,
      };
      return {
        ...state,
        primaryDeliverable: action.deliverable,
        draft: nextDraft,
        visibleSections: nextVisibleSections,
        promptText: serializeDraft(
          nextDraft,
          nextVisibleSections,
          action.deliverable
        ),
        statusMessage: `${deliverableLabel(action.deliverable)} selected as the primary output.`,
        successMessage: "",
        errorMessage: "",
      };
    }
    case "SET_ENRICHMENT_DEPTH":
      return {
        ...state,
        enrichmentDepth: action.enrichmentDepth,
        statusMessage: `${capitalize(action.enrichmentDepth)} enrichment depth selected.`,
        successMessage: "",
        errorMessage: "",
      };
    case "SET_FLAG":
      return {
        ...state,
        [action.key]: action.value,
        statusMessage: `${flagLabel(action.key)} ${action.value ? "enabled" : "disabled"}.`,
        successMessage: "",
        errorMessage: "",
      };
    case "SET_SEARCH_OPEN":
      return { ...state, searchOpen: action.open };
    case "SET_RECORDING":
      return {
        ...state,
        isRecording: action.value,
        statusMessage: action.value
          ? "Voice input started."
          : "Voice input stopped.",
        successMessage: "",
        errorMessage: "",
      };
    case "ATTACHMENTS_ADDED":
      return {
        ...state,
        attachments: [...state.attachments, ...action.attachments],
        statusMessage:
          action.statusMessage ??
          `${action.attachments.length} attachment${action.attachments.length > 1 ? "s" : ""} added.`,
        successMessage: "",
        errorMessage: "",
      };
    case "STRENGTHEN_PROMPT":
      return buildStrengthenedState(state);
    case "ENABLE_DEEP_RESEARCH":
      return enableDeepResearchState(state);
    case "RESTORE_ACTIVITY": {
      const parsed = parsePromptText(action.activity.prompt);
      return {
        ...state,
        draft: parsed.draft,
        visibleSections: parsed.visibleSections,
        promptText: action.activity.prompt,
        selectedCompany: undefined,
        statusMessage: `${action.activity.title} restored.`,
        successMessage: "",
        errorMessage: "",
      };
    }
    case "START_SUBMIT":
      return {
        ...state,
        isSubmitting: true,
        statusMessage: "Launching intelligence...",
        successMessage: "",
        errorMessage: "",
      };
    case "SUBMIT_SUCCESS":
      return {
        ...state,
        isSubmitting: false,
        statusMessage: "",
        successMessage: action.message,
        errorMessage: "",
      };
    case "SUBMIT_ERROR":
      return {
        ...state,
        isSubmitting: false,
        statusMessage: "",
        successMessage: "",
        errorMessage: action.message,
      };
    case "CLEAR_MESSAGES":
      return {
        ...state,
        statusMessage: "",
        successMessage: "",
        errorMessage: "",
      };
    default:
      return state;
  }
}

export function getInitialState(
  initialValue: string,
  initialCompany?: CompanyOption
): BuilderState {
  const hasInitialValue = initialValue.trim().length > 0;
  const parsed = hasInitialValue
    ? parsePromptText(initialValue)
    : {
        draft: createEmptyDraft(),
        visibleSections: createEmptyVisibleSections(),
      };

  const seededDraft = initialCompany
    ? {
        ...parsed.draft,
        companyName: parsed.draft.companyName || initialCompany.name,
        companyDomain:
          parsed.draft.companyDomain || initialCompany.domain || "",
        industry: parsed.draft.industry || initialCompany.industry || "",
      }
    : parsed.draft;

  const seededVisibleSections = initialCompany
    ? { ...parsed.visibleSections, company: true }
    : parsed.visibleSections;

  const primaryDeliverable = seededDraft.desiredOutputs[0] ?? "account_brief";
  const promptText = hasInitialValue
    ? initialValue.trim()
    : initialCompany
      ? serializeDraft(seededDraft, seededVisibleSections, primaryDeliverable)
      : "";

  return {
    draft: seededDraft,
    promptText,
    visibleSections: seededVisibleSections,
    mode: "Balanced",
    primaryDeliverable,
    enrichmentDepth: "standard",
    useUploadedFiles: true,
    usePriorAccountContext: true,
    runWebEnrichment: true,
    complianceSensitive:
      seededVisibleSections.compliance ||
      Boolean(
        seededDraft.compliance.regulatedIndustry ||
        seededDraft.compliance.knownRequirements.length ||
        seededDraft.compliance.securityReviewExpected
      ),
    attachments: [],
    selectedCompany: initialCompany,
    isSubmitting: false,
    isRecording: false,
    searchOpen: false,
    statusMessage: "",
    successMessage: "",
    errorMessage: "",
  };
}

export function flagLabel(
  key:
    | "useUploadedFiles"
    | "usePriorAccountContext"
    | "runWebEnrichment"
    | "complianceSensitive"
) {
  switch (key) {
    case "useUploadedFiles":
      return "Uploaded files";
    case "usePriorAccountContext":
      return "Prior account context";
    case "runWebEnrichment":
      return "Web enrichment";
    case "complianceSensitive":
      return "Compliance-sensitive mode";
    default:
      return key;
  }
}

export function sectionTitle(section: SectionKey) {
  switch (section) {
    case "company":
      return "Company details";
    case "buyingContext":
      return "Buying context";
    case "stakeholders":
      return "Stakeholders";
    case "businessPain":
      return "Business pain";
    case "deliverable":
      return "Deliverable";
    case "compliance":
      return "Compliance sensitivity";
    case "researchFocus":
      return "Research focus";
    case "notes":
      return "Additional notes";
    default:
      return section;
  }
}

export function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function createAttachmentItems(
  result: AttachResult,
  existingCount: number
): AttachmentItem[] {
  if (!result) {
    return [
      {
        id: `attachment-${existingCount + 1}`,
        name: `Attachment ${existingCount + 1}`,
      },
    ];
  }
  return Array.isArray(result) ? result : [result];
}

export function resolveNavigationAccountId(
  result: CreateSetupResult,
  selectedCompany?: CompanyOption
) {
  if (
    result &&
    typeof result === "object" &&
    "accountId" in result &&
    result.accountId
  ) {
    return result.accountId;
  }
  return selectedCompany?.accountId;
}

export function buildPayload(state: BuilderState): ProspectSetupPromptPayload {
  const accountContext =
    [state.draft.buyingContext, state.draft.whyNow]
      .filter(Boolean)
      .join(" | ") || undefined;
  const stakeholders = Object.fromEntries(
    Object.entries(state.draft.stakeholders).filter(
      ([, value]) => value.trim().length > 0
    )
  ) as Partial<Stakeholders>;

  return {
    companyName: state.draft.companyName || undefined,
    companyDomain: state.draft.companyDomain || undefined,
    industry: state.draft.industry || undefined,
    accountContext,
    buyingContext: state.draft.buyingContext || undefined,
    whyNow: state.draft.whyNow || undefined,
    knownInitiative: state.draft.knownInitiative || undefined,
    businessPain: state.draft.businessPain,
    currentFriction: state.draft.currentFriction,
    desiredOutcomes: state.draft.desiredOutcomes,
    stakeholders:
      Object.keys(stakeholders).length > 0 ? stakeholders : undefined,
    sourceArtifacts: state.attachments,
    outputType: state.primaryDeliverable,
    desiredOutputs:
      state.draft.desiredOutputs.length > 0
        ? state.draft.desiredOutputs
        : [state.primaryDeliverable],
    mode: state.mode,
    enrichmentDepth: state.enrichmentDepth,
    useUploadedFiles: state.useUploadedFiles,
    usePriorAccountContext: state.usePriorAccountContext,
    runWebEnrichment: state.runWebEnrichment,
    complianceSensitive: state.complianceSensitive,
    deepResearch: state.mode === "Deep" || state.enrichmentDepth === "deep",
    freeformPrompt: state.promptText.trim(),
  };
}

export function hasMinimumContext(state: BuilderState) {
  return Boolean(
    state.draft.companyName ||
    state.draft.companyDomain ||
    state.attachments.length > 0
  );
}

export function canSubmit(state: BuilderState) {
  return state.promptText.trim().length > 12 || hasMinimumContext(state);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Validation
// ═══════════════════════════════════════════════════════════════════════════════

export type ValidationIssue = {
  id: string;
  message: string;
  resolved: boolean;
  priority: "required" | "recommended";
};

export function getValidationIssues(state: BuilderState): ValidationIssue[] {
  const hasText = state.promptText.trim().length > 12;
  const hasCompany = Boolean(
    state.draft.companyName || state.draft.companyDomain
  );
  const hasAttachment = state.attachments.length > 0;
  const hasBuyingContext = Boolean(
    state.draft.buyingContext || state.draft.whyNow
  );
  const hasPain =
    state.draft.businessPain.length > 0 ||
    state.draft.currentFriction.length > 0;
  const hasDeliverable =
    state.draft.desiredOutputs.length > 0 || state.visibleSections.deliverable;

  return [
    {
      id: "identity",
      message:
        "Add a company name, domain, or attachment to identify the account",
      resolved: hasCompany || hasAttachment,
      priority: "required",
    },
    {
      id: "context",
      message: "Write at least a few sentences describing the context",
      resolved: hasText,
      priority: "required",
    },
    {
      id: "buyingContext",
      message: "Describe the buying context to improve relevance",
      resolved: hasBuyingContext,
      priority: "recommended",
    },
    {
      id: "pain",
      message: "Add business pains or friction points",
      resolved: hasPain,
      priority: "recommended",
    },
    {
      id: "deliverable",
      message: "Select a deliverable type",
      resolved: hasDeliverable,
      priority: "recommended",
    },
  ];
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sub-components
