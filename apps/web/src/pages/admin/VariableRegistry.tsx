/**
 * VariableRegistry — Admin Tier 3 Page
 * 
 * Variable catalog and binding management:
 * - Variable Catalog (view all variable definitions)
 * - Source Bindings (manage data source connections)
 * 
 * Features:
 * - Type system management
 * - Source binding configuration
 * - Validation rules
 * - Usage tracking
 */

import { useState, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
  ListChecks, Plus, Search, Filter, Edit3, Trash2, Eye, Link2,
  CheckCircle2, AlertCircle, Database, Code2, Hash, DollarSign,
  Percent, Type, Settings, ChevronRight, ChevronDown, Download,
  Upload, RefreshCw, ExternalLink, Check, X
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import ErrorBoundary from "@/components/ErrorBoundary";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useVariables,
  useSourceBindings,
  useVariableStats,
  useTestVariableBinding,
  type TestVariableBindingResponse,
  type Variable,
  type SourceBinding,
  type VariableType,
  type SourceType,
  type ValidationStatus,
} from "@/hooks/useVariables";
import { PageHeader, Btn } from "@/components/ui/fabric";

// ── Styling Constants ───────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<VariableType, { label: string; color: string; icon: React.ReactNode }> = {
  rate:     { label: "Rate",     color: "bg-cyan-50 text-cyan-700",     icon: <Percent size={10}/> },
  currency: { label: "Currency", color: "bg-success/10 text-success", icon: <DollarSign size={10}/> },
  integer:  { label: "Integer",  color: "bg-primary/10 text-primary",     icon: <Hash size={10}/> },
  float:    { label: "Float",    color: "bg-violet-50 text-violet-700",  icon: <Code2 size={10}/> },
  boolean:  { label: "Boolean",  color: "bg-warning/10 text-warning",    icon: <Check size={10}/> },
  string:   { label: "String",   color: "bg-muted text-muted-foreground", icon: <Type size={10}/> },
};

const SOURCE_CONFIG: Record<SourceType, { color: string; icon: React.ReactNode }> = {
  CRM:      { color: "bg-primary/10 text-primary", icon: <Database size={10}/> },
  Billing:  { color: "bg-violet-50 text-violet-700", icon: <DollarSign size={10}/> },
  ERP:      { color: "bg-indigo-50 text-indigo-700", icon: <Database size={10}/> },
  Manual:   { color: "bg-muted text-muted-foreground", icon: <Type size={10}/> },
  Model:    { color: "bg-warning/10 text-warning", icon: <Code2 size={10}/> },
  API:      { color: "bg-cyan-50 text-cyan-700", icon: <ExternalLink size={10}/> },
  Database: { color: "bg-success/10 text-success", icon: <Database size={10}/> },
};

const VALIDATION_CONFIG: Record<ValidationStatus, { color: string; icon: React.ReactNode; label: string }> = {
  validated:  { color: "text-success", icon: <CheckCircle2 size={14}/>, label: "Validated" },
  pending:    { color: "text-warning", icon: <AlertCircle size={14}/>, label: "Pending" },
  failed:     { color: "text-destructive", icon: <X size={14}/>, label: "Failed" },
  deprecated: { color: "text-muted-foreground", icon: <AlertCircle size={14}/>, label: "Deprecated" },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function TypeBadge({ type }: { type: VariableType }) {
  const config = TYPE_CONFIG[type];
  return (
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full ${config.color}`}>
      {config.icon} {config.label}
    </span>
  );
}

function SourceBadge({ source }: { source: SourceType }) {
  const config = SOURCE_CONFIG[source];
  return (
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full ${config.color}`}>
      {config.icon} {source}
    </span>
  );
}

function ValidationIcon({ status }: { status: ValidationStatus }) {
  const config = VALIDATION_CONFIG[status];
  return <span className={config.color} title={config.label}>{config.icon}</span>;
}

function BindingCard({ binding, onTest }: { binding: SourceBinding; onTest: (id: string) => void }) {
  const statusColors: Record<string, string> = {
    connected: "bg-success/10 text-success border-success/20",
    disconnected: "bg-muted text-muted-foreground border-border",
    error: "bg-destructive/10 text-destructive border-destructive/20",
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
            <Database size={18}/>
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">{binding.name}</h4>
            <p className="vf-text-caption text-muted-foreground font-mono">{binding.connection_string || "—"}</p>
          </div>
        </div>
        <span className={`vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${statusColors[binding.status]}`}>
          {binding.status}
        </span>
      </div>
      
      <div className="flex items-center justify-between vf-text-caption">
        <div className="flex items-center gap-4">
          <span className="text-muted-foreground">
            <span className="font-semibold text-foreground">{binding.variables_bound}</span> variables bound
          </span>
          {binding.last_sync && (
            <span className="text-muted-foreground">
              Last sync: {new Date(binding.last_sync).toLocaleString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onTest(binding.id)}
            className="flex items-center gap-1 px-2.5 py-1 vf-text-micro font-medium text-muted-foreground hover:bg-muted rounded transition-colors"
          >
            <RefreshCw size={10}/> Test
          </button>
          <button className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors" aria-label="Binding settings">
            <Settings size={12}/>
          </button>
        </div>
      </div>
      
      {binding.error_message && (
        <div className="mt-3 p-2 bg-destructive/10 border border-destructive/20 rounded-lg vf-text-caption text-destructive">
          {binding.error_message}
        </div>
      )}
    </div>
  );
}

function VariableRegistrySkeleton() {
  return (
    <PageShell>
      <div className="flex items-start justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-36" />
        </div>
      </div>

      {/* Stats Row Skeleton */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="bg-card border border-border rounded-xl px-4 py-3">
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
      </div>

      {/* Table Skeleton */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="bg-muted/50 border-b border-border px-4 py-3 flex gap-4">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="px-4 py-4 border-b border-border flex gap-4">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </PageShell>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

type TabType = "catalog" | "bindings";

function VariableRegistryContent() {
  const { pathname: location } = useLocation();
  const initialTab: TabType = location.includes("/bindings") ? "bindings" : "catalog";
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | VariableType>("all");
  const [sourceFilter, setSourceFilter] = useState<"all" | SourceType>("all");
  const [expandedVariable, setExpandedVariable] = useState<string | null>(null);
  const [testResultsByVariable, setTestResultsByVariable] = useState<Record<string, TestVariableBindingResponse>>({});
  const [expandedDiagnosticsByVariable, setExpandedDiagnosticsByVariable] = useState<Record<string, boolean>>({});
  const [activeTestVariableId, setActiveTestVariableId] = useState<string | null>(null);

  const { 
    data: variables = [], 
    isLoading: variablesLoading, 
    error: variablesError,
    refetch: refetchVariables
  } = useVariables({
    type: typeFilter === "all" ? undefined : typeFilter,
    source: sourceFilter === "all" ? undefined : sourceFilter,
    search: search || undefined,
  });

  const { 
    data: bindings = [], 
    isLoading: bindingsLoading,
    error: bindingsError,
    refetch: refetchBindings
  } = useSourceBindings();

  const { data: stats } = useVariableStats();
  const testVariableBinding = useTestVariableBinding();

  const filteredVariables = useMemo(() => {
    return variables.filter(v =>
      (typeFilter === "all" || v.type === typeFilter) &&
      (sourceFilter === "all" || v.source === sourceFilter) &&
      (search === "" || 
       v.name.toLowerCase().includes(search.toLowerCase()) ||
       v.display_name.toLowerCase().includes(search.toLowerCase()))
    );
  }, [variables, typeFilter, sourceFilter, search]);

  const isLoading = variablesLoading || bindingsLoading;
  const error = variablesError || bindingsError;

  const handleTestBinding = async (variable: Variable) => {
    setActiveTestVariableId(variable.variable_id);
    try {
      const result = await testVariableBinding.mutateAsync({
        variableId: variable.variable_id,
        payload: {
          sample_input: {
            tenant_id: "demo-tenant",
            effective_at: new Date().toISOString(),
          },
          context: {
            trigger: "admin-variable-registry",
            source: variable.source,
            binding: variable.binding,
          },
        },
      });
      setTestResultsByVariable(prev => ({ ...prev, [variable.variable_id]: result }));
    } finally {
      setActiveTestVariableId(null);
    }
  };

  if (isLoading) {
    return (
      <PageShell>
        <VariableRegistrySkeleton />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load variable registry"
          description="An error occurred while loading variable data."
          error={error}
          onRetry={() => { refetchVariables(); refetchBindings(); }}
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Variable Registry"
          subtitle="Catalog of all formula variables — definitions, source bindings, type system, and validation rules."
        />
        <div className="flex items-center gap-2">
          <Btn variant="outline"><Upload size={13} className="mr-1"/> Import</Btn>
          <Btn variant="primary"><Plus size={13} className="mr-1"/> Register Variable</Btn>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        {[
          { label: "Total Variables", value: stats?.total ?? variables.length, icon: <ListChecks size={14}/> },
          { label: "Validated", value: stats?.validated ?? variables.filter(v => v.validation_status === "validated").length, icon: <CheckCircle2 size={14}/>, color: "text-success" },
          { label: "Pending", value: stats?.pending ?? variables.filter(v => v.validation_status === "pending").length, icon: <AlertCircle size={14}/>, color: "text-warning" },
          { label: "Failed", value: stats?.failed ?? variables.filter(v => v.validation_status === "failed").length, icon: <X size={14}/>, color: "text-destructive" },
          { label: "Total Usage", value: stats?.avg_usage ?? variables.reduce((s, v) => s + (v.used_in_count || 0), 0), icon: <Link2 size={14}/>, color: "text-primary" },
        ].map(s => (
          <div key={s.label} className="bg-card border border-border rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={s.color || "text-muted-foreground"}>{s.icon}</span>
              <span className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">{s.label}</span>
            </div>
            <p className={`text-[22px] font-extrabold ${s.color || "text-foreground"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border mb-4">
        {[
          { id: "catalog" as const, label: "Variable Catalog", count: variables.length },
          { id: "bindings" as const, label: "Source Bindings", count: bindings.length },
        ].map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2.5 vf-text-body-s font-medium transition-colors relative",
              activeTab === tab.id
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="flex items-center gap-2">
              {tab.label}
              {tab.count !== undefined && (
                <span className={cn(
                  "px-1.5 py-0.5 rounded vf-text-micro",
                  activeTab === tab.id ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                )}>
                  {tab.count}
                </span>
              )}
            </span>
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
            )}
          </button>
        ))}
      </div>

      {activeTab === "catalog" ? (
        <>
          {/* Filters */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 max-w-sm flex-1">
              <Search size={12} className="text-muted-foreground shrink-0"/>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search variables..."
                aria-label="Search variables"
                className="flex-1 vf-text-body-s bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
              />
            </div>
            <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value === "all" ? "all" : value as VariableType)}>
              <SelectTrigger className="w-full vf-text-caption" aria-label="Filter by variable type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {Object.keys(TYPE_CONFIG).map(t => (
                  <SelectItem key={t} value={t}>{TYPE_CONFIG[t as VariableType].label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sourceFilter} onValueChange={(value) => setSourceFilter(value === "all" ? "all" : value as SourceType)}>
              <SelectTrigger className="w-full vf-text-caption" aria-label="Filter by source">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                {Object.keys(SOURCE_CONFIG).map(s => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="ml-auto flex items-center gap-2">
              <button className="flex items-center gap-1.5 px-3 py-1.5 vf-text-caption font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
                <Download size={12}/> Export
              </button>
            </div>
          </div>

          {/* Variable Table */}
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <table className="w-full vf-text-body-s">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="w-8 px-3 py-3"></th>
                  {["Variable Name", "Type", "Unit", "Source", "Binding", "Used In", "Status", ""].map(h => (
                    <th key={h} className="text-left px-3 py-3 vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredVariables.map(v => (
                  <>
                    <tr 
                      key={v.variable_id} 
                      className="hover:bg-muted transition-colors group cursor-pointer"
                      onClick={() => setExpandedVariable(expandedVariable === v.variable_id ? null : v.variable_id)}
                    >
                      <td className="px-3 py-3">
                        {expandedVariable === v.variable_id ? 
                          <ChevronDown size={14} className="text-muted-foreground" aria-label="Collapse row"/> : 
                          <ChevronRight size={14} className="text-muted-foreground" aria-label="Expand row"/>
                        }
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <ListChecks size={14} className="text-violet-500 shrink-0"/>
                          <div>
                            <span className="font-mono font-medium text-foreground block">{v.name}</span>
                            <span className="vf-text-micro text-muted-foreground">{v.display_name}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3"><TypeBadge type={v.type}/></td>
                      <td className="px-3 py-3 text-muted-foreground">{v.unit}</td>
                      <td className="px-3 py-3"><SourceBadge source={v.source}/></td>
                      <td className="px-3 py-3 font-mono vf-text-caption text-muted-foreground">{v.binding}</td>
                      <td className="px-3 py-3 text-muted-foreground">{v.used_in_count} formulas</td>
                      <td className="px-3 py-3"><ValidationIcon status={v.validation_status}/></td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="View" aria-label="View variable">
                            <Eye size={13}/>
                          </button>
                          <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="Edit" aria-label="Edit variable">
                            <Edit3 size={13}/>
                          </button>
                          <button
                            className="p-1.5 rounded hover:bg-primary/10 text-muted-foreground hover:text-primary disabled:opacity-50"
                            title="Test binding"
                            aria-label="Test variable binding"
                            disabled={activeTestVariableId === v.variable_id}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleTestBinding(v);
                            }}
                          >
                            <RefreshCw size={13} className={cn(activeTestVariableId === v.variable_id && "animate-spin")} />
                          </button>
                          <button className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive" title="Delete" aria-label="Delete variable">
                            <Trash2 size={13}/>
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedVariable === v.variable_id && (
                      <tr className="bg-muted/50">
                        <td colSpan={9} className="px-3 py-4">
                          <div className="grid grid-cols-3 gap-4">
                            <div>
                              <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold mb-1">Description</p>
                              <p className="vf-text-body-s text-foreground">{v.description || "—"}</p>
                            </div>
                            <div>
                              <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold mb-1">Binding Details</p>
                              <p className="vf-text-caption font-mono text-muted-foreground">{v.binding_path || v.binding}</p>
                              {v.default_value && (
                                <p className="vf-text-caption text-muted-foreground mt-1">Default: {v.default_value}</p>
                              )}
                            </div>
                            <div>
                              <p className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold mb-1">Metadata</p>
                              <div className="space-y-1 vf-text-caption text-muted-foreground">
                                <p>Version: {v.version}</p>
                                <p>Created: {new Date(v.created_at).toLocaleDateString()}</p>
                                <p>Updated: {new Date(v.updated_at).toLocaleDateString()}</p>
                                {v.valid_range && (
                                  <p>Range: {v.valid_range.min} - {v.valid_range.max}</p>
                                )}
                              </div>
                            </div>
                          </div>
                          {v.validation_message && (
                            <div className={`mt-3 p-2 rounded-lg vf-text-caption ${
                              v.validation_status === "failed" ? "bg-destructive/10 text-destructive" : "bg-warning/10 text-warning"
                            }`}>
                              {v.validation_message}
                            </div>
                          )}
                          {testResultsByVariable[v.variable_id] && (
                            <div className={`mt-3 p-3 rounded-lg border vf-text-caption ${testResultsByVariable[v.variable_id].pass ? "bg-success/10 border-success/20 text-success" : "bg-destructive/10 border-destructive/20 text-destructive"}`}>
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-semibold">{testResultsByVariable[v.variable_id].pass ? "Binding test passed" : "Binding test failed"}</p>
                                  <p className="mt-1 font-mono break-all">
                                    Value: {String(testResultsByVariable[v.variable_id].evaluated_value ?? "—")}
                                  </p>
                                </div>
                                <button
                                  className="vf-text-micro underline"
                                  onClick={() => setExpandedDiagnosticsByVariable(prev => ({ ...prev, [v.variable_id]: !prev[v.variable_id] }))}
                                >
                                  {expandedDiagnosticsByVariable[v.variable_id] ? "Hide diagnostics" : "Show diagnostics"}
                                </button>
                              </div>
                              {!testResultsByVariable[v.variable_id].pass && testResultsByVariable[v.variable_id].failure_class && (
                                <p className="mt-2">
                                  {testResultsByVariable[v.variable_id].failure_class === "missing_source_binding" && "No source binding is configured for this variable."}
                                  {testResultsByVariable[v.variable_id].failure_class === "invalid_variable_config" && "Variable configuration is invalid; review type, binding path, and constraints."}
                                  {testResultsByVariable[v.variable_id].failure_class === "connector_unavailable" && "Connector or source service is unavailable; retry when the service is healthy."}
                                  {testResultsByVariable[v.variable_id].failure_class === "authorization" && "Your account is not authorized to test this binding."}
                                  {testResultsByVariable[v.variable_id].failure_class === "unknown" && "The test failed for an unknown reason."}
                                </p>
                              )}
                              {expandedDiagnosticsByVariable[v.variable_id] && (
                                <div className="mt-2 space-y-1">
                                  <p className="font-semibold">Source trace</p>
                                  <p className="font-mono">source={testResultsByVariable[v.variable_id].source_trace.source}, binding={testResultsByVariable[v.variable_id].source_trace.binding}, path={testResultsByVariable[v.variable_id].source_trace.resolved_path ?? "—"}</p>
                                  {testResultsByVariable[v.variable_id].diagnostics.map((d, index) => (
                                    <p key={`${d.code}-${index}`}>
                                      [{d.severity}] {d.code}: {d.message}{d.path ? ` (${d.path})` : ""}
                                    </p>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
            {filteredVariables.length === 0 && (
              <div className="text-center py-12 text-muted-foreground vf-text-body-s">
                <ListChecks size={32} className="mx-auto mb-3 text-muted-foreground/50"/>
                No variables match your filters.
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          {/* Source Bindings */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="vf-text-body-l font-semibold text-foreground">Connected Data Sources</h3>
              <Btn variant="outline"><Plus size={12} className="mr-1"/> Add Connection</Btn>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {bindings.map(binding => (
                <BindingCard 
                  key={binding.id} 
                  binding={binding} 
                  onTest={() => {}}
                />
              ))}
            </div>
          </div>

          {/* Binding Health Summary */}
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="vf-text-body-l font-semibold text-foreground mb-4">Connection Health</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-3 bg-success/10 rounded-lg">
                <CheckCircle2 size={20} className="text-success"/>
                <div>
                  <p className="text-[18px] font-bold text-success">{bindings.filter(b => b.status === "connected").length}</p>
                  <p className="vf-text-caption text-success">Connected</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-destructive/10 rounded-lg">
                <X size={20} className="text-destructive"/>
                <div>
                  <p className="text-[18px] font-bold text-destructive">{bindings.filter(b => b.status === "error").length}</p>
                  <p className="vf-text-caption text-destructive">Errors</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
                <RefreshCw size={20} className="text-muted-foreground"/>
                <div>
                  <p className="text-[18px] font-bold text-foreground">
                    {bindings.filter(b => b.last_sync).length}
                  </p>
                  <p className="vf-text-caption text-muted-foreground">Synced Today</p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </PageShell>
  );
}

export default function VariableRegistry() {
  return (
    <ErrorBoundary>
      <VariableRegistryContent />
    </ErrorBoundary>
  );
}
