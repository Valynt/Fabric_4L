/**
 * Screen 8 — Agent Workflows Dashboard
 * Design: Refined Enterprise SaaS
 * Data Flow: React Query for server state, Zustand for UI state
 */
import { useState } from "react";
import {
  Bot,
  Clock,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Eye,
  Pause,
  Play,
  Plus,
  MoreHorizontal,
  Loader2,
} from "lucide-react";
import {
  useActiveWorkflows,
  useWorkflowHistory,
  useCancelWorkflow,
  usePauseWorkflow,
  useResumeWorkflow,
  useCreateWorkflow,
  useWorkflowTypes,
  type Workflow,
} from "@/hooks/useWorkflows";
import { HarnessRunDetail } from "@/components/HarnessRunDetail";
import { QueryState } from "@/components/QueryState";
import { WorkflowDetail } from "@/components/WorkflowDetail";
import { Badge } from "@/components/ui/badge";
import type { HarnessRun } from "@/api/harness";
import { isTerminalState } from "@/api/harness";
import {
  useCancelHarnessRun,
  useHarnessGates,
  useHarnessRuns,
  useTransitionHarnessRun,
} from "@/hooks/useHarness";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { StatusBadge as StatusBadgePrimitive } from "@/components/ui/fabric";
import { Tabs } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, MetricCard, DataTable, Btn } from "@/components/ui/fabric";

const ITEMS_PER_PAGE = 10;

// Pagination display range helper
function getDisplayRange(
  page: number,
  itemsPerPage: number,
  total: number
): string {
  const start = page * itemsPerPage + 1;
  const end = Math.min((page + 1) * itemsPerPage, total);
  return `Showing ${start} - ${end} of ${total}`;
}

// Reusable pagination controls component
interface PaginationControlsProps {
  page: number;
  totalPages: number;
  hasMore: boolean;
  isLoading: boolean;
  displayRange: string;
  onPrevious: () => void;
  onNext: () => void;
  onRefresh: () => void;
}

function PaginationControls({
  page,
  totalPages,
  hasMore,
  isLoading,
  displayRange,
  onPrevious,
  onNext,
  onRefresh,
}: PaginationControlsProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-border/50 mt-2">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{displayRange}</span>
        {hasMore && (
          <span className="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
            More available
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Btn
          variant="ghost"
          onClick={onPrevious}
          disabled={page === 0 || isLoading}
          className="text-xs"
        >
          <ChevronLeft size={14} className="mr-1" /> Previous
        </Btn>
        <span className="text-xs text-muted-foreground/60">
          Page {page + 1} of {totalPages || 1}
        </span>
        <Btn
          variant="ghost"
          onClick={onNext}
          disabled={!hasMore || isLoading || page >= totalPages - 1}
          className="text-xs"
        >
          Next <ChevronRight size={14} className="ml-1" />
        </Btn>
        <div className="w-px h-4 bg-border mx-1" />
        <Btn
          variant="ghost"
          onClick={onRefresh}
          disabled={isLoading}
          className="text-xs"
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
        </Btn>
      </div>
    </div>
  );
}

export default function AgentWorkflows() {
  const [activeTab, setActiveTab] = useState("Workflow Dashboard");

  // Pagination state
  const [activePage, setActivePage] = useState(0);
  const [historyPage, setHistoryPage] = useState(0);

  // Detail drawer state
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(
    null
  );
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Harness state
  const [harnessRunId, setHarnessRunId] = useState<string | null>(null);
  const [isHarnessDetailOpen, setIsHarnessDetailOpen] = useState(false);
  const [harnessPage, setHarnessPage] = useState(0);
  const HARNESS_PAGE_SIZE = 20;

  const { data: harnessData, isLoading: harnessLoading, error: harnessError, refetch: refetchHarnessRuns } =
    useHarnessRuns({ limit: HARNESS_PAGE_SIZE, offset: harnessPage * HARNESS_PAGE_SIZE });
  const { data: harnessGatesData } = useHarnessGates(undefined); // for KPI count
  const harnessRuns = harnessData?.items ?? [];
  const harnessPendingGates = (harnessGatesData?.items ?? []).filter(g => g.status === "pending").length;

  const transitionRun = useTransitionHarnessRun();
  const cancelRun = useCancelHarnessRun();

  // Mutations
  const cancelWorkflow = useCancelWorkflow();
  const pauseWorkflow = usePauseWorkflow();
  const resumeWorkflow = useResumeWorkflow();
  const createWorkflow = useCreateWorkflow();
  const { data: workflowTypesData } = useWorkflowTypes();

  // Server state: React Query handles fetching, caching, loading, error
  const {
    data: activeData,
    isLoading: activeLoading,
    error: activeError,
    refetch: refetchActive,
  } = useActiveWorkflows({
    limit: ITEMS_PER_PAGE,
    offset: activePage * ITEMS_PER_PAGE,
  });

  const {
    data: historyData,
    isLoading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useWorkflowHistory({
    limit: ITEMS_PER_PAGE,
    offset: historyPage * ITEMS_PER_PAGE,
  });

  // Extract items from paginated response
  const activeWorkflows = activeData?.items ?? [];
  const historyWorkflows = historyData?.items ?? [];

  const isLoading = activeLoading || historyLoading;
  const error = activeError || historyError;

  // Pagination helpers
  const activeTotalPages = activeData
    ? Math.ceil(activeData.total / ITEMS_PER_PAGE)
    : 0;
  const historyTotalPages = historyData
    ? Math.ceil(historyData.total / ITEMS_PER_PAGE)
    : 0;

  return (
    <div className="p-6 max-w-5xl">
      <PageHeader
        breadcrumbs={[{ label: "Agent Workflows" }, { label: "Dashboard" }]}
        title="Workflow Dashboard"
        subtitle="Monitor and manage AI agent workflows across all active analyses."
        actions={
          <Btn
            variant="primary"
            onClick={() => {
              const types = workflowTypesData?.types;
              const defaultType = types?.[0]?.id || "analysis";
              createWorkflow.mutate({ type: defaultType });
            }}
            disabled={createWorkflow.isPending}
          >
            {createWorkflow.isPending ? (
              <Loader2 size={14} className="mr-1.5 animate-spin" />
            ) : (
              <Plus size={14} className="mr-1.5" />
            )}
            New Workflow
          </Btn>
        }
      />

      <Tabs
        tabs={["Workflow Dashboard", "Whitespace Analysis", "Business Cases", "Harness Runs"]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Active Workflows"
          value={activeWorkflows
            .filter((w: Workflow) => w.status === "running")
            .length.toString()}
          trend={isLoading ? "Loading..." : "Running now"}
          trendUp
        />
        <MetricCard
          label="Completed Today"
          value={historyWorkflows
            .filter((w: Workflow) => w.status === "completed")
            .length.toString()}
          trend="+4 vs yesterday"
          trendUp
        />
        <MetricCard
          label="Avg. Completion Time"
          value="3.2m"
          trend="Target: <5m"
        />
        <MetricCard
          label="Human-in-Loop Pending"
          value={(
            activeWorkflows.filter((w: Workflow) => w.status === "pending").length +
            harnessPendingGates
          ).toString()}
          trend="Needs review"
        />
      </div>

      {/* Active agents */}
      <SectionCard title="Active Agents" className="mb-5">
        <div className="p-4 space-y-3">
          <QueryState
            isLoading={isLoading}
            error={error}
            isEmpty={activeWorkflows.length === 0}
            emptyMessage="No active workflows."
            emptySubMessage="Start a new analysis to see agents in action."
            loadingMessage="Loading workflows…"
          >
            {activeWorkflows.map((workflow: Workflow) => (
              <div
                key={workflow.id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${
                  workflow.status === "pending"
                    ? "bg-amber-50 border-amber-200"
                    : "bg-muted/30 border-border"
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                    workflow.status === "pending"
                      ? "bg-amber-100"
                      : "bg-blue-100"
                  }`}
                >
                  {workflow.status === "pending" ? (
                    <AlertTriangle size={14} className="text-amber-600" />
                  ) : (
                    <Bot size={14} className="text-blue-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[12px] font-bold text-foreground font-mono">
                      {workflow.id}
                    </span>
                    <StatusBadgePrimitive
                      status={
                        workflow.status === "interrupted"
                          ? "failed"
                          : workflow.status
                      }
                    />
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    <span className="font-semibold">{workflow.name}</span>
                    {workflow.progress > 0 && (
                      <div className="flex items-center gap-2 mt-1.5">
                        <Progress
                          value={workflow.progress}
                          className="h-1.5 w-24"
                        />
                        <span className="text-[10px] text-muted-foreground/70">
                          {workflow.progress}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground/60">
                    <Clock size={10} />
                    {workflow.status}
                  </div>
                  {workflow.status === "running" && (
                    <Btn
                      variant="ghost"
                      className="text-[11px] text-amber-600 hover:text-amber-700"
                      onClick={() => pauseWorkflow.mutate(workflow.id)}
                      disabled={pauseWorkflow.isPending}
                    >
                      <Pause size={12} className="mr-1" />
                      {pauseWorkflow.isPending ? "..." : "Pause"}
                    </Btn>
                  )}
                  {workflow.status === "pending" && (
                    <Btn
                      variant="ghost"
                      className="text-[11px] text-green-600 hover:text-green-700"
                      onClick={() => resumeWorkflow.mutate(workflow.id)}
                      disabled={resumeWorkflow.isPending}
                    >
                      <Play size={12} className="mr-1" />
                      {resumeWorkflow.isPending ? "..." : "Resume"}
                    </Btn>
                  )}
                  {(workflow.status === "running" ||
                    workflow.status === "pending") && (
                    <Btn
                      variant="ghost"
                      className="text-[11px] text-red-600 hover:text-red-700"
                      onClick={() => cancelWorkflow.mutate(workflow.id)}
                      disabled={cancelWorkflow.isPending}
                    >
                      {cancelWorkflow.isPending ? "Cancelling..." : "Cancel"}
                    </Btn>
                  )}
                  <Btn
                    variant="ghost"
                    className="text-[11px]"
                    onClick={() => {
                      setSelectedWorkflow(workflow);
                      setIsDetailOpen(true);
                    }}
                  >
                    <Eye size={12} className="mr-1" />
                    View
                  </Btn>
                </div>
              </div>
            ))}
          </QueryState>

          {/* Active Workflows Pagination */}
          {activeData && activeData.total > ITEMS_PER_PAGE && (
            <PaginationControls
              page={activePage}
              totalPages={activeTotalPages}
              hasMore={activeData.has_more}
              isLoading={activeLoading}
              displayRange={getDisplayRange(
                activePage,
                ITEMS_PER_PAGE,
                activeData.total
              )}
              onPrevious={() => setActivePage(p => Math.max(0, p - 1))}
              onNext={() =>
                setActivePage(p => Math.min(activeTotalPages - 1, p + 1))
              }
              onRefresh={refetchActive}
            />
          )}
        </div>
      </SectionCard>

      {/* History */}
      <SectionCard title="Workflow History" noPad>
        <QueryState
          isLoading={historyLoading}
          error={historyError}
          isEmpty={historyWorkflows.length === 0}
          emptyMessage="No workflow history available."
        >
          <DataTable
            columns={[
              "Job ID",
              "Name",
              "Status",
              "Progress",
              "Created",
              "Actions",
            ]}
            rows={historyWorkflows.map((w: Workflow) => [
              <span className="font-mono text-[11px] text-muted-foreground">
                {w.id}
              </span>,
              <span className="text-foreground font-semibold">{w.name}</span>,
              <StatusBadgePrimitive
                status={w.status === "interrupted" ? "failed" : w.status}
              />,
              <span className="text-muted-foreground text-[11px]">
                {w.progress}%
              </span>,
              <span className="text-muted-foreground/60 text-[11px]">
                {w.createdAt ? new Date(w.createdAt).toLocaleDateString() : "-"}
              </span>,
              <div className="flex gap-2">
                <button
                  className="text-blue-600 text-[11px] hover:underline flex items-center gap-1"
                  onClick={() => {
                    setSelectedWorkflow(w);
                    setIsDetailOpen(true);
                  }}
                >
                  <Eye size={12} />
                  View
                </button>
              </div>,
            ])}
          />
        </QueryState>

        {/* Pagination Controls */}
        {historyData && historyData.total > ITEMS_PER_PAGE && (
          <PaginationControls
            page={historyPage}
            totalPages={historyTotalPages}
            hasMore={historyData.has_more}
            isLoading={historyLoading}
            displayRange={getDisplayRange(
              historyPage,
              ITEMS_PER_PAGE,
              historyData.total
            )}
            onPrevious={() => setHistoryPage(p => Math.max(0, p - 1))}
            onNext={() =>
              setHistoryPage(p => Math.min(historyTotalPages - 1, p + 1))
            }
            onRefresh={refetchHistory}
          />
        )}
      </SectionCard>

      {/* ── Harness Runs Tab ─────────────────────────────────────────── */}
      {activeTab === "Harness Runs" && (
        <SectionCard title="Harness Runs" noPad>
          <QueryState
            isLoading={harnessLoading}
            error={harnessError}
            isEmpty={harnessRuns.length === 0}
            emptyMessage="No harness runs yet."
            emptySubMessage="Harness-backed agent runs will appear here."
            loadingMessage="Loading harness runs…"
          >
            <DataTable
              columns={["Run ID", "Workflow Type", "State", "Status", "Created", "Actions"]}
              rows={harnessRuns.map((run: HarnessRun) => [
                <span key="id" className="font-mono text-xs text-muted-foreground truncate max-w-[120px] block">
                  {run.id}
                </span>,
                <span key="type" className="text-sm capitalize">
                  {run.workflow_type.replace(/_/g, " ")}
                </span>,
                <span key="state" className="font-mono text-xs">{run.current_state}</span>,
                <Badge
                  key="status"
                  variant="outline"
                  className={`text-xs ${
                    run.status === "completed" ? "text-emerald-700 border-emerald-200" :
                    run.status === "failed"    ? "text-red-700 border-red-200" :
                    run.status === "running"   ? "text-blue-700 border-blue-200" :
                    run.status === "waiting_for_human" ? "text-amber-700 border-amber-200" :
                    "text-slate-600 border-slate-200"
                  }`}
                >
                  {run.status.replace(/_/g, " ")}
                </Badge>,
                <span key="created" className="text-xs text-muted-foreground">
                  {new Date(run.created_at).toLocaleDateString()}
                </span>,
                <div key="actions" className="flex items-center gap-2">
                  <button
                    className="text-blue-600 text-[11px] hover:underline flex items-center gap-1"
                    onClick={() => { setHarnessRunId(run.id); setIsHarnessDetailOpen(true); }}
                  >
                    <Eye size={12} /> View
                  </button>
                  {!isTerminalState(run.current_state) && run.status === "running" && (
                    <button
                      className="text-slate-500 text-[11px] hover:underline"
                      onClick={() => transitionRun.mutate({
                        runId: run.id,
                        data: { to_state: "CANCELLED", human_override: true },
                      })}
                    >
                      Cancel
                    </button>
                  )}
                  {run.status === "failed" && (
                    <button
                      className="text-amber-600 text-[11px] hover:underline"
                      onClick={() => transitionRun.mutate({
                        runId: run.id,
                        data: { to_state: run.current_state, human_override: true },
                      })}
                    >
                      Retry
                    </button>
                  )}
                </div>,
              ])}
            />
          </QueryState>

          {harnessData && harnessData.total > HARNESS_PAGE_SIZE && (
            <PaginationControls
              page={harnessPage}
              totalPages={Math.ceil(harnessData.total / HARNESS_PAGE_SIZE)}
              hasMore={harnessData.has_more}
              isLoading={harnessLoading}
              displayRange={getDisplayRange(harnessPage, HARNESS_PAGE_SIZE, harnessData.total)}
              onPrevious={() => setHarnessPage(p => Math.max(0, p - 1))}
              onNext={() => setHarnessPage(p => p + 1)}
              onRefresh={() => refetchHarnessRuns()}
            />
          )}
        </SectionCard>
      )}

      {/* Workflow Detail Drawer */}
      <WorkflowDetail
        workflow={selectedWorkflow}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedWorkflow(null);
        }}
        onCancel={id => cancelWorkflow.mutate(id)}
      />

      {/* Harness Run Detail Sheet */}
      <HarnessRunDetail
        runId={harnessRunId}
        isOpen={isHarnessDetailOpen}
        onClose={() => { setIsHarnessDetailOpen(false); setHarnessRunId(null); }}
      />
    </div>
  );
}
