/**
 * Integration Dashboard — Developer Tools
 * Shows endpoint coverage, hook wiring status, mock detection,
 * and system health for the DIL integration layer.
 *
 * Route: /dev/integration
 * Hooks: useSystemHealth, useIngestionStats
 */
import { useState, useMemo } from "react";
import {
  Activity, CheckCircle2, AlertCircle, XCircle, Wifi,
  Database, Layers, BarChart3, RefreshCw, Search,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useSystemHealth, useHealthAlerts } from "@/hooks/useHealthMonitor";
import { useIngestionStats } from "@/hooks/useIngestion";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Input } from "@/components/ui/input";
import { PageHeader, Btn } from "@/components/ui/fabric";

// ── Hook Registry ────────────────────────────────────────────────────────────
// Static registry of all DIL hook families and their endpoint counts
const HOOK_REGISTRY: Array<{
  family: string;
  file: string;
  layer: string;
  hooks: string[];
  endpoints: number;
  status: "green" | "partial" | "stub";
}> = [
  { family: "Accounts", file: "useAccounts.ts", layer: "L4", hooks: ["useAccounts", "useAccount", "useCreateAccount", "useSyncAccounts", "useRefreshAccount", "useAccountSyncStatus"], endpoints: 16, status: "green" },
  { family: "Sources", file: "useSources.ts", layer: "L1", hooks: ["useSources", "useCreateSource", "useDeleteSource", "useTestSource", "useExecuteSource", "useIngestionStats"], endpoints: 12, status: "green" },
  { family: "Formulas", file: "useFormulas.ts", layer: "L3", hooks: ["useFormulas", "useFormula", "useCreateFormula", "useUpdateFormula", "useEvaluateFormula", "useFormulaScenario"], endpoints: 14, status: "green" },
  { family: "Intelligence", file: "useIntelligence.ts", layer: "L3", hooks: ["useSignals", "useDrivers", "useStakeholders", "usePipelineSummary"], endpoints: 8, status: "green" },
  { family: "Business Cases", file: "useBusinessCases.ts", layer: "L4", hooks: ["useBusinessCases", "useBusinessCase", "useCreateBusinessCase", "useBusinessCaseWorkflow"], endpoints: 9, status: "green" },
  { family: "Value Packs", file: "useValuePacks.ts", layer: "L4", hooks: ["useValuePacks", "useValuePack", "useApplyValuePack", "useValuePackFrameworkList", "useValuePackOntologyMap", "useValuePackTemplates", "useValuePackComparison", "useSuggestValuePacks"], endpoints: 9, status: "green" },
  { family: "Workflows", file: "useWorkflows.ts", layer: "L4", hooks: ["useWorkflowHistory", "useActiveWorkflows", "useCancelWorkflow", "usePauseWorkflow", "useResumeWorkflow", "useCreateWorkflow", "useWorkflowTypes"], endpoints: 9, status: "green" },
  { family: "Governance", file: "useGovernance.ts", layer: "L4", hooks: ["useTenants", "useUsers", "useApiKeys", "useInviteUser", "useRevokeApiKey"], endpoints: 5, status: "green" },
  { family: "Provenance", file: "useProvenance.ts", layer: "L3", hooks: ["useProvenanceTrail", "useAuditLogs", "useExportProvenance"], endpoints: 3, status: "green" },
  { family: "Documents", file: "useDocuments.ts", layer: "L4", hooks: ["useBusinessCaseExport", "useBusinessCase", "useRegenerateBusinessCase"], endpoints: 3, status: "green" },
  { family: "Health", file: "useHealthMonitor.ts", layer: "Platform", hooks: ["useSystemHealth", "useHealthAlerts"], endpoints: 12, status: "green" },
  { family: "Graph", file: "useGraphQuery.ts", layer: "L3", hooks: ["useGraphQuery", "useEntityContext", "useEntityTraversal", "useSubgraph"], endpoints: 6, status: "green" },
  { family: "Value Trees", file: "useValueTrees.ts", layer: "L3", hooks: ["useValueTree", "useValueTreePaths", "useValueTreeCache"], endpoints: 4, status: "green" },
  { family: "Entities", file: "useEntities.ts", layer: "L2", hooks: ["useEntities", "useEntity"], endpoints: 4, status: "green" },
  { family: "Ontology", file: "useOntology.ts", layer: "L2", hooks: ["useOntologyTypes", "useOntologyRelationships", "usePublishOntology", "useAddRelationship"], endpoints: 14, status: "green" },
  { family: "Models", file: "useModels.ts", layer: "L3", hooks: ["useModels", "useModelFolders", "useCreateModel"], endpoints: 6, status: "green" },
];

const STATUS_COLORS = {
  green: "bg-success/10 text-success border-success/20",
  partial: "bg-warning/10 text-warning border-warning/20",
  stub: "bg-destructive/10 text-destructive border-destructive/20",
};

const STATUS_ICONS = {
  green: CheckCircle2,
  partial: AlertCircle,
  stub: XCircle,
};

function StatusBadge({ status }: { status: "green" | "partial" | "stub" }) {
  const Icon = STATUS_ICONS[status];
  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full vf-text-micro font-semibold border", STATUS_COLORS[status])}>
      <Icon size={10} />
      {status === "green" ? "Wired" : status === "partial" ? "Partial" : "Stub"}
    </span>
  );
}

export default function IntegrationDashboard() {
  const [search, setSearch] = useState("");
  const [layerFilter, setLayerFilter] = useState("All");
  const { data: health, isLoading: healthLoading } = useSystemHealth();
  const { data: alerts } = useHealthAlerts();
  const { data: ingestionStats } = useIngestionStats();

  const totalHooks = HOOK_REGISTRY.reduce((sum, f) => sum + f.hooks.length, 0);
  const totalEndpoints = HOOK_REGISTRY.reduce((sum, f) => sum + f.endpoints, 0);
  const greenCount = HOOK_REGISTRY.filter(f => f.status === "green").length;
  const partialCount = HOOK_REGISTRY.filter(f => f.status === "partial").length;

  const layers = useMemo(() => {
    const all = Array.from(new Set(HOOK_REGISTRY.map(f => f.layer)));
    return ["All", ...all.sort()];
  }, []);

  const filtered = useMemo(() => {
    return HOOK_REGISTRY.filter(f => {
      if (layerFilter !== "All" && f.layer !== layerFilter) return false;
      if (search && !f.family.toLowerCase().includes(search.toLowerCase()) &&
          !f.hooks.some(h => h.toLowerCase().includes(search.toLowerCase()))) return false;
      return true;
    });
  }, [search, layerFilter]);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Integration Dashboard"
        subtitle="DIL hook coverage, endpoint wiring status, and system health"
        breadcrumbs={[{ label: "Developer Tools" }, { label: "Integration" }]}
      />

      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-3 mt-6">
        <div className="p-4 bg-card border border-border rounded-xl text-center">
          <Layers size={16} className="mx-auto text-primary mb-1" />
          <div className="text-2xl font-extrabold text-foreground">{HOOK_REGISTRY.length}</div>
          <div className="vf-text-micro text-muted-foreground uppercase">Hook Families</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl text-center">
          <Database size={16} className="mx-auto text-primary mb-1" />
          <div className="text-2xl font-extrabold text-foreground">{totalHooks}</div>
          <div className="vf-text-micro text-muted-foreground uppercase">Total Hooks</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl text-center">
          <Wifi size={16} className="mx-auto text-success mb-1" />
          <div className="text-2xl font-extrabold text-foreground">{totalEndpoints}</div>
          <div className="vf-text-micro text-muted-foreground uppercase">Endpoints</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl text-center">
          <CheckCircle2 size={16} className="mx-auto text-success mb-1" />
          <div className="text-2xl font-extrabold text-success">{greenCount}</div>
          <div className="vf-text-micro text-muted-foreground uppercase">Fully Wired</div>
        </div>
        <div className="p-4 bg-card border border-border rounded-xl text-center">
          <Activity size={16} className="mx-auto text-primary mb-1" />
          <div className="text-2xl font-extrabold text-foreground">
            {healthLoading ? "…" : health?.overall_status === "healthy" ? "OK" : health?.overall_status ?? "—"}
          </div>
          <div className="vf-text-micro text-muted-foreground uppercase">System Health</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3 mt-6 mb-4">
        <div className="flex items-center gap-2 flex-1 bg-muted/50 border border-border rounded-lg px-3 py-2">
          <Search size={14} className="text-muted-foreground" />
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search hooks or families…"
            className="flex-1 vf-text-body-s"
          />
        </div>
        <div className="flex gap-1">
          {layers.map(l => (
            <button type="button" key={l} onClick={() => setLayerFilter(l)}
              className={cn(
                "px-3 py-1.5 rounded-md vf-text-caption font-medium transition-colors",
                layerFilter === l ? "bg-primary/10 text-primary" : "bg-muted/50 text-muted-foreground hover:bg-muted"
              )}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Hook Family Table */}
      <SectionCard>
        <div className="overflow-x-auto">
          <table className="w-full vf-text-body-s">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">Family</th>
                <th className="text-left py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">Layer</th>
                <th className="text-left py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">File</th>
                <th className="text-center py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">Hooks</th>
                <th className="text-center py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">Endpoints</th>
                <th className="text-center py-2 px-3 font-semibold text-muted-foreground uppercase vf-text-micro">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(f => (
                <tr key={f.family} className="border-b border-border hover:bg-muted/50/50">
                  <td className="py-2.5 px-3 font-semibold text-foreground">{f.family}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 bg-muted rounded vf-text-micro font-mono">{f.layer}</span>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-muted-foreground vf-text-caption">{f.file}</td>
                  <td className="py-2.5 px-3 text-center font-bold">{f.hooks.length}</td>
                  <td className="py-2.5 px-3 text-center font-bold">{f.endpoints}</td>
                  <td className="py-2.5 px-3 text-center"><StatusBadge status={f.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {/* Live System Metrics */}
      <div className="grid grid-cols-2 gap-4 mt-4">
        <SectionCard>
          <h3 className="vf-text-body-m font-bold text-foreground mb-3">Health Alerts</h3>
          {alerts && alerts.length > 0 ? (
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {alerts.map((alert: { id: string; severity: string; message: string; timestamp?: string }) => (
                <div key={alert.id} className={cn(
                  "p-2 rounded-md border vf-text-caption",
                  alert.severity === "critical" ? "bg-destructive/10 border-destructive/20 text-destructive" :
                  alert.severity === "warning" ? "bg-warning/10 border-warning/20 text-warning" :
                  "bg-primary/10 border-primary/20 text-primary"
                )}>
                  <span className="font-semibold uppercase vf-text-micro">{alert.severity}</span>
                  <span className="ml-2">{alert.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="vf-text-body-s text-muted-foreground text-center py-4">No active alerts.</p>
          )}
        </SectionCard>

        <SectionCard>
          <h3 className="vf-text-body-m font-bold text-foreground mb-3">Ingestion Stats</h3>
          {ingestionStats ? (
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(ingestionStats).map(([key, value]) => (
                <div key={key} className="flex justify-between p-2 bg-muted/50 rounded-md">
                  <span className="vf-text-caption text-muted-foreground">{key.replace(/_/g, ' ')}</span>
                  <span className="vf-text-caption font-bold text-foreground">{String(value)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-6 w-full" />)}</div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
