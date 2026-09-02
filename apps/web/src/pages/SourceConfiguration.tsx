/**
 * SourceConfiguration — Data Source Management
 *
 * Features:
 * - Configure and manage data source connections (L1 Ingestion API)
 * - Connection health monitoring via useSourceStats
 * - CRUD operations via useCreateSource, useUpdateSource, useDeleteSource
 * - Test connection via useTestConnection
 * - Trigger ingestion via useExecuteSource
 *
 * Route: /context/sources
 * Integrates with: Layer 1 (Ingestion) /targets API via useSources hooks
 */
import { useState, useMemo } from "react";
import {
  Plus, Search, CheckCircle2, XCircle, AlertTriangle,
  Clock, RefreshCw, Database, Globe, FileText, Cloud, Server,
  Loader2, TestTube, Trash2, Plug, Play
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import ErrorBoundary from "@/components/ErrorBoundary";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import {
  useSources,
  useSourceStats,
  useCreateSource,
  useDeleteSource,
  useTestConnection,
  useExecuteSource,
  type CreateSourceRequest,
  type DataSource,
  type SourceType,
  type ConnectionStatus,
  type SyncFrequency,
  type SourceFilters,
} from "@/hooks/useSources";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Config ──────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<SourceType, {
  icon: React.ReactNode;
  label: string;
  bgColor: string;
}> = {
  crm: { icon: <Globe size={16} />, label: 'CRM', bgColor: 'bg-primary/10 text-primary' },
  database: { icon: <Database size={16} />, label: 'Database', bgColor: 'bg-primary/10 text-primary' },
  file: { icon: <FileText size={16} />, label: 'File', bgColor: 'bg-warning/10 text-warning' },
  api: { icon: <Server size={16} />, label: 'API', bgColor: 'bg-success/10 text-success' },
  cloud_storage: { icon: <Cloud size={16} />, label: 'Cloud', bgColor: 'bg-info/10 text-info' },
};

const STATUS_CONFIG: Record<ConnectionStatus, {
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  label: string;
}> = {
  connected: {
    icon: <CheckCircle2 size={14} />,
    color: 'text-success',
    bgColor: 'bg-success/10',
    label: 'Connected',
  },
  disconnected: {
    icon: <XCircle size={14} />,
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/30',
    label: 'Disconnected',
  },
  error: {
    icon: <AlertTriangle size={14} />,
    color: 'text-destructive',
    bgColor: 'bg-destructive/10',
    label: 'Error',
  },
  testing: {
    icon: <Loader2 size={14} className="animate-spin" />,
    color: 'text-primary',
    bgColor: 'bg-primary/10',
    label: 'Testing...',
  },
};

const FREQUENCY_LABELS: Record<SyncFrequency, string> = {
  realtime: 'Real-time',
  hourly: 'Hourly',
  daily: 'Daily',
  weekly: 'Weekly',
  manual: 'Manual',
};

// ── SourceCard Component ────────────────────────────────────────────────────

function SourceCard({
  source,
  isExpanded,
  onToggle,
  onTest,
  onDelete,
  onExecute,
  isTesting,
  isExecuting,
}: {
  source: DataSource;
  isExpanded: boolean;
  onToggle: () => void;
  onTest: () => void;
  onDelete: () => void;
  onExecute: () => void;
  isTesting: boolean;
  isExecuting: boolean;
}) {
  const type = TYPE_CONFIG[source.type];
  const status = STATUS_CONFIG[isTesting ? 'testing' : source.status];

  return (
    <div className={cn(
      "bg-card border border-border rounded-xl overflow-hidden transition-all",
      isExpanded && "ring-1 ring-primary/20"
    )}>
      <div
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-muted/20 group"
        onClick={onToggle}
      >
        {/* Type Icon */}
        <div className={cn("p-2 rounded-lg", type.bgColor)}>
          {type.icon}
        </div>
        {/* Name + Endpoint */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="vf-text-body-m font-semibold text-foreground truncate">{source.name}</h3>
            <div className={cn("flex items-center gap-1 px-2 py-0.5 rounded-full vf-text-micro font-medium", status.bgColor, status.color)}>
              {status.icon}
              {status.label}
            </div>
          </div>
          <p className="vf-text-caption text-muted-foreground/60 truncate mt-0.5">
            {source.endpoint || 'No endpoint configured'}
          </p>
        </div>
        {/* Metrics */}
        <div className="flex items-center gap-4 text-right">
          <div>
            <p className="vf-text-body-s font-medium text-muted-foreground">
              {source.recordCount ? source.recordCount.toLocaleString() : '—'}
            </p>
            <p className="vf-text-micro text-muted-foreground/60">records</p>
          </div>
          <div>
            <p className={cn(
              "vf-text-body-l font-bold",
              source.healthScore >= 90 ? "text-success" :
              source.healthScore >= 70 ? "text-warning" : "text-destructive"
            )}>
              {source.healthScore}%
            </p>
            <p className="vf-text-micro text-muted-foreground/60">health</p>
          </div>
          <div>
            <p className="vf-text-body-s font-medium text-muted-foreground">{FREQUENCY_LABELS[source.syncFrequency]}</p>
            <p className="vf-text-micro text-muted-foreground/60">sync</p>
          </div>
        </div>
        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button type="button"
            onClick={(e) => { e.stopPropagation(); onExecute(); }}
            disabled={isExecuting}
            className="p-2 rounded hover:bg-success/10 text-muted-foreground/60 hover:text-success disabled:opacity-50"
            title="Run ingestion"
          >
            {isExecuting ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          </button>
          <button type="button"
            onClick={(e) => { e.stopPropagation(); onTest(); }}
            disabled={isTesting}
            className="p-2 rounded hover:bg-muted/30 text-muted-foreground/60 hover:text-muted-foreground disabled:opacity-50"
            title="Test connection"
          >
            <TestTube size={14} />
          </button>
          <button type="button"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-2 rounded hover:bg-destructive/10 text-muted-foreground/60 hover:text-destructive"
            title="Delete source"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      {/* Error Message */}
      {source.status === 'error' && source.errorMessage && (
        <div className="mx-4 mb-3 p-2 bg-destructive/10 border border-destructive/20 rounded-lg vf-text-caption text-destructive flex items-start gap-2">
          <AlertTriangle size={12} className="shrink-0 mt-0.5" />
          {source.errorMessage}
        </div>
      )}
      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-border/50 pt-3">
          {/* Sync Info */}
          <div className="flex items-center gap-6 mb-4 vf-text-caption text-muted-foreground">
            {source.lastSyncAt && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                Last sync: {new Date(source.lastSyncAt).toLocaleString()}
              </span>
            )}
            {source.nextSyncAt && (
              <span className="flex items-center gap-1">
                <RefreshCw size={12} />
                Next sync: {new Date(source.nextSyncAt).toLocaleString()}
              </span>
            )}
            {source.tags.length > 0 && (
              <span className="flex items-center gap-1">
                Tags: {source.tags.join(', ')}
              </span>
            )}
          </div>
          {/* Performance Stats */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-muted/20 rounded-lg px-3 py-2">
              <p className="vf-text-micro text-muted-foreground/60 uppercase">Success Runs</p>
              <p className="vf-text-body-l font-bold text-success">{source.successCount}</p>
            </div>
            <div className="bg-muted/20 rounded-lg px-3 py-2">
              <p className="vf-text-micro text-muted-foreground/60 uppercase">Error Runs</p>
              <p className="vf-text-body-l font-bold text-destructive">{source.errorCount}</p>
            </div>
            <div className="bg-muted/20 rounded-lg px-3 py-2">
              <p className="vf-text-micro text-muted-foreground/60 uppercase">Avg Exec Time</p>
              <p className="vf-text-body-l font-bold text-foreground">{(source.averageExecutionTimeMs / 1000).toFixed(1)}s</p>
            </div>
          </div>
          {/* Field Mappings */}
          {source.fieldMappings.length > 0 && (
            <div>
              <h4 className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                Field Mappings ({source.fieldMappings.length})
              </h4>
              <div className="bg-muted/20 rounded-lg border border-border overflow-hidden">
                <table className="w-full vf-text-caption">
                  <thead className="bg-muted/30">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground">Source Field</th>
                      <th className="px-3 py-2 text-center font-medium text-muted-foreground">→</th>
                      <th className="px-3 py-2 text-left font-medium text-muted-foreground">Target Field</th>
                      <th className="px-3 py-2 text-center font-medium text-muted-foreground">Required</th>
                    </tr>
                  </thead>
                  <tbody>
                    {source.fieldMappings.map((mapping) => (
                      <tr key={mapping.sourceField} className="border-t border-border">
                        <td className="px-3 py-2 font-mono text-muted-foreground">{mapping.sourceField}</td>
                        <td className="px-3 py-2 text-center text-muted-foreground/60">→</td>
                        <td className="px-3 py-2 font-mono text-muted-foreground">{mapping.targetField}</td>
                        <td className="px-3 py-2 text-center">
                          {mapping.isRequired ? (
                            <span className="text-success">●</span>
                          ) : (
                            <span className="text-muted">○</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Skeleton ────────────────────────────────────────────────────────────────

function SourceSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="bg-card border border-border rounded-xl px-4 py-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-10 rounded-lg" />
            <div className="flex-1">
              <Skeleton className="h-4 w-48 mb-2" />
              <Skeleton className="h-3 w-64" />
            </div>
            <Skeleton className="h-6 w-16" />
            <Skeleton className="h-6 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

function CreateSourceModal({
  open,
  form,
  isSubmitting,
  onClose,
  onChange,
  onSubmit,
}: {
  open: boolean;
  form: CreateSourceRequest;
  isSubmitting: boolean;
  onClose: () => void;
  onChange: (updates: Partial<CreateSourceRequest>) => void;
  onSubmit: (e: React.SubmitEvent<HTMLFormElement>) => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-5 shadow-lg">
        <h3 className="text-base font-semibold text-foreground">Add Source</h3>
        <p className="mt-1 vf-text-body-s text-muted-foreground">Create a new data source target for ingestion.</p>

        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <div>
            <label className="mb-1 block vf-text-caption font-medium text-muted-foreground">Name</label>
            <Input
              value={form.name}
              onChange={(e) => onChange({ name: e.target.value })}
              placeholder="Salesforce Accounts API"
              className="w-full vf-text-body-m"
              required
            />
          </div>
          <div>
            <label className="mb-1 block vf-text-caption font-medium text-muted-foreground">URL</label>
            <Input
              type="url"
              value={form.url}
              onChange={(e) => onChange({ url: e.target.value })}
              placeholder="https://api.example.com/accounts"
              className="w-full vf-text-body-m"
              required
            />
          </div>
          <div>
            <label className="mb-1 block vf-text-caption font-medium text-muted-foreground">Type</label>
            <Select value={form.targetType} onValueChange={(v) => onChange({ targetType: v as SourceType })}>
              <SelectTrigger className="w-full vf-text-body-m">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="api">API</SelectItem>
                <SelectItem value="crm">CRM</SelectItem>
                <SelectItem value="database">Database</SelectItem>
                <SelectItem value="cloud_storage">Cloud Storage</SelectItem>
                <SelectItem value="file">File</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block vf-text-caption font-medium text-muted-foreground">Description (optional)</label>
            <Textarea
              value={form.description ?? ""}
              onChange={(e) => onChange({ description: e.target.value || undefined })}
              rows={3}
              className="w-full vf-text-body-m"
            />
          </div>

          <div className="mt-4 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-md border border-border px-3 py-2 vf-text-body-s font-medium text-foreground hover:bg-muted disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center rounded-md bg-primary px-3 py-2 vf-text-body-s font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Plus size={14} className="mr-1" />}
              Create Source
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Content ────────────────────────────────────────────────────────────

function SourceConfigurationContent() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<SourceType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<ConnectionStatus | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CreateSourceRequest>({
    name: "",
    url: "",
    targetType: "api",
    description: "",
  });

  // Build filters for the API call
  const apiFilters: SourceFilters = useMemo(() => ({
    search: search || undefined,
    type: typeFilter !== 'all' ? typeFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  }), [search, typeFilter, statusFilter]);

  // Server state via React Query hooks (real L1 API)
  const { data: sourceData, isLoading, error, refetch } = useSources(apiFilters);
  const { data: stats, refetch: refetchStats } = useSourceStats();
  const createSource = useCreateSource();
  const deleteSource = useDeleteSource();
  const testConnection = useTestConnection();
  const executeSource = useExecuteSource();

  const sources = sourceData?.sources ?? [];

  const handleTest = (sourceId: string) => {
    setTestingId(sourceId);
    testConnection.mutate(
      { id: sourceId },
      { onSettled: () => setTestingId(null) }
    );
  };

  const handleDelete = (sourceId: string) => {
    if (window.confirm('Are you sure you want to delete this source? This action cannot be undone.')) {
      deleteSource.mutate(sourceId);
    }
  };

  const handleExecute = (sourceId: string) => {
    setExecutingId(sourceId);
    executeSource.mutate(
      { id: sourceId },
      { onSettled: () => setExecutingId(null) }
    );
  };

  const openCreateFlow = () => setIsCreateOpen(true);
  const closeCreateFlow = () => {
    setIsCreateOpen(false);
    setCreateForm({
      name: "",
      url: "",
      targetType: "api",
      description: "",
    });
  };

  const handleCreateSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    createSource.mutate(createForm, {
      onSuccess: async (source) => {
        closeCreateFlow();
        await Promise.all([refetch(), refetchStats()]);
        toast.success(`Source "${source.name}" created successfully.`);
      },
      onError: (err) => {
        toast.error(err.message || "Failed to create source.");
      },
    });
  };

  // Error state
  if (error) {
    return (
      <PageShell className="max-w-5xl">
        <PageHeader title="Source Configuration" subtitle="Manage data source connections" />
        <ErrorState
          title="Failed to load sources"
          error={error}
          onRetry={() => refetch()}
        />
      </PageShell>
    );
  }

  return (
    <PageShell className="max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <PageHeader
          title="Source Configuration"
          subtitle={stats ? `${stats.total ?? 0} sources · ${stats.connected ?? 0} connected · ${stats.error ?? 0} errors` : 'Loading...'}
        />
        <Btn variant="primary" onClick={openCreateFlow}>
          <Plus size={14} className="mr-1" />
          Add Source
        </Btn>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-card border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Database size={14} className="text-primary" />
            <span className="vf-text-micro uppercase tracking-wider text-muted-foreground/60 font-semibold">Total Sources</span>
          </div>
          <p className="text-2xl font-extrabold text-foreground">{stats?.total ?? '—'}</p>
        </div>
        <div className="bg-card border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Plug size={14} className="text-success" />
            <span className="vf-text-micro uppercase tracking-wider text-muted-foreground/60 font-semibold">Connected</span>
          </div>
          <p className="text-2xl font-extrabold text-success">{stats?.connected ?? '—'}</p>
        </div>
        <div className="bg-card border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={14} className="text-destructive" />
            <span className="vf-text-micro uppercase tracking-wider text-muted-foreground/60 font-semibold">Errors</span>
          </div>
          <p className="text-2xl font-extrabold text-destructive">{stats?.error ?? '—'}</p>
        </div>
        <div className="bg-card border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <FileText size={14} className="text-primary" />
            <span className="vf-text-micro uppercase tracking-wider text-muted-foreground/60 font-semibold">Total Records</span>
          </div>
          <p className="text-2xl font-extrabold text-primary">
            {stats?.total_records ? `${(stats.total_records / 1000).toFixed(0)}K` : '—'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex items-center gap-2 flex-1 max-w-sm">
          <Search size={14} className="text-muted-foreground/60 absolute left-3 top-1/2 -translate-y-1/2 z-10" />
          <Input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sources..."
            className="flex-1 vf-text-body-m pl-8"
          />
        </div>
        <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as SourceType | 'all')}>
          <SelectTrigger className="vf-text-body-s">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="crm">CRM</SelectItem>
            <SelectItem value="database">Database</SelectItem>
            <SelectItem value="api">API</SelectItem>
            <SelectItem value="cloud_storage">Cloud Storage</SelectItem>
            <SelectItem value="file">File</SelectItem>
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as ConnectionStatus | 'all')}>
          <SelectTrigger className="vf-text-body-s">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="connected">Connected</SelectItem>
            <SelectItem value="disconnected">Disconnected</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Btn variant="ghost" onClick={() => refetch()} className="vf-text-body-s">
          <RefreshCw size={14} className="mr-1" />
          Refresh
        </Btn>
      </div>

      {/* Loading State */}
      {isLoading && <SourceSkeleton />}

      {/* Source List */}
      {!isLoading && (
        <div className="space-y-3">
          {sources.map(source => (
            <SourceCard
              key={source.id}
              source={source}
              isExpanded={expandedId === source.id}
              onToggle={() => setExpandedId(expandedId === source.id ? null : source.id)}
              onTest={() => handleTest(source.id)}
              onDelete={() => handleDelete(source.id)}
              onExecute={() => handleExecute(source.id)}
              isTesting={testingId === source.id}
              isExecuting={executingId === source.id}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && sources.length === 0 && (
        <div className="text-center py-12 text-muted-foreground/60">
          <Database size={48} className="mx-auto mb-4 text-muted" />
          <p className="vf-text-body-l font-medium">No sources found</p>
          <p className="vf-text-body-s mt-1">
            {search || typeFilter !== 'all' || statusFilter !== 'all'
              ? 'Try adjusting your filters'
              : 'Add a data source to start ingesting data'}
          </p>
          <Btn variant="primary" className="mt-4" onClick={openCreateFlow}>
            <Plus size={14} className="mr-1" />
            Add First Source
          </Btn>
        </div>
      )}

      {/* Pagination */}
      {sourceData && sourceData.pagination.totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6 vf-text-body-s text-muted-foreground">
          <span>
            Page {sourceData.pagination.page} of {sourceData.pagination.totalPages}
            {' '}({sourceData.pagination.total} total)
          </span>
        </div>
      )}

      <CreateSourceModal
        open={isCreateOpen}
        form={createForm}
        isSubmitting={createSource.isPending}
        onClose={closeCreateFlow}
        onChange={(updates) => setCreateForm(prev => ({ ...prev, ...updates }))}
        onSubmit={handleCreateSubmit}
      />
    </PageShell>
  );
}

export default function SourceConfiguration() {
  return (
    <ErrorBoundary>
      <SourceConfigurationContent />
    </ErrorBoundary>
  );
}
