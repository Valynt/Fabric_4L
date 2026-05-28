/**
 * FormulaGovernance — Admin Tier 3 Page
 * 
 * Formula lifecycle management:
 * - Formula Registry (view all formulas)
 * - Version History (track formula changes)
 * - Approval Queue (approve/reject formula submissions)
 * 
 * Features:
 * - Search and filter by status, pack, owner
 * - Bulk actions for formula management
 * - Governance metadata tracking
 */

import { useState, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
  FlaskConical, CheckCircle2, Clock, AlertCircle, History, ChevronRight,
  Plus, Search, Filter, Tag, Users, Eye, Edit3, Trash2, GitBranch,
  ArrowUpDown, MoreHorizontal, Download, FileText, Check, X,
  MessageSquare, Shield, Loader2, RefreshCw, Send,
} from "lucide-react";
import { Skeleton, ErrorBoundary } from "@/components";
import { formatDate } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import {
  useFormulas,
  useFormulaApprovals,
  useApproveFormula,
  useSubmitFormula,
  type Formula,
  type ApprovalRequest,
  type FormulaStatus,
} from "@/hooks";
import { createFeatureLogger } from "@/lib/telemetry";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";

const log = createFeatureLogger('FormulaGovernance');

// ── Types ───────────────────────────────────────────────────────────────────────

type ApprovalAction = "approve" | "reject" | "request_changes";

function toggleSelection<T>(set: Set<T>, item: T): Set<T> {
  const newSet = new Set(set);
  if (newSet.has(item)) {
    newSet.delete(item);
  } else {
    newSet.add(item);
  }
  return newSet;
}

// ── Status Configuration ───────────────────────────────────────────────────────

const FORMULA_STATUS_CONFIG: Record<FormulaStatus, { 
  label: string; 
  color: string; 
  icon: React.ReactNode;
  description: string;
}> = {
  active: { 
    label: "Active",      
    color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20", 
    icon: <CheckCircle2 size={11}/>,
    description: "Approved and available for use",
  },
  draft: { 
    label: "Draft",       
    color: "bg-muted text-muted-foreground border-border", 
    icon: <Clock size={11}/>,
    description: "In development, not yet submitted",
  },
  pending: { 
    label: "Pending",     
    color: "bg-amber-500/10 text-amber-600 border-amber-500/20", 
    icon: <AlertCircle size={11}/>,
    description: "Awaiting approval review",
  },
  deprecated: { 
    label: "Deprecated", 
    color: "bg-destructive/10 text-destructive border-destructive/20", 
    icon: <History size={11}/>,
    description: "No longer recommended for use",
  },
  archived: { 
    label: "Archived", 
    color: "bg-muted text-muted-foreground border-border", 
    icon: <FileText size={11}/>,
    description: "Retired and preserved for reference",
  },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function FormulaStatusChip({ status }: { status: FormulaStatus }) {
  const config = FORMULA_STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${config.color}`}>
      {config.icon} {config.label}
    </span>
  );
}

function GovernanceScoreBadge({ score }: { score?: number }) {
  if (!score) return <span className="text-muted-foreground text-[11px]">—</span>;
  
  const color = score >= 90 ? "text-emerald-600" : 
                score >= 75 ? "text-blue-600" : 
                score >= 60 ? "text-amber-600" : "text-red-600";
  
  return (
    <div className="flex items-center gap-1">
      <Shield size={12} className={color} />
      <span className={`text-[11px] font-semibold ${color}`}>{score}</span>
    </div>
  );
}

function ApprovalQueueCard({ request, onAction }: { 
  request: ApprovalRequest; 
  onAction: (id: string, action: ApprovalAction) => void;
}) {
  return (
    <div className="bg-card border border-amber-500/20 rounded-xl p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-amber-500/10 text-amber-600 text-[10px] font-semibold px-2 py-0.5 rounded">
              Pending Approval
            </span>
            <span className="text-[11px] text-muted-foreground">
              Submitted {new Date(request.submitted_at).toLocaleDateString()}
            </span>
          </div>
          <h3 className="text-[14px] font-semibold text-foreground">{request.formula_name}</h3>
          <p className="text-[12px] text-muted-foreground mt-1">{request.change_summary}</p>
        </div>
        <div className="text-[11px] text-muted-foreground text-right">
          <p>By {request.submitted_by}</p>
          <p>v{request.previous_version} → new version</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <button 
          onClick={() => onAction(request.id, "approve")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white text-[11px] font-medium rounded-lg hover:bg-emerald-700 transition-colors"
        >
          <Check size={12}/> Approve
        </button>
        <button 
          onClick={() => onAction(request.id, "request_changes")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-card border border-border text-foreground text-[11px] font-medium rounded-lg hover:bg-muted transition-colors"
        >
          <MessageSquare size={12}/> Request Changes
        </button>
        <button 
          onClick={() => onAction(request.id, "reject")}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-card border border-destructive/20 text-destructive text-[11px] font-medium rounded-lg hover:bg-destructive/10 transition-colors"
        >
          <X size={12}/> Reject
        </button>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

type TabType = "registry" | "versions" | "approvals";

function FormulaGovernanceSkeleton() {
  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-9 w-28" />
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
        <div className="bg-muted border-b border-border px-4 py-3 flex gap-4">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="px-4 py-4 border-b border-border flex gap-4">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

function FormulaGovernanceContent() {
  const { pathname: location } = useLocation();
  const initialTab: TabType = location.includes("/approvals") ? "approvals"
    : location.includes("/versions") ? "versions"
    : "registry";
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | FormulaStatus>("all");
  const [selectedFormulas, setSelectedFormulas] = useState<Set<string>>(new Set());

  const { 
    data: formulas = [], 
    isLoading, 
    error,
    refetch: refetchFormulas
  } = useFormulas({ 
    status: statusFilter, 
    search: search || undefined 
  });
  
  const { 
    data: pendingApprovals = [],
    refetch: refetchApprovals
  } = useFormulaApprovals();

  const approveMutation = useApproveFormula();
  const submitMutation = useSubmitFormula();

  const stats = useMemo(() => {
    return formulas.reduce(
      (acc, formula) => {
        acc.total++;
        if (formula.status === "active") acc.active++;
        if (formula.status === "pending") acc.pending++;
        if (formula.status === "deprecated") acc.deprecated++;
        acc.governanceScoreSum += formula.governance_score || 0;
        return acc;
      },
      { total: 0, active: 0, pending: 0, deprecated: 0, governanceScoreSum: 0 }
    );
  }, [formulas]);

  const avgGovernanceScore = stats.total > 0 
    ? Math.round(stats.governanceScoreSum / stats.total) 
    : 0;

  const handleApprovalAction = async (id: string, action: ApprovalAction) => {
    try {
      await approveMutation.mutateAsync({ 
        formulaId: id, 
        action,
        reason: action === "request_changes" ? "Changes requested by admin" : undefined
      });
    } catch (err) {
      log.error(`Failed to ${action} formula`, { errorCode: String(err) });
    }
  };

  const toggleSelectAll = useMemo(() => {
    const allSelected = selectedFormulas.size === formulas.length && formulas.length > 0;
    return () => {
      setSelectedFormulas(allSelected ? new Set() : new Set(formulas.map((f) => f.id)));
    };
  }, [selectedFormulas.size, formulas]);

  if (isLoading) {
    return <FormulaGovernanceSkeleton />;
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl">
        <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-8 h-8 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-[14px] font-semibold text-destructive-foreground mb-1">Failed to load formula governance</h3>
              <p className="text-[12px] text-destructive/80">
                {error instanceof Error ? error.message : "An unexpected error occurred"}
              </p>
              <button 
                onClick={() => { refetchFormulas(); refetchApprovals(); }}
                className="mt-4 flex items-center gap-1.5 px-3 py-1.5 bg-destructive/20 text-destructive text-[12px] font-medium rounded-lg hover:bg-destructive/30 transition-colors"
              >
                <RefreshCw size={14} /> Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Formula Governance"
          subtitle="Manage the lifecycle of all governed formula assets — draft, review, approve, and deprecate."
        />
        <Btn variant="primary"><Plus size={13} className="mr-1"/> New Formula</Btn>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        {[
          { label: "Total Formulas", value: stats.total, icon: <FlaskConical size={14}/> },
          { label: "Active", value: stats.active, icon: <CheckCircle2 size={14}/>, color: "text-emerald-600" },
          { label: "Pending Review", value: stats.pending, icon: <AlertCircle size={14}/>, color: "text-amber-600" },
          { label: "Deprecated", value: stats.deprecated, icon: <History size={14}/>, color: "text-destructive" },
          { label: "Avg Gov Score", value: avgGovernanceScore, icon: <Shield size={14}/>, color: "text-blue-600" },
        ].map(s => (
          <div key={s.label} className="bg-card border border-border rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={s.color || "text-muted-foreground"}>{s.icon}</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{s.label}</span>
            </div>
            <p className={`text-[22px] font-extrabold ${s.color || "text-foreground"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Pending Approvals Callout */}
      {pendingApprovals.length > 0 && (
        <div className="mb-6">
          <h3 className="text-[13px] font-semibold text-foreground mb-3 flex items-center gap-2">
            <AlertCircle size={14} className="text-amber-600"/> 
            Pending Approvals ({pendingApprovals.length})
          </h3>
          {pendingApprovals.map((req: ApprovalRequest) => (
            <ApprovalQueueCard 
              key={req.id} 
              request={req} 
              onAction={handleApprovalAction}
            />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border mb-4">
        {[
          { id: "registry" as const, label: "Formula Registry", count: formulas.length },
          { id: "versions" as const, label: "Version History" },
          { id: "approvals" as const, label: "Approval Queue", count: pendingApprovals.length },
        ].map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2.5 text-[12px] font-medium transition-colors relative",
              activeTab === tab.id
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="flex items-center gap-2">
              {tab.label}
              {tab.count !== undefined && (
                <span className={cn(
                  "px-1.5 py-0.5 rounded text-[10px]",
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

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 max-w-sm flex-1">
          <Search size={12} className="text-muted-foreground shrink-0"/>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search formulas by name, pack, or owner..."
            aria-label="Search formulas"
            className="flex-1 text-[12px] bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
          />
        </div>
        <div className="flex items-center gap-1.5">
          {(["all", "active", "draft", "pending", "deprecated"] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              aria-pressed={statusFilter === s}
              className={`text-[11px] px-2.5 py-1.5 rounded-full border capitalize transition-colors font-medium ${
                statusFilter === s
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card text-muted-foreground border-border hover:border-primary"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
            <Download size={12}/> Export
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
            <Filter size={12}/> More Filters
          </button>
        </div>
      </div>

      {/* Formula Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-border bg-muted">
              <th className="w-10 px-3 py-3">
                <input 
                  type="checkbox" 
                  className="rounded border-border"
                  checked={selectedFormulas.size === formulas.length && formulas.length > 0}
                  onChange={toggleSelectAll}
                />
              </th>
              {["Formula Name", "Value Pack", "Version", "Status", "Owner", "Gov Score", "Used In", "Updated", ""].map(h => (
                <th key={h} className="text-left px-3 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                  {h === "Gov Score" ? <span className="flex items-center gap-1"><Shield size={10}/> Score</span> : h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {formulas.map((f: Formula) => (
              <tr key={f.id} className="hover:bg-muted transition-colors group">
                <td className="px-3 py-3">
                  <input 
                    type="checkbox" 
                    className="rounded border-border"
                    checked={selectedFormulas.has(f.id)}
                    onChange={() => setSelectedFormulas(toggleSelection(selectedFormulas, f.id))}
                  />
                </td>
                <td className="px-3 py-3">
                  <div className="flex items-center gap-2">
                    <FlaskConical size={14} className="text-violet-500 shrink-0"/>
                    <div>
                      <span className="font-medium text-foreground block">{f.name}</span>
                      {f.description && (
                        <span className="text-[10px] text-muted-foreground block truncate max-w-[200px]">{f.description}</span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-3 text-muted-foreground">{f.pack_name || "—"}</td>
                <td className="px-3 py-3 font-mono text-foreground">{f.version}</td>
                <td className="px-3 py-3"><FormulaStatusChip status={f.status as FormulaStatus}/></td>
                <td className="px-3 py-3 text-muted-foreground">{f.owner}</td>
                <td className="px-3 py-3"><GovernanceScoreBadge score={f.governance_score}/></td>
                <td className="px-3 py-3 text-foreground">{f.used_in_count || 0} assets</td>
                <td className="px-3 py-3 text-muted-foreground">{formatDate(f.updated_at)}</td>
                <td className="px-3 py-3">
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="View" aria-label="View formula">
                      <Eye size={13}/>
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="Edit" aria-label="Edit formula">
                      <Edit3 size={13}/>
                    </button>
                    {f.status === "draft" && (
                      <button
                        className="p-1.5 rounded hover:bg-primary/10 text-muted-foreground hover:text-primary"
                        title="Submit for Review"
                        aria-label="Submit formula for review"
                        onClick={() => submitMutation.mutate(f.id)}
                        disabled={submitMutation.isPending}
                      >
                        <Send size={13}/>
                      </button>
                    )}
                    <button className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive" title="Delete" aria-label="Delete formula">
                      <Trash2 size={13}/>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {formulas.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-[12px]">
            <FlaskConical size={32} className="mx-auto mb-3 text-muted-foreground/50"/>
            No formulas match your filters.
          </div>
        )}
      </div>

      {/* Bulk Actions Bar */}
      {selectedFormulas.size > 0 && (
        <div className="fixed bottom-6 left-[260px] right-6 bg-card border border-border rounded-xl shadow-lg px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-medium text-foreground">
              {selectedFormulas.size} selected
            </span>
            <div className="h-4 w-px bg-border" />
            <button className="text-[11px] text-muted-foreground hover:text-foreground" onClick={() => setSelectedFormulas(new Set())}>
              Clear
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
              Export
            </button>
            <button className="px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
              Archive
            </button>
            <button className="px-3 py-1.5 text-[11px] font-medium text-destructive hover:bg-destructive/10 rounded-lg transition-colors">
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FormulaGovernance() {
  return (
    <ErrorBoundary>
      <FormulaGovernanceContent />
    </ErrorBoundary>
  );
}
