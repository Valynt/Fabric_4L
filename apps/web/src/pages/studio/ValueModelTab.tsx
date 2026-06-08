/**
 * Value Model Tab — Enhanced with DIL hooks
 *
 * Primary data: workspace case value lines (existing)
 * DIL enrichment: ROI calculator for financial modeling + industry benchmarks
 */
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Settings2, Calculator, TrendingUp, BarChart3 } from "lucide-react";
import ValueStudioShellComponent from "@/components/workspace/ValueStudioShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { ErrorState } from "@/components/states/ErrorState";
import {
  useCanonicalCaseId,
  usePersistWorkspaceTab,
  useWorkspaceTabQuery,
  useGenerateWorkspaceIntelligence,
} from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";

// DIL hooks
import {
  useCalculateROI,
  useIndustryBenchmarks,
  type ROICalculationResult,
  type IndustryBenchmark,
} from "@/hooks/useROICalculator";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard, Btn } from "@/components/ui/fabric";

// ── Types ──────────────────────────────────────────────────────────────────────
type Scenario = "conservative" | "expected" | "optimistic";

interface ValueLine {
  id: string;
  driver: string;
  category: "hard" | "strategic";
  conservative: number;
  expected: number;
  optimistic: number;
  source: string;
}

const SCENARIO_LABELS: Record<Scenario, string> = {
  conservative: "Conservative",
  expected: "Expected",
  optimistic: "Optimistic",
};

const formatCurrency = (n: number) =>
  n >= 1_000_000
    ? `$${(n / 1_000_000).toFixed(2)}M`
    : `$${Math.round(n).toLocaleString()}`;

const formatPercent = (n: number) => `${(n * 100).toFixed(1)}%`;

// ── ROI Summary Card ───────────────────────────────────────────────────────────
function ROISummaryCard({ result }: { result: ROICalculationResult }) {
  return (
    <SectionCard title="ROI Analysis" className="mt-4">
      <div className="flex items-center gap-2 mb-3">
        <Calculator size={13} className="text-primary" />
        <span className="vf-text-caption text-muted-foreground">
          Calculated by the DIL ROI Engine
        </span>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <div className="text-center p-3 bg-muted/50 rounded-md">
          <p className="vf-text-micro text-muted-foreground">NPV</p>
          <p className="vf-text-body-l font-bold text-primary">
            {formatCurrency(result.npv)}
          </p>
        </div>
        <div className="text-center p-3 bg-muted/50 rounded-md">
          <p className="vf-text-micro text-muted-foreground">IRR</p>
          <p className="vf-text-body-l font-bold text-success">
            {formatPercent(result.irr)}
          </p>
        </div>
        <div className="text-center p-3 bg-muted/50 rounded-md">
          <p className="vf-text-micro text-muted-foreground">Payback</p>
          <p className="vf-text-body-l font-bold">
            {result.payback_months} mo
          </p>
        </div>
        <div className="text-center p-3 bg-muted/50 rounded-md">
          <p className="vf-text-micro text-muted-foreground">3-Year ROI</p>
          <p className="vf-text-body-l font-bold text-primary">
            {formatPercent(result.total_roi_pct / 100)}
          </p>
        </div>
      </div>
    </SectionCard>
  );
}

// ── Benchmark Card ─────────────────────────────────────────────────────────────
function BenchmarkCard({ benchmark }: { benchmark: IndustryBenchmark | null }) {
  if (!benchmark) return null;
  return (
    <SectionCard title="Industry Benchmarks" className="mt-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 size={13} className="text-warning" />
        <span className="vf-text-caption text-muted-foreground">
          Sourced from the DIL Evidence Library — {benchmark.industry} (n={benchmark.sample_size})
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="px-3 py-2 border border-border rounded-md vf-text-body-s">
          <span className="vf-text-micro text-muted-foreground block">Avg ROI</span>
          <span className="font-bold">{benchmark.avg_roi_pct.toFixed(1)}%</span>
        </div>
        <div className="px-3 py-2 border border-border rounded-md vf-text-body-s">
          <span className="vf-text-micro text-muted-foreground block">Avg Payback</span>
          <span className="font-bold">{benchmark.avg_payback_months} mo</span>
        </div>
        <div className="px-3 py-2 border border-border rounded-md vf-text-body-s">
          <span className="vf-text-micro text-muted-foreground block">Avg NPV</span>
          <span className="font-bold">${(benchmark.avg_npv / 1000).toFixed(0)}K</span>
        </div>
      </div>
    </SectionCard>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function ValueModelTab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data, isLoading, error } = useWorkspaceTabQuery<{
    valueLines: ValueLine[];
  }>(caseId ?? null, "value-model");
  const { data: evidenceData } = useWorkspaceTabQuery<{ evidence: Array<{ id: string; title: string; decision_status?: string; provenance_id?: string }> }>(caseId ?? null, "evidence");
  const persistTab = usePersistWorkspaceTab("value-model");
  const [scenario, setScenario] = useState<Scenario>("expected");
  const [showStrategic, setShowStrategic] = useState(true);
  const [railMode, setRailMode] = useState<RightRailMode>("agent");

  // DIL data
  const calculateROI = useCalculateROI();
  const { data: benchmarksData } = useIndustryBenchmarks(
    account?.industry ?? null
  );
  const [roiResult, setRoiResult] = useState<ROICalculationResult | null>(null);

  useEffect(() => {
    if (caseId && data) persistTab.mutate({ caseId, payload: data });
  }, [caseId, data]);

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "value-model",
    accountName: account?.name ?? "Account",
  });

  const lines = data?.valueLines ?? [];
  const acceptedEvidence = (evidenceData?.evidence ?? []).filter((item) => item.decision_status === "accepted");
  const visibleLines = useMemo(
    () => (showStrategic ? lines : lines.filter((l) => l.category === "hard")),
    [showStrategic, lines]
  );
  const total = visibleLines.reduce((s, l) => s + l[scenario], 0);
  const benchmark = (benchmarksData as IndustryBenchmark | undefined) ?? null;

  const generateMutation = useGenerateWorkspaceIntelligence();

  useEffect(() => {
    if (
      caseId &&
      lines.length === 0 &&
      !isLoading &&
      !generateMutation.isPending
    ) {
      generateMutation.mutate(caseId);
    }
  }, [caseId, lines.length, isLoading]);

  // Auto-calculate ROI when value lines are available
  const handleCalculateROI = () => {
    if (total <= 0) return;
    calculateROI.mutate(
      {
        deal_size: total,
        annual_benefit: total,
        implementation_cost: total * 0.3,
        discount_rate: 0.1,
        time_horizon_years: 3,
        account_id: accountId,
      },
      {
        onSuccess: (data) => {
          setRoiResult(data as ROICalculationResult);
        },
      }
    );
  };

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading || isLoading || generateMutation.isPending) {
    return (
      <CenteredLoader
        message={
          generateMutation.isPending
            ? "Generating value model..."
            : "Loading value model…"
        }
      />
    );
  }
  if (error || generateMutation.isError) {
    return (
      <ErrorState
        title="Failed to load value model"
        description="The value model data could not be retrieved."
        error={error || generateMutation.error}
        fullPage
      />
    );
  }

  if (!account) {
    return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;
  }

  return (
    <ValueStudioShellComponent
      account={{
        accountName: account?.name ?? "Account",
        industry: account?.industry ?? "Unknown",
        revenue: account?.annual_revenue
          ? `$${account.annual_revenue.toLocaleString()}`
          : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="value-model"
          messages={messages}
          onSendMessage={sendMessage}
          suggestedActions={suggestedActions}
            steps={steps}
            isStreaming={isStreaming}
            runMetadata={metadata}
        />
      }
    >
      {lines.length === 0 ? (
        <SectionCard title="Value Breakdown">
          <div className="text-sm text-muted-foreground">
            No value-model output available yet.
          </div>
        </SectionCard>
      ) : (
        <>
          {/* Metrics row */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricCard
              label="Total Annual Value"
              value={formatCurrency(total)}
              trend={`${SCENARIO_LABELS[scenario]} scenario`}
            />
            <MetricCard
              label="Hard Savings"
              value={formatCurrency(
                lines
                  .filter((l) => l.category === "hard")
                  .reduce((s, l) => s + l[scenario], 0)
              )}
            />
            <MetricCard
              label="Strategic Value"
              value={formatCurrency(
                lines
                  .filter((l) => l.category === "strategic")
                  .reduce((s, l) => s + l[scenario], 0)
              )}
            />
            <MetricCard label="Value Lines" value={String(lines.length)} />
          </div>

          <SectionCard title="Accepted Evidence Inputs" className="mb-4">
            {acceptedEvidence.length === 0 ? (
              <div className="text-xs text-muted-foreground">No accepted evidence yet.</div>
            ) : (
              <div className="space-y-2">
                {acceptedEvidence.map((item) => (
                  <div key={item.id} className="text-xs border border-border rounded-md px-2 py-1">
                    <span className="font-semibold">{item.title}</span> · Linkage ID: {item.provenance_id ?? item.id}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

          {/* Scenario selector + controls */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-2">
              {(Object.keys(SCENARIO_LABELS) as Scenario[]).map((s) => (
                <Btn
                  key={s}
                  variant={scenario === s ? "primary" : "ghost"}
                  onClick={() => setScenario(s)}
                  className="vf-text-caption"
                >
                  {SCENARIO_LABELS[s]}
                </Btn>
              ))}
            </div>
            <div className="flex gap-3 items-center">
              <label className="text-xs">
                <input
                  type="checkbox"
                  checked={showStrategic}
                  onChange={(e) => setShowStrategic(e.target.checked)}
                />{" "}
                Include strategic value
              </label>
              <Btn
                variant="outline"
                className="gap-1.5"
                onClick={handleCalculateROI}
              >
                <Calculator size={12} />
                Calculate ROI
              </Btn>
              <Btn variant="outline" className="gap-1.5">
                <Settings2 size={12} />
                Variables
              </Btn>
            </div>
          </div>

          {/* Value breakdown table */}
          <SectionCard title="Value Breakdown">
            <div className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-3 py-2 vf-text-micro font-semibold text-muted-foreground border-b border-border">
              <span>Driver</span>
              <span>Conservative</span>
              <span>Expected</span>
              <span>Optimistic</span>
              <span>Source</span>
            </div>
            {visibleLines.map((line) => (
              <div
                key={line.id}
                className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-3 py-3 vf-text-body-s border-b border-border"
              >
                <span>{line.driver}</span>
                <span
                  className={cn(
                    scenario === "conservative" && "font-semibold text-primary"
                  )}
                >
                  {formatCurrency(line.conservative)}
                </span>
                <span
                  className={cn(
                    scenario === "expected" && "font-semibold text-primary"
                  )}
                >
                  {formatCurrency(line.expected)}
                </span>
                <span
                  className={cn(
                    scenario === "optimistic" && "font-semibold text-primary"
                  )}
                >
                  {formatCurrency(line.optimistic)}
                </span>
                <span className="vf-text-micro text-muted-foreground">
                  {line.source}
                </span>
              </div>
            ))}
          </SectionCard>

          {/* DIL ROI Analysis */}
          {roiResult && <ROISummaryCard result={roiResult} />}
          {calculateROI.isPending && (
            <div className="mt-4 text-sm text-muted-foreground flex items-center gap-2">
              <TrendingUp size={14} className="animate-pulse" />
              Calculating ROI...
            </div>
          )}

          {/* DIL Industry Benchmarks */}
          <BenchmarkCard benchmark={benchmark} />
        </>
      )}
    </ValueStudioShellComponent>
  );
}
