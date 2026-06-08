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

import { useState, useMemo, Fragment } from "react";
import { useLocation } from "react-router-dom";
import {
  ListChecks, Plus, Search, Edit3, Trash2, Eye, Link2,
  CheckCircle2, AlertCircle, Database, Code2, Hash, DollarSign,
  Percent, Type, Settings, ChevronRight, ChevronDown, Download,
  Upload, RefreshCw, ExternalLink, Check, X
} from "lucide-react";
import ErrorBoundary from "@/components/ErrorBoundary";
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
import { Btn } from "@/components/ui/fabric";
import {
  AdminShell,
  AdminTabs,
  AdminTabPanel,
  AdminStatCard,
  AdminStatsRow,
  AdminFilterBar,
  AdminIconButton,
  AdminIconButtonGroup,
  AdminConfirmDialog,
  AdminEmptyState,
} from "@/components/admin";

// ── Styling Constants ───────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<VariableType, { label: string; color: string; icon: React.ReactNode }> = {
  rate:     { label: "Rate",     color: "bg-info/10 text-info",     icon: <Percent size={10}/> },
  currency: { label: "Currency", color: "bg-success/10 text-success", icon: <DollarSign size={10}/> },
  integer:  { label: "Integer",  color: "bg-primary/10 text-primary",     icon: <Hash size={10}/> },
  float:    { label: "Float",    color: "bg-primary/10 text-primary",  icon: <Code2 size={10}/> },
  boolean:  { label: "Boolean",  color: "bg-warning/10 text-warning",    icon: <Check size={10}/> },
  string:   { label: "String",   color: "bg-muted text-muted-foreground", icon: <Type size={10}/> },
};

const SOURCE_CONFIG: Record<SourceType, { color: string; icon: React.ReactNode }> = {
  CRM:      { color: "bg-primary/10 text-primary", icon: <Database size={10}/> },
  Billing:  { color: "bg-primary/10 text-primary", icon: <DollarSign size={10}/> },
  ERP:      { color: "bg-primary/10 text-primary", icon: <Database size={10}/> },
  Manual:   { color: "bg-muted text-muted-foreground", icon: <Type size={10}/> },
  Model:    { color: "bg-warning/10 text-warning", icon: <Code2 size={10}/> },
  API:      { color: "bg-info/10 text-info", icon: <ExternalLink size={10}/> },
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
          <Btn variant="ghost" size="sm" onClick={() => onTest(binding.id)}>
            <RefreshCw size={10} className="mr-1"/> Test
          </Btn>
          <AdminIconButton icon={Settings} label="Binding settings" />
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
  const [deleteTarget, setDeleteTarget] = useState<Variable | null>(null);

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

  return (
    <AdminShell
      title="Variable Registry"
      subtitle="Catalog of all formula variables — definitions, source bindings, type system, and validation rules."
      fullWidth
      actions={
        <div className="flex items-center gap-2">
          <Btn variant="outline">
            <Upload size={13} className="mr-1"/> Import
          </Btn>
          <Btn variant="primary">
            <Plus size={13} className="mr-1"/> Register Variable
          </Btn>
        </div>
      }
      tabs={
        <AdminTabs
          tabs={[
            { id: "catalog", label: "Variable Catalog", count: variables.length },
            { id: "bindings", label: "Source Bindings", count: bindings.length },
          ]}
          activeTab={activeTab}
          onChange={(tabId) => setActiveTab(tabId as TabType)}
        />
      }
    >
      <AdminTabPanel tabId="catalog" activeTab={activeTab}>
        <>
          <AdminStatsRow columns={5}>
            <AdminStatCard label="Total Variables" value={stats?.total ?? variables.length} icon={<ListChecks size={14}/>} />
            <AdminStatCard label="Validated" value={stats?.validated ?? variables.filter(v => v.validation_status === "validated").length} icon={<CheckCircle2 size={14}/>} color="success" />
            <AdminStatCard label="Pending" value={stats?.pending ?? variables.filter(v => v.validation_status === "pending").length} icon={<AlertCircle size={14}/>} color="warning" />
            <AdminStatCard label="Failed" value={stats?.failed ?? variables.filter(v => v.validation_status === "failed").length} icon={<X size={14}/>} color="destructive" />
            <AdminStatCard label="Total Usage" value={stats?.avg_usage ?? variables.reduce((s, v) => s + (v.used_in_count || 0), 0)} icon={<Link2 size={14}/>} color="primary" />
          </AdminStatsRow>

          <AdminFilterBar
            searchPlaceholder="Search variables..."
            searchValue={search}
            onSearchChange={setSearch}
            filters={
              <>
                <Select value={typeFilter} onValueChange={(value) => setTypeFilter(value === "all" ? "all" : value as VariableType)}>
                  <SelectTrigger className="w-40 vf-text-caption" aria-label="Filter by variable type">
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
                  <SelectTrigger className="w-40 vf-text-caption" aria-label="Filter by source">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources</SelectItem>
                    {Object.keys(SOURCE_CONFIG).map(s => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </>
            }
            actions={
              <Btn variant="outline" size="sm">
                <Download size={12}/> Export
              </Btn>
            }
          />

          {variablesError ? (
            <div className="rounded-xl border border-border bg-card p-6">
              <p className="text-destructive vf-text-body-s">Failed to load variables.</p>
            </div>
          ) : (
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
                    <Fragment key={v.variable_id}>
                      <tr
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
                            <ListChecks size={14} className="text-primary shrink-0"/>
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
                          <AdminIconButtonGroup>
                            <AdminIconButton icon={Eye} label="View variable" />
                            <AdminIconButton icon={Edit3} label="Edit variable" />
                            <AdminIconButton
                              icon={RefreshCw}
                              label="Test binding"
                              variant="primary"
                              disabled={activeTestVariableId === v.variable_id}
                              onClick={(e?: React.MouseEvent) => {
                                e?.stopPropagation();
                                handleTestBinding(v);
                              }}
                            />
                            <AdminIconButton
                              icon={Trash2}
                              label="Delete variable"
                              variant="destructive"
                              onClick={(e?: React.MouseEvent) => {
                                e?.stopPropagation();
                                setDeleteTarget(v);
                              }}
                            />
                          </AdminIconButtonGroup>
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
                                    <p className="font-mono">
                                      source={testResultsByVariable[v.variable_id].source_trace.source}, binding={testResultsByVariable[v.variable_id].source_trace.binding}, path={testResultsByVariable[v.variable_id].source_trace.resolved_path ?? "—"}
                                    </p>
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
                    </Fragment>
                  ))}
                </tbody>
              </table>
              {filteredVariables.length === 0 && !variablesLoading && (
                <AdminEmptyState
                  icon={ListChecks}
                  title="No variables match your filters"
                  description="Try adjusting your search or filter criteria."
                />
              )}
            </div>
          )}
        </>
      </AdminTabPanel>
      <AdminTabPanel tabId="bindings" activeTab={activeTab}>
        <>
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="vf-text-body-l font-semibold text-foreground">Connected Data Sources</h3>
              <Btn variant="outline">
                <Plus size={12} className="mr-1"/> Add Connection
              </Btn>
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

          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="vf-text-body-l font-semibold text-foreground mb-4">Connection Health</h3>
            <AdminStatsRow columns={3}>
              <AdminStatCard
                label="Connected"
                value={bindings.filter(b => b.status === "connected").length}
                icon={<CheckCircle2 size={20} />}
                color="success"
              />
              <AdminStatCard
                label="Errors"
                value={bindings.filter(b => b.status === "error").length}
                icon={<X size={20} />}
                color="destructive"
              />
              <AdminStatCard
                label="Synced Today"
                value={bindings.filter(b => b.last_sync).length}
                icon={<RefreshCw size={20} />}
              />
            </AdminStatsRow>
          </div>
        </>
      </AdminTabPanel>

      <AdminConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Variable"
        description="This variable will be permanently deleted. Any formulas using it may fail to evaluate."
        itemName={deleteTarget?.display_name || deleteTarget?.name}
        tenantName="Current tenant"
        actionLabel="Delete Variable"
        variant="destructive"
        onConfirm={() => setDeleteTarget(null)}
      />
    </AdminShell>
  );
}

export default function VariableRegistry() {
  return (
    <ErrorBoundary>
      <VariableRegistryContent />
    </ErrorBoundary>
  );
}
