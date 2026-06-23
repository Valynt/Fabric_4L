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
 * - Destructive action confirmations with tenant scope
 */

import { EmptyState } from "@/components/states";
import { useState, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
  FlaskConical, CheckCircle2, Clock, AlertCircle, History,
  Plus, Search, Filter, Shield, Eye, Edit3, Trash2, GitBranch,
  Download, FileText, Check, X, MessageSquare, Send} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import ErrorBoundary from "@/components/ErrorBoundary";
import { formatDate } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import {
  useFormulas,
  useFormulaApprovals,
  useApproveFormula,
  useSubmitFormula,
  type Formula,
  type ApprovalRequest,
  type FormulaStatus} from "@/hooks";
import { createFeatureLogger } from "@/lib/telemetry";
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
} from "@/components/admin";

const log = createFeatureLogger('FormulaGovernance');

// ── Types ───────────────────────────────────────────────────────────────────────

type ApprovalAction = "approve" | "reject" | "request_changes";
type TabType = "registry" | "versions" | "approvals";
type BulkAction = "export" | "archive" | "delete";

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
    color: "bg-success/10 text-success border-success/20",
    icon: <CheckCircle2 size={11}/>,
    description: "Approved and available for use"},
  draft: {
    label: "Draft",
    color: "bg-muted text-muted-foreground border-border",
    icon: <Clock size={11}/>,
    description: "In development, not yet submitted"},
  pending: {
    label: "Pending",
    color: "bg-warning/10 text-warning border-warning/20",
    icon: <AlertCircle size={11}/>,
    description: "Awaiting approval review"},
  deprecated: {
    label: "Deprecated",
    color: "bg-destructive/10 text-destructive border-destructive/20",
    icon: <History size={11}/>,
    description: "No longer recommended for use"},
  archived: {
    label: "Archived",
    color: "bg-muted text-muted-foreground border-border",
    icon: <FileText size={11}/>,
    description: "Retired and preserved for reference"}};

const STATUS_CHIPS = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "draft", label: "Draft" },
  { value: "pending", label: "Pending" },
  { value: "deprecated", label: "Deprecated" },
];

// ── Sub-components ─────────────────────────────────────────────────────────────

function FormulaStatusChip({ status }: { status: FormulaStatus }) {
  const config = FORMULA_STATUS_CONFIG[status];
  return (
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${config.color}`}>
      {config.icon} {config.label}
    </span>
  );
}

function GovernanceScoreBadge({ score }: { score?: number }) {
  if (!score) return <span className="text-muted-foreground vf-text-caption">—</span>;

  const color = score >= 90 ? "text-success" :
                score >= 75 ? "text-primary" :
                score >= 60 ? "text-warning" : "text-destructive";

  return (
    <div className="flex items-center gap-1">
      <Shield size={12} className={color} />
      <span className={`vf-text-caption font-semibold ${color}`}>{score}</span>
    </div>
  );
}

function ApprovalQueueCard({ request, onAction, isPending }: {
  request: ApprovalRequest;
  onAction: (id: string, action: ApprovalAction) => void;
  isPending?: boolean;
}) {
  return (
    <div className="bg-card border border-warning/20 rounded-xl p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-warning/10 text-warning vf-text-micro font-semibold px-2 py-0.5 rounded">
              Pending Approval
            </span>
            <span className="vf-text-caption text-muted-foreground">
              Submitted {new Date(request.submitted_at).toLocaleDateString()}
            </span>
          </div>
          <h3 className="vf-text-body-l font-semibold text-foreground">{request.formula_name}</h3>
          <p className="vf-text-body-s text-muted-foreground mt-1">{request.change_summary}</p>
        </div>
        <div className="vf-text-caption text-muted-foreground text-right">
          <p>By {request.submitted_by}</p>
          <p>v{request.previous_version} → new version</p>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Btn variant="primary" size="sm" onClick={() => onAction(request.id, "approve")} disabled={isPending}>
          <Check size={12} className="mr-1"/> Approve
        </Btn>
        <Btn variant="outline" size="sm" onClick={() => onAction(request.id, "request_changes")} disabled={isPending}>
          <MessageSquare size={12} className="mr-1"/> Request Changes
        </Btn>
        <Btn variant="danger" size="sm" onClick={() => onAction(request.id, "reject")} disabled={isPending}>
          <X size={12} className="mr-1"/> Reject
        </Btn>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

function FormulaGovernanceContent() {
  const { pathname: location } = useLocation();
  const initialTab: TabType = location.includes("/approvals") ? "approvals"
    : location.includes("/versions") ? "versions"
    : "registry";
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | FormulaStatus>("all");
  const [selectedFormulas, setSelectedFormulas] = useState<Set<string>>(new Set());
  const [bulkConfirm, setBulkConfirm] = useState<{ open: boolean; action: BulkAction }>({
    open: false,
    action: "delete"});

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
      refetchApprovals();
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

  const handleBulkConfirm = () => {
    setSelectedFormulas(new Set());
    setBulkConfirm({ open: false, action: "delete" });
  };

  return (
    <AdminShell
      title="Formula Governance"
      subtitle="Manage the lifecycle of all governed formula assets — draft, review, approve, and deprecate."
      fullWidth
      actions={
        <Btn variant="primary"><Plus size={13} className="mr-1"/> New Formula</Btn>
      }
      tabs={
        <AdminTabs
          tabs={[
            { id: "registry", label: "Formula Registry", count: formulas.length },
            { id: "versions", label: "Version History" },
            { id: "approvals", label: "Approval Queue", count: pendingApprovals.length },
          ]}
          activeTab={activeTab}
          onChange={(tabId) => setActiveTab(tabId as TabType)}
        />
      }
    >
      <AdminTabPanel tabId="registry" activeTab={activeTab}>
        <>
          <AdminStatsRow columns={5}>
            <AdminStatCard label="Total Formulas" value={stats.total} icon={<FlaskConical size={14}/>} />
            <AdminStatCard label="Active" value={stats.active} icon={<CheckCircle2 size={14}/>} color="success" />
            <AdminStatCard label="Pending Review" value={stats.pending} icon={<AlertCircle size={14}/>} color="warning" />
            <AdminStatCard label="Deprecated" value={stats.deprecated} icon={<History size={14}/>} color="destructive" />
            <AdminStatCard label="Avg Gov Score" value={avgGovernanceScore} icon={<Shield size={14}/>} color="primary" />
          </AdminStatsRow>

          <AdminFilterBar
            searchPlaceholder="Search formulas by name, pack, or owner..."
            searchValue={search}
            onSearchChange={setSearch}
            chips={STATUS_CHIPS}
            chipValue={statusFilter}
            onChipChange={(value) => setStatusFilter(value as "all" | FormulaStatus)}
            actions={
              <>
                <Btn variant="outline" size="sm"><Download size={12} className="mr-1"/> Export</Btn>
                <Btn variant="outline" size="sm"><Filter size={12} className="mr-1"/> More Filters</Btn>
              </>
            }
          />

          {isLoading ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center text-muted-foreground">Loading formulas…</div>
          ) : error ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center text-destructive">
              Failed to load formulas. {error instanceof Error ? error.message : ""}
            </div>
          ) : (
            <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
              <table className="w-full vf-text-body-s">
                <thead>
                  <tr className="border-b border-border bg-muted">
                    <th className="w-10 px-3 py-3">
                      <Checkbox
                        checked={selectedFormulas.size === formulas.length && formulas.length > 0}
                        onCheckedChange={toggleSelectAll}
                        aria-label="Select all formulas"
                      />
                    </th>
                    {["Formula Name", "Value Pack", "Version", "Status", "Owner", "Gov Score", "Used In", "Updated", ""].map(h => (
                      <th key={h} className="text-left px-3 py-3 vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">
                        {h === "Gov Score" ? <span className="flex items-center gap-1"><Shield size={10}/> Score</span> : h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {formulas.map((f: Formula) => (
                    <tr key={f.id} className="hover:bg-muted transition-colors group">
                      <td className="px-3 py-3">
                        <Checkbox
                          checked={selectedFormulas.has(f.id)}
                          onCheckedChange={() => setSelectedFormulas(toggleSelection(selectedFormulas, f.id))}
                          aria-label={`Select ${f.name}`}
                        />
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <FlaskConical size={14} className="text-primary shrink-0"/>
                          <div>
                            <span className="font-medium text-foreground block">{f.name}</span>
                            {f.description && (
                              <span className="vf-text-micro text-muted-foreground block truncate max-w-[200px]">{f.description}</span>
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
                        <AdminIconButtonGroup>
                          <AdminIconButton icon={Eye} label="View formula" />
                          <AdminIconButton icon={Edit3} label="Edit formula" />
                          {f.status === "draft" && (
                            <AdminIconButton
                              icon={Send}
                              label="Submit for review"
                              variant="primary"
                              onClick={() => submitMutation.mutate(f.id)}
                              disabled={submitMutation.isPending}
                            />
                          )}
                          <AdminIconButton
                            icon={Trash2}
                            label="Delete formula"
                            variant="destructive"
                            onClick={() => setBulkConfirm({ open: true, action: "delete" })}
                          />
                        </AdminIconButtonGroup>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {formulas.length === 0 && (
                <EmptyState
                  icon={FlaskConical}
                  title="No formulas match your filters"
                  description="Try adjusting your search or filter criteria."
                />
              )}
            </div>
          )}

          {/* Bulk Actions Bar */}
          {selectedFormulas.size > 0 && (
            <div className="fixed bottom-6 left-[260px] right-6 bg-card border border-border rounded-xl shadow-lg px-4 py-3 flex items-center justify-between z-40">
              <div className="flex items-center gap-3">
                <span className="vf-text-body-s font-medium text-foreground">
                  {selectedFormulas.size} selected
                </span>
                <div className="h-4 w-px bg-border" />
                <Btn variant="ghost" size="sm" onClick={() => setSelectedFormulas(new Set())}>
                  Clear
                </Btn>
              </div>
              <div className="flex items-center gap-2">
                <Btn variant="outline" size="sm" onClick={() => setBulkConfirm({ open: true, action: "export" })}>
                  Export
                </Btn>
                <Btn variant="outline" size="sm" onClick={() => setBulkConfirm({ open: true, action: "archive" })}>
                  Archive
                </Btn>
                <Btn variant="danger" size="sm" onClick={() => setBulkConfirm({ open: true, action: "delete" })}>
                  Delete
                </Btn>
              </div>
            </div>
          )}
        </>
      </AdminTabPanel>

      <AdminTabPanel tabId="versions" activeTab={activeTab}>
        <EmptyState
          icon={History}
          title="Version History"
          description="Formula version history will be available in an upcoming release."
        />
      </AdminTabPanel>

      <AdminTabPanel tabId="approvals" activeTab={activeTab}>
        <>
          {pendingApprovals.length > 0 ? (
            <div>
              <h3 className="vf-text-body-m font-semibold text-foreground mb-3 flex items-center gap-2">
                <AlertCircle size={14} className="text-warning"/>
                Pending Approvals ({pendingApprovals.length})
              </h3>
              {pendingApprovals.map((req: ApprovalRequest) => (
                <ApprovalQueueCard
                  key={req.id}
                  request={req}
                  onAction={handleApprovalAction}
                  isPending={approveMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={CheckCircle2}
              title="No pending approvals"
              description="All formula submissions have been reviewed."
            />
          )}
        </>
      </AdminTabPanel>

      <AdminConfirmDialog
        open={bulkConfirm.open}
        onOpenChange={(open) => !open && setBulkConfirm((prev) => ({ ...prev, open: false }))}
        title={
          bulkConfirm.action === "delete" ? "Delete Selected Formulas" :
          bulkConfirm.action === "archive" ? "Archive Selected Formulas" :
          "Export Selected Formulas"
        }
        description={
          bulkConfirm.action === "delete" ? `${selectedFormulas.size} formula(s) will be permanently deleted.` :
          bulkConfirm.action === "archive" ? `${selectedFormulas.size} formula(s) will be archived.` :
          `${selectedFormulas.size} formula(s) will be exported.`
        }
        tenantName="Current tenant"
        actionLabel={
          bulkConfirm.action === "delete" ? "Delete" :
          bulkConfirm.action === "archive" ? "Archive" :
          "Export"
        }
        variant={bulkConfirm.action === "delete" ? "destructive" : "warning"}
        onConfirm={handleBulkConfirm}
      />
    </AdminShell>
  );
}

export default function FormulaGovernance() {
  return (
    <ErrorBoundary>
      <FormulaGovernanceContent />
    </ErrorBoundary>
  );
}
