import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, Circle, Clock, AlertTriangle, ChevronRight, XCircle } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { apiClient } from "@/api/client";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type JourneyStageStatus = "not_started" | "in_progress" | "completed" | "blocked" | "failed";

export interface JourneyTimelineStage {
  id: string;
  label: string;
  stage_key: string;
  status: JourneyStageStatus;
  updated_at?: string | null;
  actor?: string | null;
  source_artifact_id?: string | null;
  target_artifact_id?: string | null;
  evidence_links?: string[];
  truth_object_ids?: string[];
  warnings?: string[];
  degradation_reason?: string | null;
  deep_link?: string | null;
}

export interface AccountJourneyTimelineResponse {
  tenant_id: string;
  account_id: string;
  journey_id: string;
  stages: JourneyTimelineStage[];
  current_stage_key: string;
  updated_at: string;
}

interface JourneyTimelineRightRailProps {
  tenantSlug?: string;
  accountId?: string;
  journeyId?: string;
  onClose?: () => void;
}

const DEFAULT_STAGES: JourneyTimelineStage[] = [
  { id: "signal", label: "Signal", stage_key: "signal", status: "completed", deep_link: "intelligence/signals" },
  { id: "hypothesis", label: "Hypothesis", stage_key: "hypothesis", status: "completed", deep_link: "intelligence/hypotheses" },
  { id: "value_drivers", label: "Value drivers", stage_key: "value_drivers", status: "in_progress", deep_link: "studio/value-drivers" },
  { id: "roi_calculation", label: "ROI calculation", stage_key: "roi_calculation", status: "not_started", deep_link: "studio/financial-modeling" },
  { id: "evidence_validation", label: "Evidence validation", stage_key: "evidence_validation", status: "not_started", deep_link: "studio/integrity-review" },
  { id: "narrative", label: "Narrative", stage_key: "narrative", status: "not_started", deep_link: "studio/narrative-builder" },
  { id: "export_crm_sync", label: "Export or CRM sync", stage_key: "export_crm_sync", status: "not_started", deep_link: "deliverables/exports" },
];

export function JourneyTimelineRightRail({
  tenantSlug,
  accountId,
  journeyId,
  onClose,
}: JourneyTimelineRightRailProps) {
  const params = useParams<{ tenantSlug: string; accountId: string }>();
  const activeTenantSlug = tenantSlug || params.tenantSlug || "default";
  const activeAccountId = accountId || params.accountId || "";

  const [stages, setStages] = useState<JourneyTimelineStage[]>(DEFAULT_STAGES);
  const [activeJourneyId, setActiveJourneyId] = useState<string>(journeyId || `journey_${activeAccountId}`);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);

  useEffect(() => {
    if (!activeAccountId) return;
    let isMounted = true;
    setIsLoading(true);
    setHasError(false);
    // Clear any data from a previously selected account before fetching the new one.
    setStages(DEFAULT_STAGES);
    setActiveJourneyId(journeyId || `journey_${activeAccountId}`);

    apiClient
      .get<AccountJourneyTimelineResponse>(
        "l4",
        `/accounts/${activeAccountId}/journey-timeline`
      )
      .then((res) => {
        const data = res.data;
        if (isMounted && data?.stages) {
          setStages(data.stages);
          if (data.journey_id) setActiveJourneyId(data.journey_id);
          setHasError(false);
        }
      })
      .catch(() => {
        if (isMounted) setHasError(true);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeAccountId, journeyId]);

  const renderStatusIcon = (status: JourneyStageStatus) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
      case "in_progress":
        return <Clock className="h-4 w-4 text-amber-500 animate-pulse shrink-0" />;
      case "blocked":
        return <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-rose-500 shrink-0" />;
      default:
        return <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-background border-l border-border select-none">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">ValuePilot Journey</h3>
          <p className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">
            {activeJourneyId}
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-xs px-2 py-1 rounded"
          >
            Close
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading && (
          <div className="text-[11px] text-muted-foreground animate-pulse">
            Syncing journey timeline...
          </div>
        )}
        {!isLoading && hasError && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3">
            <p className="text-xs font-semibold text-destructive">Unable to load journey</p>
            <p className="text-[11px] text-muted-foreground mt-1">
              Journey timeline could not be fetched for this account. Please try again.
            </p>
          </div>
        )}
        {stages.map((stage, idx) => {
          const isCurrent = stage.status === "in_progress";
          const stageUrl = stage.deep_link
            ? stage.deep_link.startsWith("/")
              ? `/t/${activeTenantSlug}${stage.deep_link}`
              : `/t/${activeTenantSlug}/accounts/${activeAccountId}/${stage.deep_link}`
            : `/t/${activeTenantSlug}/accounts/${activeAccountId}`;

          return (
            <div key={stage.id || stage.stage_key} className="relative pl-6">
              {idx < stages.length - 1 && (
                <div
                  className={cn(
                    "absolute left-2 top-5 bottom-0 w-0.5 -mb-4",
                    stage.status === "completed" ? "bg-emerald-500/40" : "bg-border"
                  )}
                />
              )}
              <div className="absolute left-0 top-0.5">
                {renderStatusIcon(stage.status)}
              </div>

              <div className={cn("p-2.5 rounded-lg border", isCurrent ? "border-primary/50 bg-primary/5" : "border-border/60 bg-card/40")}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">{stage.label}</span>
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded capitalize",
                      stage.status === "completed" && "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                      stage.status === "in_progress" && "bg-amber-500/10 text-amber-600 dark:text-amber-400",
                      stage.status === "not_started" && "bg-muted text-muted-foreground"
                    )}
                  >
                    {stage.status.replace("_", " ")}
                  </span>
                </div>

                {stage.actor && (
                  <div className="text-[11px] text-muted-foreground mt-1">
                    Actor: {stage.actor}
                  </div>
                )}

                {stage.source_artifact_id && (
                  <div className="text-[10px] text-muted-foreground/80 font-mono mt-0.5">
                    Artifact: {stage.source_artifact_id}
                  </div>
                )}

                {stage.warnings && stage.warnings.length > 0 && (
                  <div className="mt-1.5 text-[11px] text-amber-600 dark:text-amber-400 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 shrink-0" />
                    <span>{stage.warnings[0]}</span>
                  </div>
                )}

                <div className="mt-2 flex justify-end">
                  <Link
                    to={stageUrl}
                    className="text-[11px] text-primary hover:underline flex items-center gap-0.5"
                  >
                    <span>View step</span>
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
