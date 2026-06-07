/**
 * RealizationPage — Value Realization workspace with milestone tracking
 *
 * Route: /realization/:accountId
 *
 * Loads action-plan data (recommendations from validated hypotheses) and renders
 * initiative cards with milestone progress. Tracking state is local-only until a
 * dedicated realization backend is built in a future phase.
 */
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  TrendingUp,
  CheckCircle2,
  Circle,
  Clock,
  AlertTriangle,
  ArrowRight,
  Target,
  Zap,
  ShieldCheck,
} from "lucide-react";
import RealizationShell from "@/components/workspace/RealizationShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, ErrorState } from "@/components/states";
import { useAccountHypotheses } from "@/hooks/useHypotheses";
import { useProducts } from "@/hooks/useProducts";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useNavigation } from "@/hooks";
import { createNextAction } from "@/components/workspace/nextAction";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";

// ── Types ────────────────────────────────────────────────────────────────────

type MilestoneStatus = "completed" | "in_progress" | "pending" | "at_risk";

interface Milestone {
  id: string;
  label: string;
  status: MilestoneStatus;
  dueDate: string;
}

interface Initiative {
  id: string;
  title: string;
  priority: "critical" | "high" | "medium";
  projectedValue: number;
  confidence: "high" | "medium" | "low";
  horizon: string;
  status: "on_track" | "at_risk" | "completed" | "not_started";
  milestones: Milestone[];
  capability: string;
  pain: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function mapHypothesesToInitiatives(
  hypotheses: Array<{
    id: string;
    hypothesis_text: string;
    value_path_category?: string;
    confidence_score?: number;
    confidence?: number;
    estimated_impact_usd?: number;
    capability_name?: string;
    signal_name?: string;
    status: string;
  }>
): Initiative[] {
  return hypotheses.map((h) => {
    const impact = h.estimated_impact_usd ?? 0;
    const confidenceScore = h.confidence_score ?? h.confidence ?? 0.5;

    let priority: Initiative["priority"] = "medium";
    if (h.value_path_category === "revenue_uplift" && confidenceScore >= 0.75) {
      priority = "critical";
    } else if (confidenceScore >= 0.7 || h.value_path_category === "revenue_uplift") {
      priority = "high";
    }

    const horizon = h.value_path_category === "cost_savings" ? "0–6 months" : "6–12 months";

    // Derive a realistic milestone chain from horizon
    const milestones: Milestone[] =
      horizon === "0–6 months"
        ? [
            { id: `${h.id}-m1`, label: "Planning", status: "completed", dueDate: "Week 2" },
            { id: `${h.id}-m2`, label: "Implementation", status: "in_progress", dueDate: "Week 8" },
            { id: `${h.id}-m3`, label: "Value Capture", status: "pending", dueDate: "Week 16" },
            { id: `${h.id}-m4`, label: "Validation", status: "pending", dueDate: "Week 20" },
          ]
        : [
            { id: `${h.id}-m1`, label: "Planning", status: "completed", dueDate: "Month 1" },
            { id: `${h.id}-m2`, label: "Pilot", status: "completed", dueDate: "Month 3" },
            { id: `${h.id}-m3`, label: "Rollout", status: "in_progress", dueDate: "Month 6" },
            { id: `${h.id}-m4`, label: "Value Capture", status: "pending", dueDate: "Month 9" },
            { id: `${h.id}-m5`, label: "Validation", status: "pending", dueDate: "Month 12" },
          ];

    // Overall initiative status derived from milestones
    const allCompleted = milestones.every((m) => m.status === "completed");
    const anyAtRisk = milestones.some((m) => m.status === "at_risk");
    const hasProgress = milestones.some((m) => m.status === "completed" || m.status === "in_progress");

    let status: Initiative["status"] = "not_started";
    if (allCompleted) status = "completed";
    else if (anyAtRisk) status = "at_risk";
    else if (hasProgress) status = "on_track";

    return {
      id: h.id,
      title: h.hypothesis_text,
      priority,
      projectedValue: impact,
      confidence: confidenceScore >= 0.8 ? "high" : confidenceScore >= 0.5 ? "medium" : "low",
      horizon,
      status,
      milestones,
      capability: h.capability_name ?? "Value driver",
      pain: h.signal_name ?? "Identified pain signal",
    };
  });
}

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-destructive/10 text-destructive border-destructive/20",
  high: "bg-warning/10 text-warning border-warning/20",
  medium: "bg-primary/10 text-primary border-primary/20",
};

const STATUS_STYLES: Record<string, { icon: React.ReactNode; class: string; text: string }> = {
  on_track: { icon: <TrendingUp size={12} />, class: "bg-success/10 text-success border-success/20", text: "On Track" },
  at_risk: { icon: <AlertTriangle size={12} />, class: "bg-warning/10 text-warning border-warning/20", text: "At Risk" },
  completed: { icon: <CheckCircle2 size={12} />, class: "bg-primary/10 text-primary border-primary/20", text: "Completed" },
  not_started: { icon: <Circle size={12} />, class: "bg-muted text-muted-foreground border-border", text: "Not Started" },
};

const MILESTONE_ICON: Record<MilestoneStatus, React.ReactNode> = {
  completed: <CheckCircle2 size={14} className="text-success" />,
  in_progress: <Zap size={14} className="text-warning" />,
  pending: <Circle size={14} className="text-muted-foreground" />,
  at_risk: <AlertTriangle size={14} className="text-destructive" />,
};

// ── Component ────────────────────────────────────────────────────────────────

export default function RealizationPage() {
  const params = useParams<{ accountId: string }>();
  const accountId = params.accountId ?? null;
  const { data: account, isLoading: accountLoading } = useAccount(accountId);
  const { navigateTo } = useNavigation();
  const [railMode, setRailMode] = useState<RightRailMode>("agent");

  const { data: hypothesesData, isLoading: hypothesesLoading } = useAccountHypotheses(
    accountId ?? null,
    { status: "validated" }
  );
  const { data: productsData } = useProducts();

  const hypotheses = hypothesesData?.hypotheses ?? [];
  const initiatives = useMemo(() => mapHypothesesToInitiatives(hypotheses), [hypotheses]);
  const nextAction = accountId
    ? createNextAction({
        label: "Back to Signals",
        target: "intelligence-signals",
        params: { accountId },
        disabled: initiatives.length === 0,
        reason: "Create a realization plan after generating initiatives.",
      })
    : null;

  // Computed metrics
  const activeInitiatives = initiatives.filter((i) => i.status === "on_track" || i.status === "at_risk").length;
  const completedInitiatives = initiatives.filter((i) => i.status === "completed").length;
  const totalProjectedValue = initiatives.reduce((sum, i) => sum + i.projectedValue, 0);
  const onTrackRate = initiatives.length
    ? Math.round(
        ((initiatives.filter((i) => i.status === "on_track" || i.status === "completed").length) /
          initiatives.length) *
          100
      )
    : 0;

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "realization",
    accountName: account?.name ?? "Account",
    accountId: accountId ?? undefined,
  });

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || hypothesesLoading) {
    return <LoadingState message="Loading realization data…" fullPage />;
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return (
    <RealizationShell
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="realization"
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
          steps={steps}
          isStreaming={isStreaming}
          runMetadata={metadata}
        />
      }
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">Value Realization</h2>
            <p className="text-sm text-muted-foreground">
              Track initiative execution, milestone achievement, and value realization progress
            </p>
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="Active Initiatives" value={String(activeInitiatives)} />
          <MetricCard
            label="Projected Value"
            value={totalProjectedValue >= 1000 ? `$${(totalProjectedValue / 1000).toFixed(1)}K` : `$${totalProjectedValue.toLocaleString()}`}
          />
          <MetricCard label="Completed" value={String(completedInitiatives)} />
          <MetricCard label="On Track" value={`${onTrackRate}%`} trend={onTrackRate >= 80 ? "Healthy" : onTrackRate >= 50 ? "Needs attention" : undefined} />
        </div>

        {/* Initiatives */}
        {initiatives.length === 0 ? (
          <SectionCard title="Initiatives">
            <div className="rounded-lg border border-dashed border-border p-8 text-center">
              <Target className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                No initiatives yet. Promote and validate signals in the Intelligence workspace, then model impact in the Calculator to generate trackable initiatives.
              </p>
            </div>
            <div className="mt-4 rounded-lg border border-border bg-muted/20 p-4">
              <div className="flex items-center gap-2">
                <ArrowRight className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Realization workflow</h3>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                The Action Plan turns validated signals, evidence, and calculator outputs into trackable customer outcomes.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Projected Value</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Approved initiatives become the value target that realization work is measured against.
                  </p>
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Baseline</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Customer-approved starting metrics are captured before rollout begins.
                  </p>
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Actual Value</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Actuals record realized value during execution and compare it with the target.
                  </p>
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Outcomes</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Outcome tracking keeps owners, metrics, milestones, and risks visible.
                  </p>
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Renewal Narrative</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Realized value becomes customer-facing proof for renewal and expansion reviews.
                  </p>
                </div>
                <div className="rounded-md border bg-background p-3">
                  <p className="text-xs font-semibold text-foreground">Next Step</p>
                  <p className="mt-1 vf-text-caption text-muted-foreground">
                    Generate initiatives from validated signals to create the first action plan.
                  </p>
                </div>
              </div>
            </div>
          </SectionCard>
        ) : (
          <div className="space-y-4">
            {initiatives.map((init) => {
              const statusMeta = STATUS_STYLES[init.status];
              const completedCount = init.milestones.filter((m) => m.status === "completed").length;
              const progressPct = Math.round((completedCount / init.milestones.length) * 100);

              return (
                <SectionCard key={init.id}>
                  {/* Initiative header */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="vf-text-body-m font-bold text-foreground truncate">{init.title}</h3>
                        <span
                          className={cn(
                            "vf-text-micro px-1.5 py-0.5 rounded border font-semibold",
                            PRIORITY_STYLES[init.priority]
                          )}
                        >
                          {init.priority}
                        </span>
                        <span
                          className={cn(
                            "vf-text-micro px-1.5 py-0.5 rounded border font-semibold inline-flex items-center gap-1",
                            statusMeta.class
                          )}
                        >
                          {statusMeta.icon}
                          {statusMeta.text}
                        </span>
                      </div>
                      <p className="vf-text-caption text-muted-foreground mt-1">
                        {init.horizon} · {init.projectedValue >= 1000 ? `$${(init.projectedValue / 1000).toFixed(1)}K` : `$${init.projectedValue.toLocaleString()}`} projected · {init.confidence} confidence
                      </p>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between vf-text-micro text-muted-foreground mb-1">
                      <span>Progress</span>
                      <span>{progressPct}%</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          init.status === "at_risk"
                            ? "bg-warning/100"
                            : init.status === "completed"
                            ? "bg-primary/100"
                            : "bg-success/100"
                        )}
                        style={{ width: `${progressPct}%` }}
                      />
                    </div>
                  </div>

                  {/* Milestones */}
                  <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {init.milestones.map((m) => (
                      <div
                        key={m.id}
                        className={cn(
                          "rounded-md border p-2.5 text-center",
                          m.status === "completed"
                            ? "border-success/20 bg-success/10/30"
                            : m.status === "in_progress"
                            ? "border-warning/20 bg-warning/10/30"
                            : m.status === "at_risk"
                            ? "border-destructive/20 bg-destructive/10/30"
                            : "border-border bg-muted/20"
                        )}
                      >
                        <div className="flex justify-center mb-1">{MILESTONE_ICON[m.status]}</div>
                        <p className="vf-text-caption font-medium text-foreground">{m.label}</p>
                        <p className="vf-text-micro text-muted-foreground mt-0.5">{m.dueDate}</p>
                      </div>
                    ))}
                  </div>

                  {/* Detail row */}
                  <div className="mt-3 flex items-center gap-4 vf-text-caption text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <ShieldCheck size={11} /> {init.capability}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Clock size={11} /> {init.pain}
                    </span>
                  </div>
                </SectionCard>
              );
            })}
          </div>
        )}
        {nextAction && (
          <div className="flex items-center justify-end gap-2">
            {nextAction.disabled && <span className="text-xs text-muted-foreground">{nextAction.reason}</span>}
            <Button disabled={nextAction.disabled} onClick={() => navigateTo(nextAction.target, nextAction.params)} data-testid="primary-forward-action">
              {nextAction.label}
            </Button>
          </div>
        )}
      </div>
    </RealizationShell>
  );
}
