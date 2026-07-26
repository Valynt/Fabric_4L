/**
 * EnrichmentTab — Account Intelligence & Enrichment
 *
 * DIL-backed tab that replaces the generic workspace pattern.
 * Uses: useEnrichment (L4), useAccountBriefing (L4), useDealReadiness (L4)
 *
 * Shows enrichment status, financials, tech stack, executives, news,
 * and deal readiness score for the selected account.
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Building2,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  DollarSign,
  Cpu,
  Users,
  Newspaper,
  TrendingUp,
  Loader2,
} from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import { cn } from "@/lib/utils";
import {
  useEnrichAccount,
  useEnrichmentDetails,
  type EnrichmentResult,
  type EnrichmentFinancials,
} from "@/hooks/useEnrichment";
import {
  useAccountBriefing,
  useDealReadiness,
  type DealReadiness,
} from "@/hooks/useIntelligence";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard, StatusBadge, Btn } from "@/components/ui/fabric";

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(val: number | undefined): string {
  if (val == null) return "N/A";
  if (val >= 1_000_000_000) return `$${(val / 1_000_000_000).toFixed(1)}B`;
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toLocaleString()}`;
}

function readinessColor(label: string): string {
  switch (label) {
    case "deal_ready": return "text-success";
    case "strong": return "text-success";
    case "developing": return "text-warning";
    case "early": return "text-warning";
    case "not_ready": return "text-destructive";
    default: return "text-muted-foreground";
  }
}

function readinessLabel(label: string): string {
  return label.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Sub-components ───────────────────────────────────────────────────────────

function ReadinessGauge({ readiness }: { readiness: DealReadiness }) {
  const pct = Math.round(readiness.overall_score * 100);
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground">Deal Readiness</span>
        <span className={cn("text-lg font-bold", readinessColor(readiness.label))}>
          {pct}%
        </span>
      </div>
      <div className="w-full bg-muted rounded-full h-2">
        <div
          className={cn("h-2 rounded-full transition-all", {
            "bg-success": pct >= 80,
            "bg-success/80": pct >= 60 && pct < 80,
            "bg-warning": pct >= 40 && pct < 60,
            "bg-warning/80": pct >= 20 && pct < 40,
            "bg-destructive": pct < 20,
          })}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn("vf-text-micro font-semibold", readinessColor(readiness.label))}>
        {readinessLabel(readiness.label)}
      </span>
      {/* Component breakdown */}
      <div className="grid grid-cols-2 gap-2 mt-2">
        {Object.entries(readiness.components).map(([key, val]) => (
          <div key={key} className="flex items-center justify-between vf-text-micro">
            <span className="text-muted-foreground truncate">{key.replace(/_/g, " ")}</span>
            <span className="font-semibold">{Math.round(val * 100)}%</span>
          </div>
        ))}
      </div>
      {/* Recommendations */}
      {readiness.recommendations.length > 0 && (
        <div className="mt-3 space-y-1">
          <span className="vf-text-micro font-semibold text-muted-foreground">Recommendations</span>
          {readiness.recommendations.map((rec) => (
            <div key={rec} className="flex items-start gap-1.5 vf-text-micro text-muted-foreground">
              <AlertTriangle size={10} className="mt-0.5 text-warning shrink-0" />
              <span>{rec}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FinancialsSection({ financials }: { financials: EnrichmentFinancials }) {
  const revenue = financials?.revenue;
  const employees = financials?.employees;
  const growthRate = financials?.growth_rate;
  const fiscalYear = financials?.fiscal_year;

  return (
    <SectionCard title="Financials">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <span className="vf-text-micro text-muted-foreground">Revenue</span>
          <div className="text-sm font-semibold flex items-center gap-1">
            <DollarSign size={12} />
            {formatCurrency(revenue)}
          </div>
        </div>
        <div className="space-y-1">
          <span className="vf-text-micro text-muted-foreground">Employees</span>
          <div className="text-sm font-semibold">{employees?.toLocaleString() ?? "N/A"}</div>
        </div>
        <div className="space-y-1">
          <span className="vf-text-micro text-muted-foreground">Growth Rate</span>
          <div className={cn("text-sm font-semibold flex items-center gap-1", growthRate && growthRate > 0 ? "text-success" : "text-destructive")}>
            <TrendingUp size={12} />
            {growthRate != null ? `${(growthRate * 100).toFixed(1)}%` : "N/A"}
          </div>
        </div>
        <div className="space-y-1">
          <span className="vf-text-micro text-muted-foreground">Fiscal Year</span>
          <div className="text-sm font-semibold">{fiscalYear ?? "N/A"}</div>
        </div>
      </div>
    </SectionCard>
  );
}

function TechStackSection({ techStack }: { techStack: string[] }) {
  if (!techStack.length) return null;
  return (
    <SectionCard title="Technology Stack">
      <div className="flex flex-wrap gap-1.5">
        {techStack.map((tech) => (
          <span
            key={tech}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary vf-text-micro font-medium"
          >
            <Cpu size={10} />
            {tech}
          </span>
        ))}
      </div>
    </SectionCard>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function EnrichmentTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account } = useAccount(accountId ?? null);
  const { data: briefing, isLoading: briefingLoading } = useAccountBriefing(accountId ?? null);
  const { data: readiness, isLoading: readinessLoading } = useDealReadiness(accountId ?? null);
  const enrichAccount = useEnrichAccount();

  const [railMode, setRailMode] = useState<RightRailMode>("detail");
  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({ accountId: accountId ?? undefined,
    activeTab: "enrichment",
    accountName: account?.name ?? "Account",
  });

  const isLoading = briefingLoading || readinessLoading;
  const enrichment = briefing?.enrichment;
  const financials = enrichment?.financials ?? {};
  const techStack = enrichment?.tech_stack ?? [];
  const sourcesUsed = enrichment?.sources_used ?? [];

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (isLoading) {
    return <CenteredLoader message="Loading account intelligence…" />;
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return (
    <IntelligenceShell
      account={{
        accountName: account.name,
        industry: account.industry ?? "Unknown",
        revenue: account.annual_revenue
          ? `$${account.annual_revenue.toLocaleString()}`
          : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="enrichment"
          detailContent={
            readiness ? (
              <ReadinessGauge readiness={readiness} />
            ) : (
              <div className="text-xs text-muted-foreground">
                No deal readiness data available.
              </div>
            )
          }
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
            steps={steps}
            isStreaming={isStreaming}
            runMetadata={metadata}
        />
      }
    >
      {/* Header metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Enrichment Sources"
          value={String(sourcesUsed.length)}
          trend={sourcesUsed.join(", ")}
        />
        <MetricCard
          label="Signals Detected"
          value={String(briefing?.signals?.total ?? 0)}
        />
        <MetricCard
          label="Hypotheses"
          value={String(briefing?.hypotheses?.total ?? 0)}
        />
        <MetricCard
          label="Deal Readiness"
          value={readiness ? `${Math.round(readiness.overall_score * 100)}%` : "N/A"}
          trend={readiness ? readinessLabel(readiness.label) : undefined}
        />
      </div>

      {/* Enrich action */}
      <div className="flex items-center gap-3 mb-6">
        <Btn
          variant="primary"
          onClick={() => {
            if (accountId) {
              enrichAccount.mutate({ accountId, params: { force: false } });
            }
          }}
          disabled={enrichAccount.isPending}
        >
          {enrichAccount.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          {enrichAccount.isPending ? "Enriching…" : "Enrich Account"}
        </Btn>
        <Btn
          variant="outline"
          onClick={() => {
            if (accountId) {
              enrichAccount.mutate({ accountId, params: { force: true } });
            }
          }}
          disabled={enrichAccount.isPending}
        >
          Force Re-enrich
        </Btn>
        {enrichment?.last_enriched_at && (
          <span className="vf-text-micro text-muted-foreground flex items-center gap-1">
            <Clock size={10} />
            Last enriched: {new Date(enrichment.last_enriched_at).toLocaleDateString()}
          </span>
        )}
        {enrichAccount.isSuccess && (
          <span className="vf-text-micro text-success flex items-center gap-1">
            <CheckCircle2 size={10} />
            Enrichment complete
          </span>
        )}
      </div>

      {/* Financials */}
      {Object.keys(financials).length > 0 && (
        <div className="mb-4">
          <FinancialsSection financials={financials} />
        </div>
      )}

      {/* Tech Stack */}
      {techStack.length > 0 && (
        <div className="mb-4">
          <TechStackSection techStack={techStack} />
        </div>
      )}

      {/* Recent Signals */}
      {briefing?.signals?.recent && briefing.signals.recent.length > 0 && (
        <SectionCard title="Recent Signals" className="mb-4">
          <div className="space-y-1">
            {briefing.signals.recent.map((signal) => (
              <div
                key={signal.id}
                className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted/50"
              >
                <AlertTriangle size={12} className="text-warning shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium truncate">{signal.text}</div>
                  <div className="vf-text-micro text-muted-foreground">
                    {signal.category} · {new Date(signal.detected_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Competitive snapshot */}
      {briefing?.competitive?.competitors && briefing.competitive.competitors.length > 0 && (
        <SectionCard title="Competitive Landscape">
          <div className="space-y-1">
            {briefing.competitive.competitors.map((comp) => (
              <div
                key={comp.name}
                className="flex items-center justify-between px-3 py-2 rounded-md hover:bg-muted/50"
              >
                <span className="text-xs font-medium">{comp.name}</span>
                <div className="flex items-center gap-3">
                  <span className="vf-text-micro text-muted-foreground">
                    Win rate: {Math.round(comp.win_rate * 100)}%
                  </span>
                  <span
                    className={cn("vf-text-micro font-semibold", {
                      "text-destructive": comp.threat_level === "high",
                      "text-warning": comp.threat_level === "medium",
                      "text-success": comp.threat_level === "low",
                    })}
                  >
                    {comp.threat_level}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Empty state */}
      {!briefing && !isLoading && (
        <SectionCard title="Account Intelligence">
          <div className="text-center py-8">
            <Building2 size={32} className="mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-2">
              No enrichment data available yet.
            </p>
            <p className="text-xs text-muted-foreground">
              Click "Enrich Account" to pull financial data, tech stack, and competitive intelligence.
            </p>
          </div>
        </SectionCard>
      )}
    </IntelligenceShell>
  );
}
