import * as React from "react";
import {
  ArrowUp,
  Briefcase,
  Building2,
  CheckCircle2,
  Circle,
  FileText,
  History,
  Mic,
  Paperclip,
  Search,
  Settings2,
  Shield,
  Sparkles,
  Users,
  Wand2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { createFeatureLogger } from "@/lib/telemetry";
import type {
  DeliverableType,
  ProspectSetupDraft,
  SectionKey,
  Stakeholders,
} from "./promptParser";
import { DEFAULT_COMPANIES, DEFAULT_ACTIVITIES } from "@/lib/demoData";
import {
  MODE_OPTIONS,
  MESSAGE_CLEAR_TIMEOUT_MS,
  DELIVERABLE_OPTIONS,
  ENRICHMENT_OPTIONS,
  builderReducer,
  buildPayload,
  canSubmit,
  createAttachmentItems,
  deliverableLabel,
  enableDeepResearchState,
  flagLabel,
  formatSubmitError,
  getInitialState,
  getValidationIssues,
  hasContent,
  resolveNavigationAccountId,
  sectionTitle,
  serializeDraft,
  type ActivityItem,
  type AttachResult,
  type AttachmentItem,
  type BuilderAction,
  type BuilderState,
  type CompanyOption,
  type CreateSetupResult,
  type EnrichmentDepth,
  type ProspectSetupPromptPayload,
  type PromptMode,
  type ValidationIssue,
  UI_BUTTON_STYLES,
  hasMinimumContext,
} from "./ProspectPromptBuilder.state";

const log = createFeatureLogger("ProspectPromptBuilder");

export type { DeliverableType, ProspectSetupDraft, SectionKey, Stakeholders };
export type {
  ActivityItem,
  AttachmentItem,
  CompanyOption,
  CreateSetupResult,
  ProspectSetupPromptPayload,
};

export type ProspectPromptBuilderProps = {
  className?: string;
  initialValue?: string;
  initialCompany?: CompanyOption;
  companyOptions?: CompanyOption[];
  recentActivities?: ActivityItem[];
  onCreateSetup?: (
    payload: ProspectSetupPromptPayload
  ) => CreateSetupResult | Promise<CreateSetupResult>;
  onAttachContent?: () => AttachResult | Promise<AttachResult>;
  onOpenVoiceInput?: () => void;
  onNavigateToWorkspace?: (path: string, accountId: string) => void;
  /** Override the internal submitting state (e.g., from an API mutation). */
  isSubmitting?: boolean;
  /** Generate a custom workspace path for post-submit navigation. */
  getWorkspacePath?: (accountId: string) => string;
  /** Called when submission succeeds but no accountId is available for navigation. */
  onFallbackNavigation?: () => void;
  /** Called immediately before the API request so external state can be primed. */
  onBeforeSubmit?: (state: BuilderState) => void;
};

// ═══════════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════

const SettingsSwitch = React.memo(function SettingsSwitch({
  id,
  label,
  checked,
  onCheckedChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <Label
        htmlFor={id}
        className="cursor-pointer select-none text-sm font-normal"
      >
        {label}
      </Label>
      <Switch id={id} checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
});

const PromptSettingsPopover = React.memo(function PromptSettingsPopover({
  state,
  dispatch,
}: {
  state: BuilderState;
  dispatch: React.Dispatch<BuilderAction>;
}) {
  return (
    <Popover>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={cn(UI_BUTTON_STYLES.icon, "hover:bg-muted/80")}
              aria-label="Prompt settings"
            >
              <Settings2 className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent className="rounded-lg">
          Open analysis settings
        </TooltipContent>
      </Tooltip>
      <PopoverContent
        align="end"
        className="w-80 rounded-2xl border border-border/60 bg-popover p-4 shadow-lg"
      >
        <div className="flex flex-col gap-4">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Deliverable
            </p>
            <div className="grid grid-cols-2 gap-2">
              {DELIVERABLE_OPTIONS.map(option => (
                <Button
                  key={option.value}
                  type="button"
                  variant="outline"
                  onClick={() =>
                    dispatch({
                      type: "SET_PRIMARY_DELIVERABLE",
                      deliverable: option.value,
                    })
                  }
                  className={cn(
                    UI_BUTTON_STYLES.option,
                    "justify-start text-left",
                    state.primaryDeliverable === option.value &&
                      "border-foreground bg-accent text-foreground"
                  )}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Enrichment depth
            </p>
            <div className="grid grid-cols-3 gap-2">
              {ENRICHMENT_OPTIONS.map(option => (
                <Button
                  key={option.value}
                  type="button"
                  variant="outline"
                  onClick={() =>
                    dispatch({
                      type: "SET_ENRICHMENT_DEPTH",
                      enrichmentDepth: option.value,
                    })
                  }
                  className={cn(
                    UI_BUTTON_STYLES.option,
                    state.enrichmentDepth === option.value &&
                      "border-foreground bg-accent text-foreground"
                  )}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          <Separator />

          <div className="space-y-3">
            <SettingsSwitch
              id="uploaded-files"
              label="Use uploaded files"
              checked={state.useUploadedFiles}
              onCheckedChange={v =>
                dispatch({
                  type: "SET_FLAG",
                  key: "useUploadedFiles",
                  value: v,
                })
              }
            />
            <SettingsSwitch
              id="prior-context"
              label="Use prior account context"
              checked={state.usePriorAccountContext}
              onCheckedChange={v =>
                dispatch({
                  type: "SET_FLAG",
                  key: "usePriorAccountContext",
                  value: v,
                })
              }
            />
            <SettingsSwitch
              id="web-enrichment"
              label="Run web enrichment"
              checked={state.runWebEnrichment}
              onCheckedChange={v =>
                dispatch({
                  type: "SET_FLAG",
                  key: "runWebEnrichment",
                  value: v,
                })
              }
            />
            <SettingsSwitch
              id="compliance-sensitive"
              label="Compliance-sensitive mode"
              checked={state.complianceSensitive}
              onCheckedChange={v =>
                dispatch({
                  type: "SET_FLAG",
                  key: "complianceSensitive",
                  value: v,
                })
              }
            />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
});

const RecentActivityMenu = React.memo(function RecentActivityMenu({
  activities,
  onRestore,
}: {
  activities: ActivityItem[];
  onRestore: (a: ActivityItem) => void;
}) {
  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={cn(UI_BUTTON_STYLES.icon, "hover:bg-muted/80")}
              aria-label="Recent value cases"
            >
              <History className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent className="rounded-lg">
          Open recent value cases
        </TooltipContent>
      </Tooltip>
      <DropdownMenuContent
        align="end"
        className="w-80 rounded-2xl border border-border/60 bg-popover p-1 shadow-lg"
      >
        <DropdownMenuLabel className="text-xs uppercase tracking-wide text-muted-foreground">
          Recent value cases
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {activities.map(activity => (
          <DropdownMenuItem
            key={activity.id}
            onClick={() => onRestore(activity)}
            className="flex flex-col items-start gap-0.5 rounded-xl px-3 py-2.5"
          >
            <span className="text-sm font-medium">{activity.title}</span>
            <span className="text-xs text-muted-foreground">
              {activity.updatedAt}
            </span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
});

const StatusBanner = React.memo(function StatusBanner({
  successMessage,
  statusMessage,
  errorMessage,
}: Pick<BuilderState, "successMessage" | "statusMessage" | "errorMessage">) {
  if (!successMessage && !statusMessage && !errorMessage) return null;

  const tone = errorMessage ? "error" : successMessage ? "success" : "info";
  const message = errorMessage || successMessage || statusMessage;

  return (
    <div
      role={errorMessage ? "alert" : "status"}
      className={cn(
        "mx-5 mb-3 rounded-2xl border px-3 py-2 text-sm transition-all",
        tone === "error" &&
          "border-destructive/30 bg-destructive/10 text-destructive dark:text-destructive",
        tone === "success" &&
          "border-success/30 bg-success/10 text-success dark:text-success",
        tone === "info" && "border-border/60 bg-muted/40 text-foreground"
      )}
    >
      {message}
    </div>
  );
});

const ValidationChecklist = React.memo(function ValidationChecklist({
  issues,
}: {
  issues: ValidationIssue[];
}) {
  const unresolved = issues.filter(i => !i.resolved);
  if (unresolved.length === 0) return null;

  return (
    <div className="mx-5 mb-3 rounded-2xl border border-warning/20 bg-warning/5 px-3 py-2">
      <p className="text-xs font-medium text-warning dark:text-warning mb-1.5">
        Finish these to launch:
      </p>
      <ul className="space-y-1">
        {unresolved.map(issue => (
          <li
            key={issue.id}
            className="flex items-start gap-2 text-xs text-warning dark:text-warning"
          >
            <Circle className="h-3 w-3 mt-0.5 shrink-0 opacity-60" />
            <span>{issue.message}</span>
          </li>
        ))}
      </ul>
    </div>
  );
});

const PromptHeader = React.memo(function PromptHeader({
  mode,
  onModeChange,
  state,
  dispatch,
  recentActivities,
}: {
  mode: PromptMode;
  onModeChange: (mode: PromptMode) => void;
  state: BuilderState;
  dispatch: React.Dispatch<BuilderAction>;
  recentActivities: ActivityItem[];
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-2">
      <div className="flex min-w-0 items-center gap-2">
        <DropdownMenu>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className={UI_BUTTON_STYLES.pill}
                >
                  {mode}
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent className="rounded-lg">
              Choose analysis depth
            </TooltipContent>
          </Tooltip>
          <DropdownMenuContent
            align="start"
            className="rounded-2xl border border-border/60 bg-popover p-1 shadow-lg"
          >
            <DropdownMenuLabel className="text-xs uppercase tracking-wide text-muted-foreground">
              Analysis depth
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {MODE_OPTIONS.map(option => (
              <DropdownMenuItem
                key={option}
                onClick={() => onModeChange(option)}
                className="rounded-xl"
              >
                {option}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Badge
          variant="secondary"
          className="h-10 rounded-2xl border border-border/60 bg-muted/60 px-4 text-sm font-medium text-foreground shadow-sm"
        >
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          New Value Case
        </Badge>
      </div>

      <div className="flex items-center gap-1.5">
        <PromptSettingsPopover state={state} dispatch={dispatch} />
        <RecentActivityMenu
          activities={recentActivities}
          onRestore={activity =>
            dispatch({ type: "RESTORE_ACTIVITY", activity })
          }
        />
      </div>
    </div>
  );
});

const CompanySearchPopover = React.memo(function CompanySearchPopover({
  open,
  onOpenChange,
  companyOptions,
  onSelect,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  companyOptions: CompanyOption[];
  onSelect: (c: CompanyOption) => void;
}) {
  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <Tooltip>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={UI_BUTTON_STYLES.icon}
              aria-label="Search accounts"
            >
              <Search className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
        </TooltipTrigger>
        <TooltipContent className="rounded-lg">
          Search for a company or saved account
        </TooltipContent>
      </Tooltip>
      <PopoverContent
        align="start"
        side="top"
        className="w-[360px] rounded-2xl border border-border/60 bg-popover p-0 shadow-lg"
      >
        <Command className="rounded-2xl">
          <CommandInput
            placeholder="Search company, account, or domain..."
            className="h-11"
          />
          <CommandList className="max-h-72">
            <CommandEmpty>No matching accounts found.</CommandEmpty>
            {companyOptions.map(company => (
              <CommandItem
                key={company.id}
                value={`${company.name} ${company.domain ?? ""} ${company.industry ?? ""}`}
                onSelect={() => onSelect(company)}
                className="flex items-center gap-2 px-3 py-2.5"
              >
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-sm font-medium">
                    {company.name}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {[company.domain, company.industry]
                      .filter(Boolean)
                      .join(" • ")}
                  </span>
                </div>
              </CommandItem>
            ))}
            <CommandSeparator />
            <CommandItem
              onSelect={() =>
                onSelect({
                  id: "__manual__",
                  name: "",
                  domain: "",
                  industry: "",
                })
              }
              className="px-3 py-2.5"
            >
              <FileText className="mr-2 h-4 w-4 text-muted-foreground" />
              Insert company section
            </CommandItem>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
});

const SectionIcon = ({ section }: { section: SectionKey }) => {
  switch (section) {
    case "company":
      return <Building2 className="h-3.5 w-3.5" />;
    case "buyingContext":
      return <Briefcase className="h-3.5 w-3.5" />;
    case "stakeholders":
      return <Users className="h-3.5 w-3.5" />;
    case "businessPain":
      return <FileText className="h-3.5 w-3.5" />;
    case "deliverable":
      return <Wand2 className="h-3.5 w-3.5" />;
    case "compliance":
      return <Shield className="h-3.5 w-3.5" />;
    case "researchFocus":
      return <Search className="h-3.5 w-3.5" />;
    case "notes":
      return <FileText className="h-3.5 w-3.5" />;
  }
};

const ContextChips = React.memo(function ContextChips({
  state,
  dispatch,
}: {
  state: BuilderState;
  dispatch: React.Dispatch<BuilderAction>;
}) {
  const hidden = (Object.keys(state.visibleSections) as SectionKey[]).filter(
    k => !state.visibleSections[k]
  );
  if (hidden.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2 px-2">
      {hidden.map(section => (
        <Button
          key={section}
          type="button"
          variant="outline"
          size="sm"
          onClick={() => dispatch({ type: "ENABLE_SECTION", section })}
          className="h-8 gap-1.5 rounded-xl border border-dashed border-border/60 bg-transparent px-3 text-xs font-medium text-muted-foreground shadow-none transition-all hover:border-border hover:bg-muted/40 hover:text-foreground"
        >
          <SectionIcon section={section} />+ {sectionTitle(section)}
        </Button>
      ))}
    </div>
  );
});

const AttachmentPills = React.memo(function AttachmentPills({
  attachments,
}: {
  attachments: AttachmentItem[];
}) {
  if (attachments.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 px-2">
      {attachments.map(a => (
        <span
          key={a.id}
          className={cn(UI_BUTTON_STYLES.badge, "flex items-center gap-1")}
        >
          <Paperclip className="h-3 w-3" />
          {a.name}
        </span>
      ))}
    </div>
  );
});

const SuggestionsRail = React.memo(function SuggestionsRail({
  onEnableSection,
  onCompliance,
}: {
  onEnableSection: (section: SectionKey) => void;
  onCompliance: () => void;
}) {
  return (
    <div className="rounded-2xl border border-border/60 bg-muted/20 p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">
            Quick start inputs
          </p>
          <p className="text-xs text-muted-foreground">
            Start with any section below. All of the key setup inputs are
            visible here.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <ChipButton
          icon={Building2}
          label="Add company + website"
          onClick={() => onEnableSection("company")}
        />
        <ChipButton
          icon={Briefcase}
          label="Define buying context"
          onClick={() => onEnableSection("buyingContext")}
        />
        <ChipButton
          icon={Users}
          label="Add stakeholders"
          onClick={() => onEnableSection("stakeholders")}
        />
        <ChipButton
          icon={Briefcase}
          label="Describe business pain"
          onClick={() => onEnableSection("businessPain")}
        />
        <ChipButton
          icon={FileText}
          label="Choose deliverable"
          onClick={() => onEnableSection("deliverable")}
        />
        <ChipButton
          icon={Shield}
          label="Flag compliance sensitivity"
          onClick={onCompliance}
        />
      </div>
    </div>
  );
});

const PromptFooter = React.memo(function PromptFooter({
  state,
  dispatch,
  companyOptions,
  onAttachContent,
  onOpenVoiceInput,
  onSubmit,
  submitEnabled,
  isSubmitting,
  minimumContextAvailable,
}: {
  state: BuilderState;
  dispatch: React.Dispatch<BuilderAction>;
  companyOptions: CompanyOption[];
  onAttachContent?: () => AttachResult | Promise<AttachResult>;
  onOpenVoiceInput?: () => void;
  onSubmit: () => void;
  submitEnabled: boolean;
  isSubmitting: boolean;
  minimumContextAvailable: boolean;
}) {
  const handleAttach = async () => {
    try {
      const result = onAttachContent ? await onAttachContent() : null;
      const items = createAttachmentItems(result, state.attachments.length);
      dispatch({ type: "ATTACHMENTS_ADDED", attachments: items });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      log.error("Attach content failed", { error: errorMessage });
      dispatch({
        type: "SUBMIT_ERROR",
        message: "Unable to attach content. Please try again.",
      });
    }
  };

  const handleVoice = () => {
    onOpenVoiceInput?.();
    dispatch({ type: "SET_RECORDING", value: !state.isRecording });
  };

  return (
    <div className="flex items-center justify-between gap-3 border-t border-border/50 px-4 py-4">
      <div className="flex items-center gap-1">
        <CompanySearchPopover
          open={state.searchOpen}
          onOpenChange={o => dispatch({ type: "SET_SEARCH_OPEN", open: o })}
          companyOptions={companyOptions}
          onSelect={c => dispatch({ type: "SELECT_COMPANY", company: c })}
        />

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => void handleAttach()}
              className={UI_BUTTON_STYLES.icon}
              aria-label="Attach source material"
            >
              <Paperclip className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent className="rounded-lg">
            Attach files, notes, or source material
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => {
                  if (!minimumContextAvailable) return;
                  dispatch({ type: "ENABLE_DEEP_RESEARCH" });
                }}
                disabled={!minimumContextAvailable}
                className={cn(
                  minimumContextAvailable
                    ? UI_BUTTON_STYLES.accentIcon
                    : "h-10 w-10 rounded-2xl border border-transparent bg-transparent text-muted-foreground/50"
                )}
                aria-label="Run account enrichment"
              >
                <Sparkles className="h-4 w-4" />
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent className="rounded-lg">
            {minimumContextAvailable
              ? "Research the company, industry, and likely buying context"
              : "Add a company, website, or attachment before running research"}
          </TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={handleVoice}
              className={cn(
                UI_BUTTON_STYLES.icon,
                state.isRecording &&
                  "text-destructive dark:text-destructive hover:text-destructive dark:hover:text-destructive"
              )}
              aria-pressed={state.isRecording}
              aria-label={
                state.isRecording ? "Stop voice input" : "Start voice input"
              }
            >
              <Mic className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent className="rounded-lg">
            {state.isRecording ? "Stop dictation" : "Dictate the setup prompt"}
          </TooltipContent>
        </Tooltip>
      </div>

      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => dispatch({ type: "STRENGTHEN_PROMPT" })}
              className={UI_BUTTON_STYLES.accentIcon}
              aria-label="Strengthen setup prompt"
            >
              <Wand2 className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent className="rounded-lg">
            Improve prompt structure and fill missing setup sections
          </TooltipContent>
        </Tooltip>

        <Button
          type="submit"
          size="sm"
          disabled={!submitEnabled || isSubmitting}
          className={UI_BUTTON_STYLES.primary}
        >
          {isSubmitting ? "Launching..." : "Launch Intelligence"}
          <ArrowUp className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
});

type ChipButtonProps = {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
};

function ChipButton({ icon: Icon, label, onClick }: ChipButtonProps) {
  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      className={UI_BUTTON_STYLES.chip}
    >
      <Icon className="mr-2 h-3.5 w-3.5 shrink-0" />
      <span className="truncate sm:whitespace-normal">{label}</span>
    </Button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main export
// ═══════════════════════════════════════════════════════════════════════════════

export function ProspectPromptBuilder({
  className,
  initialValue = "",
  initialCompany,
  companyOptions = DEFAULT_COMPANIES,
  recentActivities = DEFAULT_ACTIVITIES,
  onCreateSetup,
  onAttachContent,
  onOpenVoiceInput,
  onNavigateToWorkspace,
  isSubmitting: externalIsSubmitting,
  getWorkspacePath,
  onFallbackNavigation,
  onBeforeSubmit,
}: ProspectPromptBuilderProps) {
  const [state, dispatch] = React.useReducer(
    builderReducer,
    { initialValue, initialCompany },
    ({ initialValue, initialCompany }) =>
      getInitialState(initialValue, initialCompany)
  );

  const isSubmitting = externalIsSubmitting ?? state.isSubmitting;

  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const helperId = React.useId();
  const statusId = React.useId();

  const matchedSelectedCompany = React.useMemo(() => {
    if (state.selectedCompany) return state.selectedCompany;
    if (!state.draft.companyName && !state.draft.companyDomain)
      return undefined;
    return companyOptions.find(company => {
      const nameMatches =
        state.draft.companyName &&
        company.name.toLowerCase() === state.draft.companyName.toLowerCase();
      const domainMatches =
        state.draft.companyDomain &&
        company.domain &&
        company.domain.toLowerCase() ===
          state.draft.companyDomain.toLowerCase();
      return Boolean(nameMatches || domainMatches);
    });
  }, [
    companyOptions,
    state.draft.companyDomain,
    state.draft.companyName,
    state.selectedCompany,
  ]);

  const activeDeliverableLabel = React.useMemo(
    () => deliverableLabel(state.primaryDeliverable),
    [state.primaryDeliverable]
  );
  const minimumContextAvailable = React.useMemo(
    () => hasMinimumContext(state),
    [state]
  );
  const submitEnabled = React.useMemo(() => canSubmit(state), [state]);
  const validationIssues = React.useMemo(
    () => getValidationIssues(state),
    [state]
  );
  const liveMessage =
    state.errorMessage || state.successMessage || state.statusMessage;

  React.useEffect(() => {
    if (
      matchedSelectedCompany &&
      matchedSelectedCompany.id !== state.selectedCompany?.id
    ) {
      dispatch({
        type: "SYNC_SELECTED_COMPANY",
        company: matchedSelectedCompany,
      });
    }
  }, [matchedSelectedCompany, state.selectedCompany]);

  React.useEffect(() => {
    if (!liveMessage) return;
    const timeout = window.setTimeout(
      () => dispatch({ type: "CLEAR_MESSAGES" }),
      MESSAGE_CLEAR_TIMEOUT_MS
    );
    return () => window.clearTimeout(timeout);
  }, [liveMessage]);

  const focusTextareaAtEnd = React.useCallback(() => {
    const node = textareaRef.current;
    if (!node) return;
    requestAnimationFrame(() => {
      node.focus();
      const position = node.value.length;
      node.setSelectionRange(position, position);
    });
  }, []);

  const handlePromptChange = React.useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      dispatch({ type: "APPLY_PROMPT_TEXT", promptText: event.target.value });
    },
    []
  );

  const handleEnableSection = React.useCallback(
    (section: SectionKey) => {
      dispatch({ type: "ENABLE_SECTION", section });
      focusTextareaAtEnd();
    },
    [focusTextareaAtEnd]
  );

  const handleCompanySelect = React.useCallback(
    (company: CompanyOption) => {
      dispatch({ type: "SELECT_COMPANY", company });
      focusTextareaAtEnd();
    },
    [focusTextareaAtEnd]
  );

  const handleStrengthen = React.useCallback(() => {
    dispatch({ type: "STRENGTHEN_PROMPT" });
    focusTextareaAtEnd();
  }, [focusTextareaAtEnd]);

  const handleDeepResearch = React.useCallback(() => {
    if (!minimumContextAvailable) return;
    dispatch({ type: "ENABLE_DEEP_RESEARCH" });
    focusTextareaAtEnd();
  }, [focusTextareaAtEnd, minimumContextAvailable]);

  const handleAttach = React.useCallback(async () => {
    try {
      const result = onAttachContent ? await onAttachContent() : null;
      const attachments = createAttachmentItems(
        result,
        state.attachments.length
      );
      dispatch({ type: "ATTACHMENTS_ADDED", attachments });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      log.error("Attach content failed", { error: errorMessage });
      dispatch({
        type: "SUBMIT_ERROR",
        message: "Unable to attach content. Please try again.",
      });
    }
  }, [onAttachContent, state.attachments.length]);

  const handleVoiceInput = React.useCallback(() => {
    const next = !state.isRecording;
    dispatch({ type: "SET_RECORDING", value: next });
    onOpenVoiceInput?.();
  }, [onOpenVoiceInput, state.isRecording]);

  const handleFormSubmit = React.useCallback(
    async (event?: React.FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      if (!submitEnabled || isSubmitting) return;

      dispatch({ type: "START_SUBMIT" });
      try {
        const payload = buildPayload(state);

        onBeforeSubmit?.(state);

        const result = onCreateSetup ? await onCreateSetup(payload) : undefined;
        const accountId = resolveNavigationAccountId(
          result,
          matchedSelectedCompany
        );

        dispatch({
          type: "SUBMIT_SUCCESS",
          message: accountId
            ? "Intelligence launched. Opening workspace..."
            : "New value case created.",
        });

        if (accountId) {
          const path = getWorkspacePath
            ? getWorkspacePath(accountId)
            : `/workspace`;
          if (onNavigateToWorkspace) {
            onNavigateToWorkspace(path, accountId);
          }
        } else {
          onFallbackNavigation?.();
        }
      } catch (error) {
        log.error("Form submission failed", { errorCode: String(error) });
        dispatch({
          type: "SUBMIT_ERROR",
          message: formatSubmitError(error),
        });
      }
    },
    [
      submitEnabled,
      isSubmitting,
      state,
      onBeforeSubmit,
      onCreateSetup,
      matchedSelectedCompany,
      getWorkspacePath,
      onNavigateToWorkspace,
      onFallbackNavigation,
    ]
  );

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        event.preventDefault();
        void handleFormSubmit();
      }
    },
    [handleFormSubmit]
  );

  const handleComplianceChip = React.useCallback(() => {
    dispatch({ type: "SET_FLAG", key: "complianceSensitive", value: true });
    dispatch({ type: "ENABLE_SECTION", section: "compliance" });
    focusTextareaAtEnd();
  }, [focusTextareaAtEnd]);

  return (
    <TooltipProvider delayDuration={150}>
      <div className={cn("w-full", className)}>
        <form
          className="mx-auto flex w-full max-w-4xl flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8"
          onSubmit={handleFormSubmit}
        >
          <PromptHeader
            mode={state.mode}
            onModeChange={mode => dispatch({ type: "SET_MODE", mode })}
            state={state}
            dispatch={dispatch}
            recentActivities={recentActivities}
          />

          <div className="px-2">
            <Label htmlFor="prospect-setup-prompt" className="sr-only">
              New value case prompt
            </Label>
            <p id={helperId} className="text-sm text-muted-foreground">
              Use quick inputs to shape a new value case, refine it naturally,
              and press Ctrl/Cmd+Enter to launch intelligence.
            </p>
          </div>

          <div className="relative overflow-hidden rounded-[28px] border border-border/60 bg-background shadow-sm">
            <div className="px-5 pt-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                {matchedSelectedCompany ? (
                  <Badge variant="outline" className={UI_BUTTON_STYLES.badge}>
                    <Building2 className="mr-1.5 h-3.5 w-3.5" />
                    {matchedSelectedCompany.name}
                  </Badge>
                ) : null}
                <Badge variant="outline" className={UI_BUTTON_STYLES.badge}>
                  {activeDeliverableLabel}
                </Badge>
                {state.complianceSensitive ? (
                  <Badge
                    variant="outline"
                    className="rounded-2xl border border-warning/40 bg-warning/10 px-2.5 py-1 text-xs font-medium text-warning dark:text-warning"
                  >
                    <Shield className="mr-1.5 h-3.5 w-3.5" />
                    Compliance-sensitive
                  </Badge>
                ) : null}
                {state.attachments.length > 0 ? (
                  <Badge variant="outline" className={UI_BUTTON_STYLES.badge}>
                    <Paperclip className="mr-1.5 h-3.5 w-3.5" />
                    {state.attachments.length} attachment
                    {state.attachments.length > 1 ? "s" : ""}
                  </Badge>
                ) : null}
              </div>
              <div className="mb-3 grid gap-3 rounded-2xl border border-border/60 bg-muted/20 p-3 sm:grid-cols-2">
                <label className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Company name
                  </span>
                  <input
                    type="text"
                    value={state.draft.companyName}
                    onChange={event =>
                      dispatch({
                        type: "SET_COMPANY_FIELD",
                        field: "companyName",
                        value: event.target.value,
                      })
                    }
                    placeholder="Company name"
                    className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm text-foreground shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    Website
                  </span>
                  <input
                    type="text"
                    value={state.draft.companyDomain}
                    onChange={event =>
                      dispatch({
                        type: "SET_COMPANY_FIELD",
                        field: "companyDomain",
                        value: event.target.value,
                      })
                    }
                    placeholder="Website"
                    className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm text-foreground shadow-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </label>
              </div>
            </div>

            <Textarea
              id="prospect-setup-prompt"
              ref={textareaRef}
              value={state.promptText}
              onChange={handlePromptChange}
              onKeyDown={handleKeyDown}
              aria-describedby={`${helperId} ${statusId}`}
              placeholder="Start a new value case by entering the company, context, stakeholders, pain points, and desired output..."
              className="min-h-[132px] resize-none border-0 bg-transparent px-5 pb-3 pt-0 vf-text-body-l leading-6 text-foreground shadow-none placeholder:text-muted-foreground/80 focus-visible:ring-0 focus-visible:ring-offset-0"
            />

            <StatusBanner
              successMessage={state.successMessage}
              statusMessage={state.statusMessage}
              errorMessage={state.errorMessage}
            />

            {!submitEnabled && (
              <ValidationChecklist issues={validationIssues} />
            )}

            <PromptFooter
              state={state}
              dispatch={dispatch}
              companyOptions={companyOptions}
              onAttachContent={onAttachContent}
              onOpenVoiceInput={onOpenVoiceInput}
              onSubmit={handleFormSubmit}
              submitEnabled={submitEnabled}
              isSubmitting={isSubmitting}
              minimumContextAvailable={minimumContextAvailable}
            />
          </div>

          <SuggestionsRail
            onEnableSection={handleEnableSection}
            onCompliance={handleComplianceChip}
          />

          <div
            id={statusId}
            aria-live="polite"
            aria-atomic="true"
            className="sr-only"
          >
            {liveMessage}
          </div>
        </form>
      </div>
    </TooltipProvider>
  );
}
