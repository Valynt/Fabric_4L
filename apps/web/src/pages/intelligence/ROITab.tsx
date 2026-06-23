/**
 * ROITab — ROI Calculator & Financial Projections
 *
 * TODO(dead-code): FABRIC-REM-001 — evaluate for removal; no runtime importer
 * currently references this file. The active ROI calculator tab uses
 * `apps/web/src/pages/calculator/ROITab.tsx`.
 *
 * DIL-backed tab wired to the ROI Calculator Service (L3).
 * Uses: useCalculateROI, useROITemplates, useIndustryBenchmarks from useROICalculator hook.
 *
 * Interactive calculator with scenario modeling (conservative/moderate/aggressive),
 * multi-year projections, and industry benchmarks.
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Calculator,
  DollarSign,
  TrendingUp,
  Loader2,
  ChevronDown,
  ChevronUp,
  Link,
} from "lucide-react";
import IntelligenceShell from "@/components/workspace/IntelligenceShell";
import RightRail, { type RightRailMode } from "@/components/workspace/RightRail";
import { useAgentEvents } from "@/agui";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { CenteredLoader } from "@/components/CenteredLoader";
import { useCanonicalCaseId, useWorkspaceTabQuery } from "@/hooks/useWorkspaceCase";
import { cn } from "@/lib/utils";
import {
  useCalculateROI,
  useROITemplates,
  useIndustryBenchmarks,
  type ROICalculationResult,
  type ScenarioResult,
  type AnnualProjection,
  type ROITemplate,
} from "@/hooks/useROICalculator";
import { SectionCard } from "@/components/blocks/SectionCard";
import { MetricCard } from "@/components/ui/fabric";
import { Input } from "@/components/ui/input";

function formatCurrency(val: number): string {
  if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (Math.abs(val) >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
  return `$${val.toLocaleString()}`;
}

function scenarioColor(scenario: string): string {
  switch (scenario) {
    case "conservative":
      return "text-warning";
    case "moderate":
      return "text-primary";
    case "aggressive":
      return "text-success";
    default:
      return "text-muted-foreground";
  }
}

interface ROIInputs {
  deal_size: number;
  implementation_cost: number;
  annual_benefit: number;
  time_horizon_years: number;
  discount_rate: number;
  ramp_months: number;
}

type AssumptionSupportStatus = "supported" | "partial" | "unsupported" | "unreviewed";

type WorkspaceAssumption = {
  id?: string;
  statement?: string;
  text?: string;
  support_status?: AssumptionSupportStatus;
  supportStatus?: AssumptionSupportStatus;
  evidence_ids?: string[];
  evidenceIds?: string[];
};

const DEFAULT_INPUTS: ROIInputs = {
  deal_size: 100000,
  implementation_cost: 50000,
  annual_benefit: 80000,
  time_horizon_years: 3,
  discount_rate: 10,
  ramp_months: 3,
};

const STATUS_STYLE: Record<AssumptionSupportStatus, string> = {
  supported: "border-success/30 bg-success/10 text-success",
  partial: "border-warning/30 bg-warning/10 text-warning",
  unsupported: "border-destructive/30 bg-destructive/10 text-destructive",
  unreviewed: "border-border bg-muted text-muted-foreground",
};

function InputField({
  label,
  value,
  onChange,
  prefix,
  suffix,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  prefix?: string;
  suffix?: string;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div className="space-y-1">
      <label className="vf-text-micro font-semibold text-muted-foreground">{label}</label>
      <div className="flex items-center gap-1">
        {prefix && <span className="text-xs text-muted-foreground">{prefix}</span>}
        <Input
          type="number"
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          min={min}
          max={max}
          step={step ?? 1}
          className="w-full text-xs font-mono"
        />
        {suffix && <span className="text-xs text-muted-foreground">{suffix}</span>}
      </div>
    </div>
  );
}

function ScenarioCard({
  label,
  result,
  isActive,
}: {
  label: string;
  result: ScenarioResult | undefined;
  isActive: boolean;
}) {
  if (!result) return null;

  return (
    <div
      className={cn(
        "space-y-2 rounded-md border p-3 transition-colors",
        isActive ? "border-primary bg-primary/5" : "border-border",
      )}
    >
      <div className="flex items-center justify-between">
        <span className={cn("text-xs font-bold", scenarioColor(label.toLowerCase()))}>{label}</span>
        <span className="text-lg font-bold">{Math.round(result.total_roi_pct)}%</span>
      </div>
      <div className="grid grid-cols-2 gap-2 vf-text-micro">
        <div>
          <span className="text-muted-foreground">NPV</span>
          <div className="font-semibold">{formatCurrency(result.npv)}</div>
        </div>
        <div>
          <span className="text-muted-foreground">IRR</span>
          <div className="font-semibold">{result.irr != null ? `${Math.round(result.irr * 100)}%` : "N/A"}</div>
        </div>
        <div>
          <span className="text-muted-foreground">Payback</span>
          <div className="font-semibold">{result.payback_months} months</div>
        </div>
        <div>
          <span className="text-muted-foreground">Multiplier</span>
          <div className="font-semibold">{result.multiplier}x</div>
        </div>
      </div>
    </div>
  );
}

function ProjectionTable({ projections }: { projections: AnnualProjection[] }) {
  if (!projections.length) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full vf-text-micro">
        <thead>
          <tr className="border-b border-border">
            <th className="py-1.5 text-left font-semibold text-muted-foreground">Year</th>
            <th className="py-1.5 text-right font-semibold text-muted-foreground">Benefit</th>
            <th className="py-1.5 text-right font-semibold text-muted-foreground">Cost</th>
            <th className="py-1.5 text-right font-semibold text-muted-foreground">Net</th>
            <th className="py-1.5 text-right font-semibold text-muted-foreground">Cumulative</th>
          </tr>
        </thead>
        <tbody>
          {projections.map((projection) => {
            const net = projection.benefit - projection.cost;
            return (
              <tr key={projection.year} className="border-b border-border/50">
                <td className="py-1.5 font-semibold">Year {projection.year}</td>
                <td className="text-right text-success">{formatCurrency(projection.benefit)}</td>
                <td className="text-right text-destructive">{formatCurrency(projection.cost)}</td>
                <td className={cn("text-right font-semibold", net >= 0 ? "text-success" : "text-destructive")}>
                  {formatCurrency(net)}
                </td>
                <td
                  className={cn(
                    "text-right font-semibold",
                    projection.cumulative_net >= 0 ? "text-success" : "text-destructive",
                  )}
                >
                  {formatCurrency(projection.cumulative_net)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function ROITab() {
  const { accountId } = useParams<{ accountId: string }>();
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const { data: caseId } = useCanonicalCaseId(accountId ?? null);
  const { data: evidenceData } = useWorkspaceTabQuery<{
    evidence: Array<{ id: string; title: string; decision_status?: string; provenance_id?: string }>;
  }>(caseId ?? null, "evidence");
  const { data: assumptionsData } = useWorkspaceTabQuery<{ assumptions: WorkspaceAssumption[] }>(
    caseId ?? null,
    "assumptions",
  );
  const { data: templates } = useROITemplates();
  const { data: benchmarks } = useIndustryBenchmarks(account?.industry ?? null);
  const calculateROI = useCalculateROI();

  const [inputs, setInputs] = useState<ROIInputs>(DEFAULT_INPUTS);
  const [activeScenario, setActiveScenario] = useState<string>("moderate");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [railMode, setRailMode] = useState<RightRailMode>("detail");

  const { messages, sendMessage, suggestedActions, steps, isStreaming, metadata } = useAgentEvents({
    activeTab: "roi",
    accountName: account?.name ?? "Account",
  });

  const result: ROICalculationResult | undefined = calculateROI.data;
  const acceptedEvidence = (evidenceData?.evidence ?? []).filter((item) => item.decision_status === "accepted");
  const assumptions = assumptionsData?.assumptions ?? [];
  const scenarios: Record<string, ScenarioResult> = result?.scenarios ?? {};
  const activeResult: ScenarioResult | undefined = scenarios[activeScenario];

  if (!accountId) {
    return <AccountRequiredGuard accountId={accountId} />;
  }

  if (accountLoading) {
    return <CenteredLoader message="Loading account…" />;
  }

  if (!account) {
    return <div className="p-6 text-sm text-destructive">Account not found.</div>;
  }

  return (
    <IntelligenceShell
      account={{
        accountName: account.name,
        industry: account.industry ?? "Unknown",
        revenue: account.annual_revenue ? `$${account.annual_revenue.toLocaleString()}` : "N/A",
      }}
      rightRail={
        <RightRail
          mode={railMode}
          onModeChange={setRailMode}
          activeTab="roi"
          detailContent={
            benchmarks ? (
              <div className="space-y-3">
                <h3 className="text-sm font-bold">Industry Benchmarks</h3>
                <p className="vf-text-micro text-muted-foreground">
                  {account.industry ?? "General"} industry averages
                </p>
                <div className="space-y-2 vf-text-micro">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Avg ROI</span>
                    <span className="font-semibold">
                      {benchmarks.avg_roi_pct != null ? `${Math.round(benchmarks.avg_roi_pct)}%` : "N/A"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Avg Payback</span>
                    <span className="font-semibold">
                      {benchmarks.avg_payback_months != null ? `${benchmarks.avg_payback_months} mo` : "N/A"}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Calculate ROI to view results and benchmarks.</div>
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
      <SectionCard title="Accepted Evidence Inputs" className="mb-4">
        {acceptedEvidence.length === 0 ? (
          <div className="text-xs text-muted-foreground">No accepted evidence linked yet.</div>
        ) : (
          <div className="space-y-1">
            {acceptedEvidence.map((item) => (
              <div key={item.id} className="text-xs">
                {item.title} · Linkage ID: {item.provenance_id ?? item.id}
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Assumption Support Trace" className="mb-4">
        {!assumptions.length ? (
          <div className="text-xs text-muted-foreground">No assumptions available for support tracing yet.</div>
        ) : (
          <div className="space-y-2">
            {assumptions.map((item, index) => {
              const support = item.support_status ?? item.supportStatus ?? "unreviewed";
              const linkedEvidence = (item.evidence_ids ?? item.evidenceIds ?? [])
                .map((evidenceId) => acceptedEvidence.find((evidence) => evidence.id === evidenceId))
                .filter((evidence): evidence is NonNullable<typeof evidence> => Boolean(evidence));
              return (
                <div key={item.id ?? `assumption-${index}`} className="rounded border border-border p-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium">{item.statement ?? item.text ?? "Untitled assumption"}</p>
                    <span
                      className={cn(
                        "rounded border px-1.5 py-0.5 vf-text-micro font-semibold capitalize",
                        STATUS_STYLE[support],
                      )}
                    >
                      {support}
                    </span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {linkedEvidence.length ? (
                      linkedEvidence.map((evidence) => (
                        <div key={evidence.id} className="flex items-center gap-1 vf-text-micro text-muted-foreground">
                          <Link size={10} />
                          <span>{evidence.title}</span>
                          <span>·</span>
                          <span>Artifact {evidence.provenance_id ?? evidence.id}</span>
                        </div>
                      ))
                    ) : (
                      <div className="vf-text-micro text-warning">No supporting evidence linked.</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>

      <SectionCard title="ROI Calculator" className="mb-4">
        <div className="mb-4 grid grid-cols-3 gap-4">
          <InputField
            label="Deal Size (ACV)"
            value={inputs.deal_size}
            onChange={(value) => setInputs((prev) => ({ ...prev, deal_size: value }))}
            prefix="$"
            min={0}
            step={10000}
          />
          <InputField
            label="Implementation Cost"
            value={inputs.implementation_cost}
            onChange={(value) => setInputs((prev) => ({ ...prev, implementation_cost: value }))}
            prefix="$"
            min={0}
            step={5000}
          />
          <InputField
            label="Annual Benefit"
            value={inputs.annual_benefit}
            onChange={(value) => setInputs((prev) => ({ ...prev, annual_benefit: value }))}
            prefix="$"
            min={0}
            step={5000}
          />
        </div>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="mb-3 flex items-center gap-1 vf-text-micro font-semibold text-muted-foreground hover:text-foreground"
        >
          {showAdvanced ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          Advanced Settings
        </button>

        {showAdvanced && (
          <div className="mb-4 grid grid-cols-3 gap-4">
            <InputField
              label="Time Horizon"
              value={inputs.time_horizon_years}
              onChange={(value) => setInputs((prev) => ({ ...prev, time_horizon_years: value }))}
              suffix="years"
              min={1}
              max={10}
            />
            <InputField
              label="Discount Rate"
              value={inputs.discount_rate}
              onChange={(value) => setInputs((prev) => ({ ...prev, discount_rate: value }))}
              suffix="%"
              min={0}
              max={50}
            />
            <InputField
              label="Ramp-up Period"
              value={inputs.ramp_months}
              onChange={(value) => setInputs((prev) => ({ ...prev, ramp_months: value }))}
              suffix="months"
              min={0}
              max={24}
            />
          </div>
        )}

        <button
          onClick={() => {
            calculateROI.mutate({
              deal_size: inputs.deal_size,
              implementation_cost: inputs.implementation_cost,
              annual_benefit: inputs.annual_benefit,
              time_horizon_years: inputs.time_horizon_years,
              discount_rate: inputs.discount_rate / 100,
              ramp_months: inputs.ramp_months,
              account_id: accountId,
            });
          }}
          disabled={calculateROI.isPending}
          className={cn(
            "inline-flex items-center gap-2 rounded-md px-4 py-2 text-xs font-semibold transition-colors",
            "bg-primary text-primary-foreground hover:bg-primary/90",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {calculateROI.isPending ? <Loader2 size={14} className="animate-spin" /> : <Calculator size={14} />}
          {calculateROI.isPending ? "Calculating…" : "Calculate ROI"}
        </button>
      </SectionCard>

      {result && (
        <>
          <div className="mb-4 grid grid-cols-3 gap-4">
            {["conservative", "moderate", "aggressive"].map((scenario) => (
              <button key={scenario} onClick={() => setActiveScenario(scenario)} className="text-left">
                <ScenarioCard
                  label={scenario.charAt(0).toUpperCase() + scenario.slice(1)}
                  result={scenarios[scenario]}
                  isActive={activeScenario === scenario}
                />
              </button>
            ))}
          </div>

          {activeResult && (
            <div className="mb-4 grid grid-cols-4 gap-4">
              <MetricCard label="ROI" value={`${Math.round(activeResult.total_roi_pct)}%`} />
              <MetricCard label="NPV" value={formatCurrency(activeResult.npv)} />
              <MetricCard label="Payback Period" value={`${activeResult.payback_months} mo`} />
              <MetricCard label="Multiplier" value={`${activeResult.multiplier}x`} />
            </div>
          )}

          {result.annual_projections && result.annual_projections.length > 0 && (
            <SectionCard title="Multi-Year Projections" className="mb-4">
              <ProjectionTable projections={result.annual_projections} />
            </SectionCard>
          )}
        </>
      )}

      {templates && templates.length > 0 && (
        <SectionCard title="Saved Templates">
          <div className="space-y-1">
            {templates.map((template: ROITemplate) => (
              <button
                key={template.id}
                onClick={() => {
                  if (template.defaults) {
                    setInputs({
                      deal_size: template.defaults.deal_size ?? DEFAULT_INPUTS.deal_size,
                      implementation_cost: template.defaults.implementation_cost ?? DEFAULT_INPUTS.implementation_cost,
                      annual_benefit: template.defaults.annual_benefit ?? DEFAULT_INPUTS.annual_benefit,
                      time_horizon_years: template.defaults.time_horizon_years ?? DEFAULT_INPUTS.time_horizon_years,
                      discount_rate: (template.defaults.discount_rate ?? 0.1) * 100,
                      ramp_months: template.defaults.ramp_months ?? DEFAULT_INPUTS.ramp_months,
                    });
                  }
                }}
                className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left hover:bg-muted/50"
              >
                <Calculator size={12} className="text-muted-foreground" />
                <div className="flex-1">
                  <div className="text-xs font-medium">{template.name}</div>
                  <div className="vf-text-micro text-muted-foreground">{template.description}</div>
                </div>
              </button>
            ))}
          </div>
        </SectionCard>
      )}

      {!result && !calculateROI.isPending && (
        <SectionCard title="Financial Projections">
          <div className="py-8 text-center">
            <DollarSign size={32} className="mx-auto mb-3 text-muted-foreground" />
            <p className="mb-2 text-sm text-muted-foreground">
              Enter your parameters above and click &quot;Calculate ROI&quot; to generate projections.
            </p>
            <p className="text-xs text-muted-foreground">
              Three scenarios (conservative, moderate, aggressive) with NPV, IRR, and payback analysis.
            </p>
          </div>
        </SectionCard>
      )}
    </IntelligenceShell>
  );
}
