/**
 * TargetsAdmin — Context Engine / Targets
 * Route: /context/targets (requires governance permission)
 */
import { useState, useCallback } from 'react';
import {
  Plus, RefreshCw, Play, Pause, Archive, Trash2,
  Search, Filter, CheckCircle2, XCircle, AlertTriangle,
  Clock, Globe, ChevronRight, MoreHorizontal, Loader2,
  Activity, Target, Settings2, Calendar, AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { PageShell } from '@/components';
import { ErrorState } from '@/components/states/ErrorState';
import { EmptyState } from '@/components/states';
import { PageHeader } from '@/components/ui/fabric/PageHeader';
import { MetricCard } from '@/components/ui/fabric/MetricCard';
import { SidePanel } from '@/components/ui/fabric/SidePanel';
import { StatusBadge } from '@/components/ui/fabric/StatusBadge';
import { PaginationBar } from '@/components/ui/fabric/PaginationBar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  useTargets, useTargetStats, useUpdateTargetStatus,
  useExecuteTarget, useBatchTargetOperation,
  type TargetSummary, type TargetFilters, type TargetStatus,
} from '@/hooks/useTargets';
import { useIngestionJobList } from '@/hooks/useIngestion';
import { TargetDetailPanel } from './TargetsAdmin.detail';
import { TargetFormPanel } from './TargetsAdmin.form';

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<TargetStatus, { label: string; variant: 'success' | 'warning' | 'destructive' | 'secondary'; icon: React.ReactNode }> = {
  ACTIVE:   { label: 'Active',   variant: 'success',     icon: <CheckCircle2 size={12} /> },
  PAUSED:   { label: 'Paused',   variant: 'warning',     icon: <Clock size={12} /> },
  ERROR:    { label: 'Error',    variant: 'destructive', icon: <XCircle size={12} /> },
  ARCHIVED: { label: 'Archived', variant: 'secondary',   icon: <Archive size={12} /> },
};

const TYPE_LABELS: Record<string, string> = {
  SINGLE_PAGE:  'Single Page',
  PAGINATED:    'Paginated',
  SPIDER:       'Spider',
  API_ENDPOINT: 'API Endpoint',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function handleDivKeyDown(e: React.KeyboardEvent, callback: () => void) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    callback();
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function HealthBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-success' : score >= 50 ? 'bg-warning' : 'bg-destructive';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="vf-text-caption text-muted-foreground tabular-nums">{score}%</span>
    </div>
  );
}

function TargetStatusBadge({ status }: { status: TargetStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.ARCHIVED;
  return (
    <StatusBadge variant={cfg.variant}>
      <span className="flex items-center gap-1">{cfg.icon}{cfg.label}</span>
    </StatusBadge>
  );
}

function StatsStrip({ stats, isLoading }: { stats: ReturnType<typeof useTargetStats>['data']; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <MetricCard label="Total Targets" value={String(stats?.total ?? 0)} />
      <MetricCard label="Active" value={String(stats?.connected ?? 0)} />
      <MetricCard label="Paused / Offline" value={String(stats?.disconnected ?? 0)} />
      <MetricCard label="Error" value={String(stats?.error ?? 0)} />
    </div>
  );
}

// ── Target Table Row ──────────────────────────────────────────────────────────

interface TargetRowProps {
  target: TargetSummary;
  selected: boolean;
  onSelect: (id: string, checked: boolean) => void;
  onRowClick: (target: TargetSummary) => void;
  onRun: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onArchive: (id: string) => void;
  isRunning: boolean;
}

function TargetRow({ target, selected, onSelect, onRowClick, onRun, onPause, onResume, onArchive, isRunning }: TargetRowProps) {
  const canRun = target.status === 'ACTIVE';
  const canPause = target.status === 'ACTIVE' || target.status === 'ERROR';
  const canResume = target.status === 'PAUSED';
  const canArchive = target.status !== 'ARCHIVED';

  return (
    <tr
      className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer"
      onClick={() => onRowClick(target)}
    >
      <td className="px-4 py-3 w-10" onClick={e => e.stopPropagation()}>
        <Checkbox
          checked={selected}
          onCheckedChange={checked => onSelect(target.id, !!checked)}
          aria-label={`Select ${target.name}`}
        />
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col gap-0.5">
          <span className="vf-text-body-m font-medium text-foreground truncate max-w-[220px]">{target.name}</span>
          <span className="vf-text-caption text-muted-foreground truncate max-w-[220px]">{target.url}</span>
        </div>
      </td>
      <td className="px-4 py-3 hidden sm:table-cell">
        <Badge variant="outline" className="vf-text-caption">{TYPE_LABELS[target.targetType] ?? target.targetType}</Badge>
      </td>
      <td className="px-4 py-3">
        <TargetStatusBadge status={target.status} />
      </td>
      <td className="px-4 py-3 hidden md:table-cell vf-text-body-s text-muted-foreground">
        {target.lastSuccessAt ? new Date(target.lastSuccessAt).toLocaleDateString() : '—'}
      </td>
      <td className="px-4 py-3 hidden lg:table-cell">
        <div className="flex items-center gap-3 vf-text-body-s text-muted-foreground">
          <span className="text-success">{target.successCount}✓</span>
          <span className="text-destructive">{target.errorCount}✗</span>
        </div>
      </td>
      <td className="px-4 py-3 hidden xl:table-cell">
        <HealthBar score={target.healthScore} />
      </td>
      <td className="px-4 py-3 hidden lg:table-cell">
        <div className="flex flex-wrap gap-1">
          {target.tags.slice(0, 2).map(tag => (
            <Badge key={tag} variant="secondary" className="vf-text-micro px-1.5 py-0">{tag}</Badge>
          ))}
          {target.tags.length > 2 && <span className="vf-text-micro text-muted-foreground">+{target.tags.length - 2}</span>}
        </div>
      </td>
      <td className="px-4 py-3 w-10" onClick={e => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="Target actions">
              <MoreHorizontal size={14} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            {canRun && (
              <DropdownMenuItem onClick={() => onRun(target.id)} disabled={isRunning}>
                <Play size={13} className="mr-2" />Run now
              </DropdownMenuItem>
            )}
            {canPause && (
              <DropdownMenuItem onClick={() => onPause(target.id)}>
                <Pause size={13} className="mr-2" />Pause
              </DropdownMenuItem>
            )}
            {canResume && (
              <DropdownMenuItem onClick={() => onResume(target.id)}>
                <Play size={13} className="mr-2" />Resume
              </DropdownMenuItem>
            )}
            {canArchive && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => onArchive(target.id)} className="text-destructive focus:text-destructive">
                  <Archive size={13} className="mr-2" />Archive
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

// ── Target Table ──────────────────────────────────────────────────────────────

interface TargetTableProps {
  targets: TargetSummary[];
  isLoading: boolean;
  selectedIds: Set<string>;
  onSelectOne: (id: string, checked: boolean) => void;
  onSelectAll: (checked: boolean) => void;
  onRowClick: (target: TargetSummary) => void;
  onRun: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onArchive: (id: string) => void;
  runningId: string | null;
}

function TargetTable({ targets, isLoading, selectedIds, onSelectOne, onSelectAll, onRowClick, onRun, onPause, onResume, onArchive, runningId }: TargetTableProps) {
  const allSelected = targets.length > 0 && targets.every(t => selectedIds.has(t.id));
  const someSelected = targets.some(t => selectedIds.has(t.id));

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 rounded" />)}
      </div>
    );
  }

  if (targets.length === 0) {
    return (
      <EmptyState
        icon={Target}
        title="No targets found"
        description="Targets define what Layer 1 should crawl and research."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/30">
            <th className="px-4 py-2.5 w-10">
              <Checkbox
                checked={allSelected}
                onCheckedChange={onSelectAll}
                aria-label="Select all"
                data-state={someSelected && !allSelected ? 'indeterminate' : undefined}
              />
            </th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider">Name / URL</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider hidden sm:table-cell">Type</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Last Run</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Runs</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider hidden xl:table-cell">Health</th>
            <th className="px-4 py-2.5 text-left vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Tags</th>
            <th className="px-4 py-2.5 w-10" />
          </tr>
        </thead>
        <tbody>
          {targets.map(target => (
            <TargetRow
              key={target.id}
              target={target}
              selected={selectedIds.has(target.id)}
              onSelect={onSelectOne}
              onRowClick={onRowClick}
              onRun={onRun}
              onPause={onPause}
              onResume={onResume}
              onArchive={onArchive}
              isRunning={runningId === target.id}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Bulk Action Toolbar ───────────────────────────────────────────────────────

interface BulkToolbarProps {
  selectedIds: Set<string>;
  onClear: () => void;
  onBulkRun: () => void;
  onBulkPause: () => void;
  onBulkArchive: () => void;
  isBusy: boolean;
}

function BulkToolbar({ selectedIds, onClear, onBulkRun, onBulkPause, onBulkArchive, isBusy }: BulkToolbarProps) {
  if (selectedIds.size === 0) return null;
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-primary/5 border-b border-primary/20">
      <span className="vf-text-body-m font-medium text-primary">{selectedIds.size} selected</span>
      <div className="flex items-center gap-2 ml-2">
        <Button size="sm" variant="outline" onClick={onBulkRun} disabled={isBusy} className="h-7 vf-text-body-s">
          <Play size={12} className="mr-1.5" />Run
        </Button>
        <Button size="sm" variant="outline" onClick={onBulkPause} disabled={isBusy} className="h-7 vf-text-body-s">
          <Pause size={12} className="mr-1.5" />Pause
        </Button>
        <Button size="sm" variant="outline" onClick={onBulkArchive} disabled={isBusy} className="h-7 vf-text-body-s text-destructive hover:text-destructive">
          <Archive size={12} className="mr-1.5" />Archive
        </Button>
      </div>
      <Button size="sm" variant="ghost" onClick={onClear} className="ml-auto h-7 vf-text-body-s">Clear</Button>
    </div>
  );
}

// ── Filter Bar ────────────────────────────────────────────────────────────────

interface FilterBarProps {
  filters: TargetFilters;
  onChange: (f: Partial<TargetFilters>) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

function TargetFilterBar({ filters, onChange, onRefresh, isRefreshing }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-border">
      <div className="relative flex-1 min-w-[180px] max-w-xs">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search targets…"
          value={filters.search ?? ''}
          onChange={e => onChange({ search: e.target.value || undefined, page: 1 })}
          className="pl-8 h-8 vf-text-body-m"
        />
      </div>
      <Select value={filters.status ?? 'all'} onValueChange={v => onChange({ status: v === 'all' ? undefined : v as TargetStatus, page: 1 })}>
        <SelectTrigger className="h-8 w-32 vf-text-body-m" aria-label="Status filter"><SelectValue placeholder="Status" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="ACTIVE">Active</SelectItem>
          <SelectItem value="PAUSED">Paused</SelectItem>
          <SelectItem value="ERROR">Error</SelectItem>
          <SelectItem value="ARCHIVED">Archived</SelectItem>
        </SelectContent>
      </Select>
      <Select value={filters.targetType ?? 'all'} onValueChange={v => onChange({ targetType: v === 'all' ? undefined : v as TargetFilters['targetType'], page: 1 })}>
        <SelectTrigger className="h-8 w-36 vf-text-body-m"><SelectValue placeholder="Type" /></SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All types</SelectItem>
          <SelectItem value="SINGLE_PAGE">Single Page</SelectItem>
          <SelectItem value="PAGINATED">Paginated</SelectItem>
          <SelectItem value="SPIDER">Spider</SelectItem>
          <SelectItem value="API_ENDPOINT">API Endpoint</SelectItem>
        </SelectContent>
      </Select>
      <Button size="sm" variant="ghost" onClick={onRefresh} disabled={isRefreshing} className="h-8 ml-auto" aria-label="Refresh">
        <RefreshCw size={14} className={cn(isRefreshing && 'animate-spin')} />
      </Button>
    </div>
  );
}

// ── Scheduled Tab ────────────────────────────────────────────────────────────

function ScheduledTab({ onRowClick }: { onRowClick: (t: TargetSummary) => void }) {
  const { data, isLoading } = useTargets({ limit: 50, sortBy: 'updated_at', sortOrder: 'asc' });
  const scheduled = data?.targets.filter(t => t.schedule?.enabled === true) ?? [];
  if (isLoading) return <div className="p-4 space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-10 rounded" />)}</div>;
  if (scheduled.length === 0) return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Calendar size={32} className="text-muted-foreground mb-3" />
      <p className="vf-text-body-l font-medium">No scheduled targets</p>
      <p className="vf-text-body-m text-muted-foreground mt-1">Enable a schedule on a target to see it here.</p>
    </div>
  );
  return (
    <div className="divide-y divide-border overflow-auto">
      {scheduled.map(t => (
        <div
          key={t.id}
          role="button"
          tabIndex={0}
          className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 cursor-pointer"
          onClick={() => onRowClick(t)}
          onKeyDown={(e) => handleDivKeyDown(e, () => onRowClick(t))}
        >
          <Calendar size={14} className="text-muted-foreground shrink-0" />
          <span className="font-medium vf-text-body-m flex-1 truncate">{t.name}</span>
          <TargetStatusBadge status={t.status} />
          <ChevronRight size={14} className="text-muted-foreground" />
        </div>
      ))}
    </div>
  );
}

// ── Compliance Failures Tab ───────────────────────────────────────────────────

function ComplianceFailuresTab({ onRowClick }: { onRowClick: (t: TargetSummary) => void }) {
  const { data, isLoading } = useTargets({ status: 'ERROR', limit: 50, sortBy: 'updated_at', sortOrder: 'desc' });
  const failures = data?.targets ?? [];
  if (isLoading) return <div className="p-4 space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-10 rounded" />)}</div>;
  if (failures.length === 0) return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <CheckCircle2 size={32} className="text-success mb-3" />
      <p className="vf-text-body-l font-medium">No compliance failures</p>
      <p className="vf-text-body-m text-muted-foreground mt-1">All targets are operating within compliance bounds.</p>
    </div>
  );
  return (
    <div className="divide-y divide-border overflow-auto">
      {failures.map(t => (
        <div
          key={t.id}
          role="button"
          tabIndex={0}
          className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 cursor-pointer"
          onClick={() => onRowClick(t)}
          onKeyDown={(e) => handleDivKeyDown(e, () => onRowClick(t))}
        >
          <AlertTriangle size={14} className="text-destructive shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-medium vf-text-body-m truncate">{t.name}</p>
            <p className="vf-text-caption text-muted-foreground truncate">{t.url}</p>
          </div>
          <TargetStatusBadge status={t.status} />
          <span className="vf-text-body-s text-muted-foreground hidden sm:block">{t.errorCount} errors</span>
          <ChevronRight size={14} className="text-muted-foreground" />
        </div>
      ))}
    </div>
  );
}

// ── Events Tab ────────────────────────────────────────────────────────────────

function EventsTab() {
  const { data, isLoading } = useIngestionJobList({ limit: 50, sortBy: 'created_at', sortOrder: 'desc' });
  const jobs = data?.jobs ?? [];
  if (isLoading) return <div className="p-4 space-y-2">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 rounded" />)}</div>;
  if (jobs.length === 0) return (
    <div className="py-12 text-center vf-text-body-m text-muted-foreground">No recent events.</div>
  );
  return (
    <div className="divide-y divide-border overflow-auto">
      {jobs.map(job => (
        <div key={job.id} className="flex items-center gap-3 px-4 py-3 vf-text-body-m">
          <Activity size={14} className="text-muted-foreground shrink-0" />
          <span className="font-medium truncate flex-1">{job.domain}</span>
          <StatusBadge status={job.status} />
          {job.pagesProcessed != null && (
            <span className="text-muted-foreground vf-text-body-s hidden sm:block">{job.pagesProcessed} pages</span>
          )}
          <span className="text-muted-foreground vf-text-body-s hidden sm:block">
            {new Date(job.createdAt).toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type PanelMode = 'detail' | 'create' | 'edit' | null;

export default function TargetsAdmin() {
  // Filters
  const [filters, setFilters] = useState<TargetFilters>({ page: 1, limit: 25, sortBy: 'created_at', sortOrder: 'desc' });
  const updateFilters = useCallback((patch: Partial<TargetFilters>) => setFilters(f => ({ ...f, ...patch })), []);

  // Data — declared before selection handlers that depend on `data`
  const { data, isLoading, isFetching, refetch, error } = useTargets(filters);
  const { data: stats, isLoading: statsLoading, error: statsError } = useTargetStats();

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const handleSelectOne = useCallback((id: string, checked: boolean) => {
    setSelectedIds(prev => { const next = new Set(prev); checked ? next.add(id) : next.delete(id); return next; });
  }, []);
  const handleSelectAll = useCallback((checked: boolean) => {
    setSelectedIds(checked ? new Set(data?.targets.map(t => t.id) ?? []) : new Set());
  }, [data]);

  // Panel
  const [panelMode, setPanelMode] = useState<PanelMode>(null);
  const [selectedTarget, setSelectedTarget] = useState<TargetSummary | null>(null);
  const [archiveTargetId, setArchiveTargetId] = useState<string | null>(null);

  // Mutations
  const updateStatus = useUpdateTargetStatus();
  const executeTarget = useExecuteTarget();
  const batchOp = useBatchTargetOperation();
  const [runningId, setRunningId] = useState<string | null>(null);

  // Row actions
  const handleRun = useCallback(async (id: string) => {
    setRunningId(id);
    try {
      await executeTarget.mutateAsync({ id });
      toast.success('Crawl job queued');
    } catch {
      toast.error('Failed to queue job');
    } finally {
      setRunningId(null);
    }
  }, [executeTarget]);

  const handlePause = useCallback(async (id: string) => {
    try {
      await updateStatus.mutateAsync({ id, status: 'PAUSED' });
      toast.success('Target paused');
    } catch {
      toast.error('Failed to pause target');
    }
  }, [updateStatus]);

  const handleResume = useCallback(async (id: string) => {
    try {
      await updateStatus.mutateAsync({ id, status: 'ACTIVE' });
      toast.success('Target resumed');
    } catch {
      toast.error('Failed to resume target');
    }
  }, [updateStatus]);

  const handleArchiveConfirm = useCallback(async () => {
    if (!archiveTargetId) return;
    try {
      await updateStatus.mutateAsync({ id: archiveTargetId, status: 'ARCHIVED' });
      toast.success('Target archived');
    } catch {
      toast.error('Failed to archive target');
    } finally {
      setArchiveTargetId(null);
    }
  }, [archiveTargetId, updateStatus]);

  // Bulk actions
  const handleBulkOp = useCallback(async (operation: 'execute' | 'pause' | 'archive') => {
    const ids = Array.from(selectedIds);
    try {
      const result = await batchOp.mutateAsync({ operation, targetIds: ids });
      if (result.failed > 0) {
        toast.warning(`${result.succeeded} succeeded, ${result.failed} failed`);
      } else {
        toast.success(`${result.succeeded} target(s) updated`);
      }
      setSelectedIds(new Set());
    } catch {
      toast.error('Batch operation failed');
    }
  }, [selectedIds, batchOp]);

  const pagination = data?.pagination;

  if (isLoading) {
    return (
      <PageShell className="flex flex-col h-full" fullWidth>
        <PageHeader
          title="Targets"
          subtitle="Define and manage what Layer 1 crawls, monitors, and researches."
          breadcrumbs={[{ label: 'Context Engine', href: '/context' }, { label: 'Targets' }]}
        />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
        </div>
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 rounded" />)}
        </div>
      </PageShell>
    );
  }

  if (error || statsError) {
    return (
      <PageShell className="flex flex-col h-full" fullWidth>
        <PageHeader
          title="Targets"
          subtitle="Define and manage what Layer 1 crawls, monitors, and researches."
          breadcrumbs={[{ label: 'Context Engine', href: '/context' }, { label: 'Targets' }]}
        />
        <ErrorState
          title="Failed to load targets"
          description={error instanceof Error ? error.message : statsError instanceof Error ? statsError.message : "An unexpected error occurred"}
          onRetry={() => refetch()}
        />
      </PageShell>
    );
  }

  return (
    <PageShell className="flex flex-col h-full" fullWidth>
      <PageHeader
        title="Targets"
        subtitle="Define and manage what Layer 1 crawls, monitors, and researches."
        breadcrumbs={[{ label: 'Context Engine', href: '/context' }, { label: 'Targets' }]}
        actions={
          <>
            <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isFetching} className="h-8">
              <RefreshCw size={14} className={cn('mr-1.5', isFetching && 'animate-spin')} />Refresh
            </Button>
            <Button size="sm" onClick={() => { setSelectedTarget(null); setPanelMode('create'); }} className="h-8">
              <Plus size={14} className="mr-1.5" />New Target
            </Button>
          </>
        }
      />
      <StatsStrip stats={stats} isLoading={statsLoading} />

      <Tabs defaultValue="all" className="flex-1 flex flex-col min-h-0">
        <div className="border-b border-border">
          <TabsList className="h-9 bg-transparent p-0 gap-1">
            {[
              { value: 'all', label: 'All Targets', icon: <Target size={13} /> },
              { value: 'scheduled', label: 'Scheduled', icon: <Calendar size={13} /> },
              { value: 'failures', label: 'Compliance Failures', icon: <AlertCircle size={13} /> },
              { value: 'events', label: 'Events', icon: <Activity size={13} /> },
            ].map(tab => (
              <TabsTrigger key={tab.value} value={tab.value} className="h-9 px-3 vf-text-body-m data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none">
                <span className="flex items-center gap-1.5">{tab.icon}{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        {/* All Targets */}
        <TabsContent value="all" className="flex-1 flex flex-col min-h-0 mt-0">
          <TargetFilterBar filters={filters} onChange={updateFilters} onRefresh={() => refetch()} isRefreshing={isFetching} />
          <BulkToolbar
            selectedIds={selectedIds}
            onClear={() => setSelectedIds(new Set())}
            onBulkRun={() => handleBulkOp('execute')}
            onBulkPause={() => handleBulkOp('pause')}
            onBulkArchive={() => handleBulkOp('archive')}
            isBusy={batchOp.isPending}
          />
          <div className="flex-1 overflow-auto">
            <TargetTable
              targets={data?.targets ?? []}
              isLoading={isLoading}
              selectedIds={selectedIds}
              onSelectOne={handleSelectOne}
              onSelectAll={handleSelectAll}
              onRowClick={t => { setSelectedTarget(t); setPanelMode('detail'); }}
              onRun={handleRun}
              onPause={handlePause}
              onResume={handleResume}
              onArchive={id => setArchiveTargetId(id)}
              runningId={runningId}
            />
          </div>
          {pagination && (
            <PaginationBar
              page={pagination.page}
              pageSize={pagination.limit}
              totalItems={pagination.total}
              totalPages={pagination.totalPages}
              canPrevious={pagination.page > 1}
              canNext={pagination.page < pagination.totalPages}
              onPrevious={() => updateFilters({ page: pagination.page - 1 })}
              onNext={() => updateFilters({ page: pagination.page + 1 })}
              onPageChange={p => updateFilters({ page: p })}
              itemLabel="targets"
            />
          )}
        </TabsContent>

        {/* Scheduled */}
        <TabsContent value="scheduled" className="flex-1 flex flex-col min-h-0 mt-0">
          <ScheduledTab onRowClick={t => { setSelectedTarget(t); setPanelMode('detail'); }} />
        </TabsContent>

        {/* Compliance Failures */}
        <TabsContent value="failures" className="flex-1 flex flex-col min-h-0 mt-0">
          <ComplianceFailuresTab onRowClick={t => { setSelectedTarget(t); setPanelMode('detail'); }} />
        </TabsContent>

        {/* Events */}
        <TabsContent value="events" className="flex-1 overflow-auto mt-0">
          <EventsTab />
        </TabsContent>
      </Tabs>

      {/* Right rail — detail */}
      <SidePanel
        open={panelMode === 'detail' && !!selectedTarget}
        onOpenChange={open => { if (!open) setPanelMode(null); }}
        title={selectedTarget?.name ?? 'Target Detail'}
        width="xl"
      >
        {selectedTarget && panelMode === 'detail' && (
          <TargetDetailPanel
            targetId={selectedTarget.id}
            onEdit={() => setPanelMode('edit')}
            onClose={() => setPanelMode(null)}
          />
        )}
      </SidePanel>

      {/* Right rail — create / edit */}
      <SidePanel
        open={panelMode === 'create' || panelMode === 'edit'}
        onOpenChange={open => { if (!open) setPanelMode(null); }}
        title={panelMode === 'create' ? 'New Target' : 'Edit Target'}
        width="xl"
      >
        {(panelMode === 'create' || panelMode === 'edit') && (
          <TargetFormPanel
            targetId={panelMode === 'edit' ? selectedTarget?.id ?? null : null}
            onSuccess={target => {
              setPanelMode('detail');
              setSelectedTarget({ ...target, healthScore: 0, successCount: 0, errorCount: 0, averageExecutionTimeMs: 0 } as TargetSummary);
              toast.success(panelMode === 'create' ? 'Target created' : 'Target updated');
            }}
            onCancel={() => setPanelMode(panelMode === 'edit' ? 'detail' : null)}
          />
        )}
      </SidePanel>

      {/* Archive confirmation */}
      <AlertDialog open={!!archiveTargetId} onOpenChange={open => { if (!open) setArchiveTargetId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Archive this target?</AlertDialogTitle>
            <AlertDialogDescription>
              Archived targets stop running and cannot be resumed. Existing job history is preserved.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleArchiveConfirm} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageShell>
  );
}
