/**
 * ROITab — ROI Calculator
 *
 * Workspace tab for the Calculator workspace.
 */
import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { Calculator, Loader2, RefreshCcw, Save } from "lucide-react";
import { useAccount } from "@/hooks/useAccounts";
import { AccountRequiredGuard } from "@/components/AccountRequiredGuard";
import { LoadingState, ErrorState } from "@/components/states";
import { QK } from "@/hooks/queryKeys";
import { useValueLevers } from "@/hooks/useCalculators";
import { useBenchmarksList, useCalculateROI, useIndustryBenchmarks, type ROICalculationRequest } from "@/hooks/useROICalculator";
import { useValuePacks } from "@/hooks/useValuePacks";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useWorkspaceSelectionStore } from "@/stores/workspaceSelectionStore";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Input } from "@/components/ui/input";
import { MetricCard } from "@/components/ui/fabric";
import type { StudioTabProps } from "@/features/value-studio/types";

type ScenarioState = {
  deal_size: number;
  implementation_cost: number;
  annual_benefit: number;
  time_horizon_years: number;
  discount_rate: number;
  ramp_months: number;
};

type PersistedScenarioVersion = {
  versionId: string;
  accountId: string;
  caseId: string;
  modelId: string;
  name: string;
  assumptions: ScenarioState;
  updatedAt: string;
};

const DEFAULT_SCENARIO: ScenarioState = {
  deal_size: 120000,
  implementation_cost: 60000,
  annual_benefit: 100000,
  time_horizon_years: 3,
  discount_rate: 10,
  ramp_months: 3,
};

const STORAGE_KEY = "vf.roi.scenario_versions.v1";

function fmtCurrency(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

export default function CalcROITab({ accountId }: StudioTabProps) {
  const location = useLocation();
  const setSelection = useWorkspaceSelectionStore((state) => state.setSelection);
  const getSelection = useWorkspaceSelectionStore((state) => state.getSelection);
  const { data: account, isLoading: accountLoading } = useAccount(accountId ?? null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [modelId, setModelId] = useState<string | null>(null);
  const [scenario, setScenario] = useState<ScenarioState>(DEFAULT_SCENARIO);


  useEffect(() => {
    if (!accountId) return;
    const params = new URLSearchParams(location.search);
    const queryModelId = params.get("value_model_id") || null;
    const queryTreeId = params.get("tree_id") || null;
    if (queryModelId || queryTreeId) {
      setSelection(accountId, { valueModelId: queryModelId, treeId: queryTreeId });
      if (queryModelId) setModelId(queryModelId);
      if (queryTreeId) setCaseId(queryTreeId);
      return;
    }
    const persisted = getSelection(accountId);
    if (persisted.valueModelId) setModelId(persisted.valueModelId);
    if (persisted.treeId) setCaseId(persisted.treeId);
  }, [accountId, location.search, getSelection, setSelection]);

  const queryClient = useQueryClient();
  const { data: leverData, isLoading: leversLoading, error: leverError } = useValueLevers({ industry: account?.industry ?? undefined });
  const { data: assumptions, isLoading: assumptionsLoading } = useIndustryBenchmarks(account?.industry ?? null);
  const { data: allAssumptions } = useBenchmarksList();
  const { data: packs } = useValuePacks({});
  const recalcMutation = useCalculateROI();

  const scenarioKey = useMemo(
    () => ["calculator", "roi", "scenario", accountId ?? "", caseId ?? "case-default", modelId ?? "model-default"] as const,
    [accountId, caseId, modelId]
  );

  const versionsQuery = useQuery<PersistedScenarioVersion[]>({
    queryKey: scenarioKey,
    enabled: Boolean(accountId),
    queryFn: async () => {
      const raw = localStorage.getItem(STORAGE_KEY);
      const all: PersistedScenarioVersion[] = raw ? JSON.parse(raw) : [];
      return all.filter((entry) => entry.accountId === accountId && entry.caseId === (caseId ?? "case-default") && entry.modelId === (modelId ?? "model-default"));
    },
  });

  const saveScenarioMutation = useMutation({
    mutationKey: ["calculator", "roi", "scenario", "save"],
    mutationFn: async (name: string) => {
      const raw = localStorage.getItem(STORAGE_KEY);
      const all: PersistedScenarioVersion[] = raw ? JSON.parse(raw) : [];
      const entry: PersistedScenarioVersion = {
        versionId: `sv_${Date.now()}`,
        accountId: accountId ?? "",
        caseId: caseId ?? "case-default",
        modelId: modelId ?? "model-default",
        name,
        assumptions: scenario,
        updatedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify([entry, ...all]));
      return entry;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scenarioKey });
    },
  });

  const updateScenarioMutation = useMutation({
    mutationKey: ["calculator", "roi", "scenario", "edit"],
    mutationFn: async (next: Partial<ScenarioState>) => {
      const updated = { ...scenario, ...next };
      setScenario(updated);
      return updated;
    },
    onSuccess: async (updated) => {
      if (!accountId) return;
      await recalcMutation.mutateAsync({ ...updated, account_id: accountId } as ROICalculationRequest);
      queryClient.invalidateQueries({ queryKey: QK.roi.list({ account_id: accountId }) });
      queryClient.invalidateQueries({ queryKey: QK.roi.all });
    },
  });

  useEffect(() => {
    const latest = versionsQuery.data?.[0];
    if (latest) {
      setScenario(latest.assumptions);
    }
  }, [versionsQuery.data]);

  if (!accountId) return <AccountRequiredGuard accountId={accountId} />;
  if (accountLoading) return <LoadingState message="Loading account…" fullPage />;
  if (!account) return <ErrorState title="Account not found" description="Select a valid account to continue in this workspace." fullPage />;

  const calc = recalcMutation.data;
  const scenarioNames = Object.keys(calc?.scenarios ?? {});

  return (
    <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Calculator className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">ROI Calculator</h2>
            <p className="text-sm text-muted-foreground">Scenario assumptions, value levers, and traceable formula outcomes.</p>
            <p className="text-xs text-muted-foreground">Selected tree: {caseId ?? "None"} · Selected model: {modelId ?? "None"}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <MetricCard label="Conservative" value={calc?.scenarios?.conservative ? `${Math.round(calc.scenarios.conservative.total_roi_pct)}%` : "—"} />
          <MetricCard label="Moderate" value={calc?.scenarios?.moderate ? `${Math.round(calc.scenarios.moderate.total_roi_pct)}%` : "—"} />
          <MetricCard label="Aggressive" value={calc?.scenarios?.aggressive ? `${Math.round(calc.scenarios.aggressive.total_roi_pct)}%` : "—"} />
        </div>

        <SectionCard title="Scenario assumptions">
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(scenario).map(([k, v]) => (
              <label key={k} className="space-y-1">
                <span className="text-xs text-muted-foreground">{k.replaceAll("_", " ")}</span>
                <Input type="number" value={v} onChange={(e) => updateScenarioMutation.mutate({ [k]: Number(e.target.value) } as Partial<ScenarioState>)} className="w-full text-xs" />
              </label>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <button onClick={() => saveScenarioMutation.mutate(`Version ${new Date().toLocaleString()}`)} className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 hover:bg-muted" disabled={saveScenarioMutation.isPending}>
              <Save className="h-3.5 w-3.5" /> Save version
            </button>
            <button onClick={() => recalcMutation.mutate({ ...scenario, account_id: accountId })} className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 hover:bg-muted" disabled={recalcMutation.isPending}>
              {recalcMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCcw className="h-3.5 w-3.5" />} Recalculate
            </button>
            {updateScenarioMutation.isPending && <span className="text-muted-foreground">Updating assumptions…</span>}
            {recalcMutation.isError && <span className="text-destructive">Failed to recalculate scenario.</span>}
            {saveScenarioMutation.isError && <span className="text-destructive">Failed to persist scenario version.</span>}
          </div>
        </SectionCard>

        <SectionCard title="Value model drivers and levers">
          {leversLoading ? <p className="text-sm text-muted-foreground">Loading value levers…</p> : leverError ? <p className="text-sm text-destructive">Failed to load value levers.</p> : (
            <div className="space-y-2">
              {(leverData?.levers ?? []).map((lever) => {
                const mappedPack = packs?.find((p) => p.name.toLowerCase().includes(lever.category.toLowerCase()));
                return (
                  <div key={lever.id} className="rounded border border-border p-2 text-xs">
                    <div className="font-medium">{lever.name}</div>
                    <div className="text-muted-foreground">Driver: {lever.category} · Formula var: <code>{lever.id}</code></div>
                    <div className="text-muted-foreground">Mapped value pack: {mappedPack?.name ?? "Unmapped"}</div>
                  </div>
                );
              })}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Trace / explain">
          <div className="space-y-2 text-xs">
            <p className="text-muted-foreground">Changed assumptions are reflected in scenario outputs and benchmarks.</p>
            <p>Total NPV: <span className="font-semibold">{calc ? fmtCurrency(calc.npv) : "—"}</span></p>
            <p>Benchmark ROI ({account.industry ?? "Industry"}): <span className="font-semibold">{assumptions ? `${Math.round(assumptions.avg_roi_pct)}%` : assumptionsLoading ? "Loading…" : "N/A"}</span></p>
            <p>Loaded assumption sets: <span className="font-semibold">{allAssumptions?.benchmarks.length ?? 0}</span></p>
            <p>Calculated scenarios: <span className="font-semibold">{scenarioNames.join(", ") || "None yet"}</span></p>
          </div>
        </SectionCard>

        <SectionCard title="Saved scenario versions (reload/resume)">
          <div className="space-y-2">
            {(versionsQuery.data ?? []).map((version) => (
              <button key={version.versionId} onClick={() => setScenario(version.assumptions)} className="w-full rounded border border-border p-2 text-left text-xs hover:bg-muted">
                <div className="font-medium">{version.name}</div>
                <div className="text-muted-foreground">{version.accountId} / {version.caseId} / {version.modelId}</div>
              </button>
            ))}
            {!versionsQuery.data?.length && <p className="text-xs text-muted-foreground">No versions saved for this account/case/model.</p>}
          </div>
        </SectionCard>
    </div>
  );
}
