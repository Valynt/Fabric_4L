import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Filter,
  ShieldCheck,
  XCircle,
  Zap,
} from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { useNavigation } from "@/hooks";
import { useCanonicalCaseId, usePersistWorkspaceTab } from "@/hooks/useWorkspaceCase";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, EmptyState, ErrorState } from "@/components/states";
import { cn } from "@/lib/utils";
import {
  useValueSignals,
  useReviewSignal,
  usePromoteValueSignal,
  useRefineSignals,
} from "@/hooks/useValueSignals";
import {
  toSignalCard,
  type ValueSignal,
  type SignalCard,
  type ValueSignalLifecycleState,
} from "@/types/valueSignal";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn, MetricCard } from "@/components/ui/fabric";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const LIFECYCLE_BADGE: Record<ValueSignalLifecycleState, { label: string; className: string }> = {
  draft:      { label: "Draft",      className: "bg-muted text-muted-foreground" },
  extracted:  { label: "Extracted",  className: "bg-info/10 text-info" },
  validated:  { label: "Validated",  className: "bg-success/10 text-success" },
  rejected:   { label: "Rejected",   className: "bg-destructive/10 text-destructive" },
  promoted:   { label: "Promoted",   className: "bg-primary/10 text-primary" },
  expired:    { label: "Expired",    className: "bg-warning/10 text-warning" },
  superseded: { label: "Superseded", className: "bg-muted text-muted-foreground" },
};

const TYPE_DOT: Record<string, string> = {
  Pain:               "bg-destructive/100",
  Opportunity:        "bg-success/100",
  Risk:               "bg-warning/100",
  Expansion:          "bg-primary/100",
  Renewal:            "bg-warning/100",
  "Cost Saving":      "bg-success/100",
  "Revenue Uplift":   "bg-primary/100",
  Efficiency:         "bg-info/100",
  Compliance:         "bg-primary/100",
  "Strategic Priority": "bg-primary/100",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LifecycleBadge({ state }: { state: ValueSignalLifecycleState }) {
  const cfg = LIFECYCLE_BADGE[state] ?? { label: state, className: "bg-muted text-muted-foreground" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 vf-text-micro font-medium", cfg.className)}>
      {cfg.label}
    </span>
  );
}

function TrustBar({ score }: { score: number }) {
  const pct = Math.round(score);
  const color = pct >= 70 ? "bg-success" : pct >= 40 ? "bg-warning" : "bg-destructive";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="vf-text-micro text-muted-foreground">{pct}%</span>
    </div>
  );
}

function EvidenceList({ evidence }: { evidence: ValueSignal["evidence"] }) {
  if (!evidence.length) {
    return <p className="vf-text-caption text-muted-foreground italic">No evidence attached.</p>;
  }
  return (
    <div className="space-y-2">
      {evidence.map((item) => (
        <div key={item.id} className="rounded-md border border-border bg-muted/30 p-2 vf-text-caption">
          <div className="flex items-start justify-between gap-2">
            <span className="font-medium text-foreground truncate">{item.source_ref}</span>
            <span className="shrink-0 text-muted-foreground">{Math.round(item.confidence * 100)}%</span>
          </div>
          {item.excerpt && <p className="mt-1 text-muted-foreground line-clamp-2">{item.excerpt}</p>}
          {item.url && (
            <a href={item.url} target="_blank" rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-primary hover:underline">
              Source <ExternalLink size={10} />
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

function ProvenanceBlock({ provenance }: { provenance: ValueSignal["provenance"] }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 p-2 vf-text-caption space-y-1">
      <div className="flex items-center gap-1.5 font-medium text-foreground">
        <ShieldCheck size={11} className="text-muted-foreground" /> Provenance
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-muted-foreground">
        <span>Extractor</span><span className="text-foreground capitalize">{provenance.extractor}</span>
        <span>Method</span><span className="text-foreground">{provenance.method}</span>
        {provenance.model && <><span>Model</span><span className="text-foreground">{provenance.model}</span></>}
        {provenance.source_system && <><span>System</span><span className="text-foreground">{provenance.source_system}</span></>}
        <span>Extracted</span><span className="text-foreground">{new Date(provenance.extracted_at).toLocaleString()}</span>
      </div>
    </div>
  );
}

export default function SignalsTab() {
  const params = useParams<{ accountId: string }>();
  const accountId = params.accountId ?? null;
  const { data: account, isLoading: accountLoading, error: accountError } = useAccount(accountId);
  const {
    data: signalList,
    isLoading: signalsLoading,
    error: signalsError,
    refetch: refetchSignals,
  } = useValueSignals(accountId);

  const reviewMutation = useReviewSignal();
  const promoteMutation = usePromoteValueSignal();
  const refineMutation = useRefineSignals();
  const { navigateTo } = useNavigation();
  const persistTab = usePersistWorkspaceTab("signals");
  // Only resolve the canonical case ID when persistence has failed and the user
  // may retry — avoids an unconditional POST /analysis/cases on every mount.
  const { data: caseId } = useCanonicalCaseId(persistTab.isError ? accountId : null);

  const [selectedSignal, setSelectedSignal] = useState<ValueSignal | null>(null);
  const [railMode, setRailMode] = useState<RightRailMode>("agent");
  const [selectedValuePath, setSelectedValuePath] = useState<string>("");

  const signals: ValueSignal[] = signalList?.items ?? [];
  const cards: SignalCard[] = signals.map(toSignalCard);

  const handleReview = async (status: "validated" | "rejected") => {
    if (!selectedSignal || !accountId) return;
    const updated = await reviewMutation.mutateAsync({
      signalId: selectedSignal.id,
      accountId,
      body: { status },
    });
    setSelectedSignal(updated);
  };

  const handlePromote = async () => {
    if (!selectedSignal || !accountId || !selectedValuePath) return;
    await promoteMutation.mutateAsync({
      signalId: selectedSignal.id,
      accountId,
      body: {
        value_path_category: selectedValuePath as
          | "revenue_uplift"
          | "cost_savings"
          | "risk_reduction"
          | "blended",
      },
    });
  };

  const handleRefine = () => {
    if (!accountId) return;
    refineMutation.mutate({ account_id: accountId, source_refs: [] });
  };

  const isLoading = accountLoading || signalsLoading;
  const hasError = accountError || signalsError;

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "signals",
    accountName: account?.name ?? "Account",
    accountId: accountId ?? undefined,
    selectedSignalId: selectedSignal?.id,
    entityContext: { selectedSignal: selectedSignal ?? undefined },
  });

  if (!accountId) return <AccountRequiredGuard accountId={accountId} />;

  const selectedCard = selectedSignal ? toSignalCard(selectedSignal) : null;

  const detailContent = selectedSignal && selectedCard ? (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <LifecycleBadge state={selectedSignal.lifecycle_state} />
          <span className="vf-text-micro text-muted-foreground">{selectedCard.category}</span>
        </div>
        <h3 className="vf-text-body-m font-semibold text-foreground leading-snug">{selectedCard.name}</h3>
      </div>
      {/* Scores */}
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-md bg-muted/50 p-2 text-center">
          <div className="vf-text-micro text-muted-foreground mb-0.5">Confidence</div>
          <div className="vf-text-body-l font-bold">{selectedCard.confidence}%</div>
        </div>
        <div className="rounded-md bg-muted/50 p-2">
          <div className="vf-text-micro text-muted-foreground mb-0.5">Trust</div>
          <TrustBar score={selectedCard.trust_score} />
        </div>
      </div>
      {selectedSignal.impact_area && (
        <div className="vf-text-caption text-muted-foreground">
          Impact: <span className="text-foreground font-medium">{selectedCard.impact}</span>
        </div>
      )}
      {/* Review */}
      <div className="grid grid-cols-2 gap-2">
        <Btn variant={selectedSignal.lifecycle_state === "validated" ? "primary" : "outline"} className="w-full"
          onClick={() => handleReview("validated")} disabled={reviewMutation.isPending}>
          <CheckCircle2 size={12} /> Approve
        </Btn>
        <Btn variant={selectedSignal.lifecycle_state === "rejected" ? "danger" : "outline"} className="w-full"
          onClick={() => handleReview("rejected")} disabled={reviewMutation.isPending}>
          <XCircle size={12} /> Reject
        </Btn>
      </div>
      {/* Promote */}
      <div className="space-y-2 pt-1">
        <label className="vf-text-caption font-medium text-muted-foreground">Value Path</label>
        <Select value={selectedValuePath} onValueChange={setSelectedValuePath}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select value path…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="revenue_uplift">Revenue Uplift</SelectItem>
            <SelectItem value="cost_savings">Cost Savings</SelectItem>
            <SelectItem value="risk_reduction">Risk Reduction</SelectItem>
            <SelectItem value="blended">Blended</SelectItem>
          </SelectContent>
        </Select>
        <Btn variant="primary" className="w-full"
          disabled={!["validated","extracted"].includes(selectedSignal.lifecycle_state) || !selectedValuePath || promoteMutation.isPending}
          onClick={handlePromote}>
          {promoteMutation.isPending ? "Promoting…" : "Promote to Value Path"}
        </Btn>
        {promoteMutation.isSuccess && (
          <Btn variant="ghost" className="w-full text-primary" onClick={() => navigateTo("hypothesis", { accountId })}>
            View Hypothesis <ArrowRight size={12} />
          </Btn>
        )}
      </div>
      {/* Evidence */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center gap-1.5 vf-text-caption font-medium text-muted-foreground">
          <Zap size={11} /> Evidence ({selectedSignal.evidence.length})
        </div>
        <EvidenceList evidence={selectedSignal.evidence} />
      </div>
      {/* Provenance */}
      <ProvenanceBlock provenance={selectedSignal.provenance} />
      {selectedSignal.validation_notes && (
        <div className="vf-text-caption text-muted-foreground border-t border-border pt-2">
          Notes: {selectedSignal.validation_notes}
        </div>
      )}
    </div>
  ) : null;

  return (
    <IntelligenceShell
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          detailContent={detailContent}
          activeTab="signals"
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
          steps={steps}
          isStreaming={isStreaming}
          runMetadata={metadata}
        />
      }
    >
      {persistTab.persistState === "failed" && (
        <div className="mb-4 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-xs flex items-center justify-between">
          <span>Could not persist this tab</span>
          {caseId && (
            <button className="underline" onClick={() => persistTab.mutate({ caseId, payload: { signals: signalList?.items ?? [] } })}>
              Retry save
            </button>
          )}
        </div>
      )}
      {isLoading ? (
        <LoadingState message="Loading signals…" />
      ) : hasError ? (
        <ErrorState
          title="Signals could not be loaded"
          description="The app could not retrieve value signals for this account. Check that the L2.5 Signal Refinery service is running."
          error={signalsError || accountError}
          onRetry={refetchSignals}
          retryLabel="Retry"
          fallbackAction={
            <Link to="/accounts">
              <Btn variant="outline">Go to Accounts</Btn>
            </Link>
          }
        />
      ) : signals.length === 0 ? (
        <EmptyState
          title="No signals yet"
          description="Run intelligence gathering to generate evidence-backed value signals for this account."
          icon={Activity}
          action={
            <Btn onClick={handleRefine} disabled={refineMutation.isPending}>
              {refineMutation.isPending ? "Generating…" : "Generate Signals"}
            </Btn>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard label="Signals" value={String(signals.length)} trend="Account-scoped" trendUp />
            <MetricCard
              label="Avg Confidence"
              value={`${Math.round((signals.reduce((s, x) => s + x.confidence, 0) / signals.length) * 100)}%`}
            />
            <MetricCard
              label="Avg Trust"
              value={`${Math.round((signals.reduce((s, x) => s + x.trust_score, 0) / signals.length) * 100)}%`}
            />
            <MetricCard
              label="Validated"
              value={String(signals.filter((s) => s.lifecycle_state === "validated" || s.lifecycle_state === "promoted").length)}
            />
          </div>

          <SectionCard title="Value Signals">
            <div className="flex items-center justify-between mb-3">
              <span className="vf-text-caption text-muted-foreground">{signals.length} detected</span>
              <Btn variant="outline" className="gap-1.5">
                <Filter size={12} /> Filters
              </Btn>
            </div>
            {cards.map((card, i) => {
              const signal = signals[i];
              const isSelected = selectedSignal?.id === card.id;
              return (
                <button
                  key={card.id}
                  onClick={() => { setSelectedSignal(signal); setRailMode("detail"); }}
                  className={cn(
                    "w-full text-left px-3 py-3 border-b border-border last:border-0",
                    "grid grid-cols-[auto_1fr_auto_auto_auto_auto] gap-3 items-center vf-text-body-s",
                    isSelected ? "bg-primary/5" : "hover:bg-muted/50",
                  )}
                >
                  <span className="w-5 text-muted-foreground font-medium">{i + 1}</span>
                  <div className="flex items-center gap-2 min-w-0">
                    <div className={cn("w-1.5 h-5 rounded-full shrink-0", TYPE_DOT[card.category] ?? "bg-muted-foreground")} />
                    <span className="font-medium truncate">{card.name}</span>
                  </div>
                  <LifecycleBadge state={card.lifecycle_state} />
                  <span className="w-12 text-right text-muted-foreground">{card.confidence}%</span>
                  <TrustBar score={card.trust_score} />
                  <span className="w-14 text-right text-muted-foreground vf-text-micro">{card.evidence_count} ev.</span>
                </button>
              );
            })}
          </SectionCard>
        </>
      )}
    </IntelligenceShell>
  );
}
