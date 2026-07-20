/**
 * Ingestion Jobs Page
 * Design: Refined Enterprise SaaS
 *
 * Layout:
 *   - Page header with title, Refresh, and + New Job buttons
 *   - Filter controls (Status, Source, Date Range)
 *   - Job queue table (left, wide)
 *   - Actions panel with Run All, Pause (right top)
 *   - Job detail panel (right mid)
 *   - Logs/Output panel (right bottom)
 */
import { useState, useMemo, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Input } from "@/components/ui/input";
import { RefreshCw, Plus, Play, Pause, AlertCircle, Info, List, Sparkles } from 'lucide-react';
import { TopTabNav } from '@/components/blocks/TopTabNav';
import {
  SourceCorpusCard,
  AccountIntelligencePacketCard,
  SkillOutputPanel,
} from '@/components/skill-outputs';
import {
  useSourceCorpora,
  useAccountIntelligencePackets,
} from '@/hooks/useSkillJobs';
import { toast } from 'sonner';
import { PaginationBar } from '@/components/ui/fabric/PaginationBar';
import { LoadingState } from '@/components/states';
import { useNavigation, usePaginatedList } from '@/hooks';
import { DataTable, type DataTableColumn } from '@/components/ui/fabric/DataTable';
import { StatusBadge } from '@/components/ui/fabric/StatusBadge';
import { useIngestionJobsStore, type JobStatusFilter } from '@/stores/ingestionJobsStore';
import { createFeatureLogger } from '@/lib/telemetry';
import {
  useIngestionJobList,
  useIngestionJobDetail,
  useJobComplianceLogs,
  useCancelJob,
  useRetryJob,
  useBatchOperation,
  type JobListFilters,
  type IngestionJob,
  type BatchOperationRequest,
} from '@/hooks/useIngestion';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell, ErrorState, EmptyState } from '@/components';

const log = createFeatureLogger('IngestionJobs');
const PAGE_SIZE = 15;

// UUID validation regex pattern (RFC 4122 format)
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const STATUS_OPTIONS: { value: JobStatusFilter; label: string }[] = [
  { value: 'all', label: 'All Status' },
  { value: 'pending', label: 'Pending' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Processed' },
  { value: 'failed', label: 'Failed' },
];

const STAGE_STATUS_COLORS = {
  COMPLETED: 'text-success',
  FAILED: 'text-destructive',
  RUNNING: 'text-warning',
  DEFAULT: 'text-muted-foreground',
} as const;

const JOB_ID_TRUNCATE_TABLE = 8;
const JOB_ID_TRUNCATE_DETAIL = 16;

function truncateId(id: string, length: number): string {
  if (!id || id.length <= length) return id ?? '—';
  return `${id.slice(0, length)}...`;
}

const JOB_STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'outline' | 'destructive' | 'success' | 'warning' | 'info' | 'pending'> = {
  completed: 'success',
  processing: 'warning',
  pending: 'pending',
  failed: 'destructive',
};

export default function IngestionJobs() {
  const [searchParams, setSearchParams] = useSearchParams();

  // UI state from Zustand store
  const { selectedJobId, setSelectedJobId, filters, setStatusFilter, setDateFrom, setDateTo, resetFilters } =
    useIngestionJobsStore();

  // Pagination state using usePaginatedList hook
  const paginationState = usePaginatedList({
    initialPage: searchParams.get('page') ? Math.max(1, parseInt(searchParams.get('page')!, 10)) : 1,
    initialPageSize: 15,
    mode: 'server',
  });

  // Initialize selected job from URL on mount (only once)
  useEffect(() => {
    const jobId = searchParams.get('job');
    if (jobId) setSelectedJobId(jobId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only on mount

  // Sync page and selected job to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (paginationState.page > 1) params.set('page', String(paginationState.page));
    if (selectedJobId) params.set('job', selectedJobId);
    setSearchParams(params, { replace: true });
  }, [paginationState.page, selectedJobId, setSearchParams]);

  // Build API filters
  const apiFilters: JobListFilters = useMemo(
    () => ({
      status: filters.status === 'all' ? undefined : [filters.status.toUpperCase()],
      dateFrom: filters.dateFrom || undefined,
      dateTo: filters.dateTo || undefined,
      sortBy: 'created_at',
      sortOrder: 'desc',
      page: paginationState.page,
      limit: paginationState.limit,
    }),
    [filters, paginationState.page, paginationState.limit]
  );

  // Data fetching
  const { data: listData, isLoading: listLoading, error: listError, refetch } = useIngestionJobList(apiFilters);
  const { data: detailData, isLoading: detailLoading } = useIngestionJobDetail(selectedJobId);
  const { data: logsData, isLoading: logsLoading } = useJobComplianceLogs(selectedJobId);

  // Mutations
  const cancelJob = useCancelJob();
  const retryJob = useRetryJob();
  const batchOperation = useBatchOperation();

  const jobs = useMemo(() => listData?.jobs ?? [], [listData]);
  const apiPagination = listData?.pagination ?? { page: 1, limit: paginationState.limit, total: 0, totalPages: 1 };
  const latestJob = jobs[0];

  const { navigateTo } = useNavigation();

  // Handlers
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleNewJob = useCallback(() => {
    navigateTo('home');
  }, [navigateTo]);

  const handleRowClick = useCallback((job: IngestionJob) => {
    setSelectedJobId(job.id === selectedJobId ? null : job.id);
  }, [selectedJobId, setSelectedJobId]);

  const handleCancelJob = useCallback(async () => {
    if (!selectedJobId || cancelJob.isPending) return;
    try {
      await cancelJob.mutateAsync(selectedJobId);
    } catch {
      // Error is handled by mutation state and displayed in UI
    }
  }, [selectedJobId, cancelJob]);

  const handleRetryJob = useCallback(async () => {
    if (!selectedJobId || retryJob.isPending) return;
    try {
      await retryJob.mutateAsync(selectedJobId);
    } catch {
      // Error is handled by mutation state and displayed in UI
    }
  }, [selectedJobId, retryJob]);

  const handleBatchRetry = useCallback(async () => {
    if (batchOperation.isPending || jobs.length === 0) return;
    
    // Filter failed jobs and validate UUID format in a single pass
    const validJobIds = jobs.flatMap(j =>
      j.status === 'failed' && UUID_REGEX.test(j.id) ? [j.id] : []
    );
    
    // Validate that we have valid UUIDs to retry
    if (validJobIds.length === 0) {
      toast.error('Failed job IDs are not valid UUIDs');
      return;
    }
    
    try {
      const request: BatchOperationRequest = {
        operation: 'retry',
        job_ids: validJobIds,
      };
      await batchOperation.mutateAsync(request);
      toast.success(`Retrying ${validJobIds.length} failed job(s)`);
    } catch (error) {
      log.error('Batch retry failed', { error: error instanceof Error ? error.message : String(error) });
      toast.error('Failed to retry jobs. Please try again.');
    }
  }, [batchOperation, jobs]);

  // Workspace tab state
  const [activeTab, setActiveTab] = useState<'jobs' | 'skill-outputs'>('jobs');
  const [selectedSkillJobId, setSelectedSkillJobId] = useState<string | null>(null);

  const INGESTION_TABS = [
    { id: 'jobs', label: 'Job Queue', icon: List },
    { id: 'skill-outputs', label: 'Skill Outputs', icon: Sparkles },
  ] as const;

  // Table columns definition using fabric DataTable format
  const columns: DataTableColumn<IngestionJob>[] = [
    { key: 'id', header: 'Job ID', render: (job) => (
      <span className="font-mono vf-text-caption text-muted-foreground">
        {truncateId(job.id, JOB_ID_TRUNCATE_TABLE)}
      </span>
    )},
    { key: 'domain', header: 'Domain', render: (job) => (
      <span className="font-medium text-foreground truncate max-w-[150px]" title={job.domain}>
        {job.domain}
      </span>
    )},
    { key: 'status', header: 'Status', render: (job) => (
      <StatusBadge variant={JOB_STATUS_VARIANTS[job.status] ?? 'default'}>
        {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
      </StatusBadge>
    )},
    { key: 'progress', header: 'Progress', render: (job) => (
      <div className="flex items-center gap-2">
        <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all"
            style={{ width: `${job.progress}%` }}
          />
        </div>
        <span className="vf-text-caption text-muted-foreground">{job.progress}%</span>
      </div>
    )},
    { key: 'createdAt', header: 'Created', render: (job) => (
      <span className="vf-text-caption text-muted-foreground">
        {new Date(job.createdAt).toLocaleDateString()}
      </span>
    )},
  ];

  return (
    <PageShell>
    <TooltipProvider>
    <div className="h-full flex flex-col">
      {/* Page Header */}
      <PageHeader
        title="Ingestion Jobs"
        subtitle="Monitor and manage data ingestion pipeline"
        actions={
          <div className="flex items-center gap-2">
            <Btn variant="ghost" onClick={handleRefresh} disabled={listLoading}>
              <RefreshCw size={13} className={listLoading ? 'animate-spin' : ''} />
              Refresh
            </Btn>
            <Btn variant="primary" onClick={handleNewJob}>
              <Plus size={13} />
              New Job
            </Btn>
          </div>
        }
      />

      {/* Horizontal tab navigation */}
      <TopTabNav
        tabs={INGESTION_TABS as unknown as import('@/components/blocks/TopTabNav').TopTabItem[]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as 'jobs' | 'skill-outputs')}
        className="mb-4"
      />

      {/* Skill Outputs tab */}
      {activeTab === 'skill-outputs' && (
        <SkillOutputsWorkspace
          selectedJobId={selectedSkillJobId}
          onSelectJob={setSelectedSkillJobId}
        />
      )}

      {/* Main Content Grid — Job Queue tab */}
      {activeTab === 'jobs' && (
      <div className="flex-1 grid grid-cols-[1fr_320px] gap-4 min-h-0">
        {/* Left Column: Filters + Job Queue */}
        <div className="flex flex-col gap-4 min-h-0">
          {latestJob && (
            <div className="bg-card border border-border rounded-lg px-3 py-2 flex items-center gap-2">
              <Info size={14} className="text-primary shrink-0" />
              <p className="vf-text-body-s text-muted-foreground">
                Latest ingestion job:
                {' '}<span className="font-semibold text-foreground">{latestJob.domain}</span>
                {' '}is
                {' '}<span className="font-semibold text-foreground">
                  {latestJob.status.charAt(0).toUpperCase() + latestJob.status.slice(1)}
                </span>
                {' '}with
                {' '}<span className="font-semibold text-foreground">{latestJob.progress}%</span>
                {' '}progress from Layer 1.
              </p>
            </div>
          )}

          {/* Filter Controls */}
          <div className="bg-card border border-border rounded-lg p-3 flex items-center gap-3 flex-wrap">
            <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground">Filter Controls</span>
            <div className="flex items-center gap-2">
              <label className="vf-text-caption text-muted-foreground">Status:</label>
              <Select value={filters.status} onValueChange={(v) => { setStatusFilter(v as JobStatusFilter); paginationState.setPage(1); }}>
                <SelectTrigger className="w-[140px] vf-text-body-s"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <label className="vf-text-caption text-muted-foreground">From:</label>
              <Input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  paginationState.setPage(1);
                }}
                className="vf-text-body-s"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="vf-text-caption text-muted-foreground">To:</label>
              <Input
                type="date"
                value={filters.dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  paginationState.setPage(1);
                }}
                className="vf-text-body-s"
              />
            </div>
            {(filters.status !== 'all' || filters.dateFrom || filters.dateTo) && (
              <button
                onClick={() => {
                  resetFilters();
                  paginationState.setPage(1);
                }}
                className="vf-text-caption text-primary hover:underline ml-auto"
              >
                Reset filters
              </button>
            )}
          </div>

          {/* Job Queue Table */}
          <div className="bg-card border border-border rounded-lg flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="px-4 pt-3 pb-2 border-b border-border flex items-center justify-between">
              <span className="vf-text-body-m font-bold text-foreground">Job Queue</span>
              <span className="vf-text-caption text-muted-foreground">
                {apiPagination.total} total jobs
              </span>
            </div>
            <div className="flex-1 overflow-auto">
              {listLoading ? (
                <div className="p-4 space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : listError ? (
                <ErrorState
                  title="Failed to load jobs"
                  description="Something went wrong while fetching the job queue."
                  error={listError}
                  onRetry={handleRefresh}
                />
              ) : jobs.length === 0 ? (
                <EmptyState
                  title={filters.status !== 'all' || filters.dateFrom || filters.dateTo ? 'No jobs match your filters' : 'No jobs found'}
                  description={filters.status !== 'all' || filters.dateFrom || filters.dateTo ? 'Try adjusting your filter criteria' : 'Create a new job to get started'}
                  icon={List}
                />
              ) : (
                <DataTable
                  data={jobs}
                  columns={columns}
                  keyExtractor={(job) => job.id}
                  onRowClick={handleRowClick}
                  selectedKey={selectedJobId ?? undefined}
                />
              )}
            </div>
            {/* Pagination */}
            <PaginationBar
              page={paginationState.page}
              pageSize={paginationState.pageSize}
              totalPages={apiPagination.totalPages}
              canPrevious={paginationState.page > 1}
              canNext={paginationState.page < apiPagination.totalPages}
              onPrevious={() => paginationState.setPage(paginationState.page - 1)}
              onNext={() => paginationState.setPage(paginationState.page + 1)}
              onPageChange={(newPage) => paginationState.setPage(newPage)}
              summaryVariant="page"
            />
          </div>
        </div>

        {/* Right Column: Actions + Job Detail + Logs */}
        <div className="flex flex-col gap-4 min-h-0">
          {/* Actions Panel */}
          <div className="bg-card border border-border rounded-lg p-3">
            <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground block mb-2">
              Actions
            </span>
            <div className="flex items-center gap-2">
              <Btn
                variant="outline"
                className="flex-1"
                onClick={handleBatchRetry}
                disabled={batchOperation.isPending || jobs.filter(j => j.status === 'failed').length === 0}
              >
                <Play size={13} />
                {batchOperation.isPending ? 'Retrying...' : 'Retry Failed'}
              </Btn>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Btn variant="outline" className="flex-1" disabled>
                    <Pause size={13} />
                    Pause
                  </Btn>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p className="vf-text-caption">Batch Pause — coming in future release</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Job Detail Panel */}
          <div className="bg-card border border-border rounded-lg flex-1 flex flex-col min-h-0">
            <div className="px-4 pt-3 pb-2 border-b border-border">
              <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground">Job Detail</span>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {!selectedJobId ? (
                <p data-testid="job-detail-empty-state" className="vf-text-body-s text-muted-foreground text-center py-8">
                  Select a job from the queue to view details
                </p>
              ) : detailLoading ? (
                <div className="space-y-3" data-testid="job-detail-loading-state">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ) : detailData ? (
                <div className="space-y-3 vf-text-body-s">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ID:</span>
                    <span className="font-mono vf-text-caption">{truncateId(detailData.id, JOB_ID_TRUNCATE_DETAIL)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <StatusBadge variant={JOB_STATUS_VARIANTS[detailData.status] ?? 'default'}>
                      {detailData.status.charAt(0).toUpperCase() + detailData.status.slice(1)}
                    </StatusBadge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Priority:</span>
                    <span>{detailData.priority}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Domain:</span>
                    <span className="truncate max-w-[150px]" title={detailData.domain}>
                      {detailData.domain}
                    </span>
                  </div>
                  <div className="border-t border-border pt-2 mt-2">
                    <span className="vf-text-micro font-semibold uppercase text-muted-foreground block mb-1">
                      Progress
                    </span>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${detailData.progress?.percentComplete ?? 0}%` }}
                        />
                      </div>
                      <span className="vf-text-caption">{detailData.progress?.percentComplete ?? 0}%</span>
                    </div>
                    <div className="vf-text-caption text-muted-foreground">
                      {detailData.progress?.processedPages ?? 0} / {detailData.progress?.totalPages ?? '?'} pages
                    </div>
                  </div>
                  {detailData.stages && detailData.stages.length > 0 && (
                    <div className="border-t border-border pt-2">
                      <span className="vf-text-micro font-semibold uppercase text-muted-foreground block mb-1">
                        Stages
                      </span>
                      <div className="space-y-1">
                        {detailData.stages.map((stage, i) => (
                          <div key={i} className="flex items-center justify-between vf-text-caption">
                            <span className="truncate">{stage.stage}</span>
                            <span
                              className={
                                STAGE_STATUS_COLORS[stage.status as keyof typeof STAGE_STATUS_COLORS] ??
                                STAGE_STATUS_COLORS.DEFAULT
                              }
                            >
                              {stage.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {detailData.errors && detailData.errors.length > 0 && (
                    <div className="border-t border-border pt-2">
                      <span className="vf-text-micro font-semibold uppercase text-destructive block mb-1">
                        Errors ({detailData.errors.length})
                      </span>
                      <div className="space-y-1 max-h-24 overflow-auto">
                        {detailData.errors.map((err) => (
                          <div key={err.id} className="vf-text-caption text-destructive p-1 bg-destructive/5 rounded">
                            <div className="font-semibold">{err.errorCode}</div>
                            <div className="truncate">{err.errorMessage}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* Action Buttons */}
                  <div className="border-t border-border pt-3 flex gap-2">
                    {detailData.status === 'failed' && (
                      <Btn variant="primary" className="flex-1" onClick={handleRetryJob} disabled={retryJob.isPending}>
                        {retryJob.isPending ? 'Retrying...' : 'Retry Job'}
                      </Btn>
                    )}
                    {(detailData.status === 'pending' || detailData.status === 'processing') && (
                      <Btn
                        variant="danger"
                        className="flex-1"
                        onClick={handleCancelJob}
                        disabled={cancelJob.isPending}
                      >
                        {cancelJob.isPending ? 'Cancelling...' : 'Cancel Job'}
                      </Btn>
                    )}
                  </div>
                  {/* Mutation Error Display */}
                  {(retryJob.error || cancelJob.error) && (
                    <div className="mt-2 p-2 bg-destructive/10 border border-destructive/20 rounded vf-text-caption text-destructive">
                      <div className="flex items-start gap-1.5">
                        <AlertCircle size={12} className="mt-0.5 shrink-0" />
                        <div>
                          <p className="font-semibold">Action failed</p>
                          <p className="text-destructive/80">
                            {retryJob.error?.message || cancelJob.error?.message || 'Please try again'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <p className="vf-text-body-s text-muted-foreground text-center py-8">Job not found</p>
              )}
            </div>
          </div>

          {/* Logs / Output Panel */}
          <div className="bg-card border border-border rounded-lg h-48 flex flex-col">
            <div className="px-4 pt-3 pb-2 border-b border-border">
              <span className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground">
                Logs / Output
              </span>
            </div>
            <div className="flex-1 overflow-auto p-3">
              {!selectedJobId ? (
                <p className="vf-text-caption text-muted-foreground text-center py-4">
                  Select a job to view logs
                </p>
              ) : logsLoading ? (
                <div className="space-y-2" data-testid="job-logs-loading-state">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ) : logsData && logsData.length > 0 ? (
                <div className="space-y-1" data-testid="job-logs-list-state">
                  {logsData.map((log) => (
                    <div key={log.id} className="vf-text-caption border-b border-border/50 pb-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={
                            log.severity === 'ERROR'
                              ? 'text-destructive font-semibold'
                              : log.severity === 'WARNING'
                              ? 'text-warning'
                              : 'text-muted-foreground'
                          }
                        >
                          {log.severity}
                        </span>
                        <span className="text-muted-foreground">
                          {new Date(log.createdAt).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="text-foreground truncate" title={log.eventType}>
                        {log.eventType}
                      </div>
                      {log.requestUrl && (
                        <div className="text-muted-foreground truncate vf-text-micro" title={log.requestUrl}>
                          {log.requestUrl}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p data-testid="job-logs-empty-state" className="vf-text-caption text-muted-foreground text-center py-4">No logs available</p>
              )}
            </div>
          </div>
        </div>
      </div>
      )}
    </div>
    </TooltipProvider>
    </PageShell>
  );
}

// =============================================================================
// Skill Outputs workspace — shown when "Skill Outputs" tab is active
// =============================================================================

interface SkillOutputsWorkspaceProps {
  selectedJobId: string | null;
  onSelectJob: (jobId: string | null) => void;
}

function SkillOutputsWorkspace({ selectedJobId, onSelectJob }: SkillOutputsWorkspaceProps) {
  const [activeSubTab, setActiveSubTab] = useState<'corpora' | 'packets'>('corpora');
  const [selectedCorpusJobId, setSelectedCorpusJobId] = useState<string | null>(null);
  const [selectedPacketJobId, setSelectedPacketJobId] = useState<string | null>(null);

  const { data: corporaData, isLoading: corporaLoading } = useSourceCorpora();
  const { data: packetsData, isLoading: packetsLoading } = useAccountIntelligencePackets();

  const SKILL_SUBTABS = [
    { id: 'corpora', label: 'Source Corpora' },
    { id: 'packets', label: 'Account Intelligence' },
  ] as const;

  const activeJobId = activeSubTab === 'corpora' ? selectedCorpusJobId : selectedPacketJobId;

  return (
    <div className="flex-1 flex gap-4 min-h-0">
      {/* Left: list */}
      <div className="flex-1 flex flex-col min-h-0 bg-card border border-border rounded-xl overflow-hidden">
        <TopTabNav
          tabs={SKILL_SUBTABS as unknown as import('@/components/blocks/TopTabNav').TopTabItem[]}
          activeTab={activeSubTab}
          onChange={(id) => setActiveSubTab(id as 'corpora' | 'packets')}
        />

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {activeSubTab === 'corpora' && (
            <>
              {corporaLoading && <LoadingState message="Loading corpora…" />}
              {!corporaLoading && !corporaData?.items.length && (
                <EmptyState
                  icon={List}
                  title="No source corpora yet"
                  description="Launch a licensing company intake job to create one."
                />
              )}
              {corporaData?.items.map((corpus) => (
                <SourceCorpusCard
                  key={corpus.id}
                  corpus={corpus}
                  selected={selectedCorpusJobId === corpus.id}
                  onSelect={(id) => setSelectedCorpusJobId(id === selectedCorpusJobId ? null : id)}
                />
              ))}
            </>
          )}

          {activeSubTab === 'packets' && (
            <>
              {packetsLoading && <LoadingState message="Loading packets…" />}
              {!packetsLoading && !packetsData?.items.length && (
                <EmptyState
                  icon={Sparkles}
                  title="No account intelligence packets yet"
                  description="Launch a prospect research job to create one."
                />
              )}
              {packetsData?.items.map((packet) => (
                <AccountIntelligencePacketCard
                  key={packet.id}
                  packet={packet}
                  selected={selectedPacketJobId === packet.id}
                  onSelect={(id) => setSelectedPacketJobId(id === selectedPacketJobId ? null : id)}
                />
              ))}
            </>
          )}
        </div>
      </div>

      {/* Right rail: skill output detail panel */}
      {activeJobId && (
        <SkillOutputPanel
          jobId={activeJobId}
          onClose={() => {
            if (activeSubTab === 'corpora') setSelectedCorpusJobId(null);
            else setSelectedPacketJobId(null);
          }}
          className="rounded-xl border border-border"
        />
      )}
    </div>
  );
}
