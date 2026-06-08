/**
 * PackManagement — Admin Tier 3 Page
 *
 * Value Pack lifecycle management:
 * - Pack Library (view all packs with status & industry)
 * - Composition details (drivers, formulas, benchmarks)
 *
 * Features:
 * - Search and filter by industry, status
 * - Fork / execute pack actions
 * - Composition counts
 */

import { useState, useMemo } from "react";
import {
  FolderKanban, Plus, Search, Eye, Edit3, GitBranch,
  CheckCircle2, Clock, AlertCircle, Archive, RefreshCw,
  Loader2, BarChart3, FlaskConical, ListChecks,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/formatters";
import ErrorBoundary from "@/components/ErrorBoundary";
import { Input } from "@/components/ui/input";
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
  useValuePacks,
  type ValuePack,
  type PackStatus,
} from "@/hooks/useValuePacks";
import { PageHeader, Btn } from "@/components/ui/fabric";

// ── Styling Constants ───────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<PackStatus, { color: string; icon: React.ReactNode; label: string }> = {
  published: { color: "bg-success/10 text-success border-success/20", icon: <CheckCircle2 size={11}/>, label: "Published" },
  active:    { color: "bg-success/10 text-success border-success/20", icon: <CheckCircle2 size={11}/>, label: "Active" },
  draft:     { color: "bg-muted text-muted-foreground border-border", icon: <Clock size={11}/>, label: "Draft" },
  archived:  { color: "bg-destructive/10 text-destructive border-destructive/20", icon: <Archive size={11}/>, label: "Archived" },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function PackStatusChip({ status }: { status: PackStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  return (
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${cfg.color}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
}


function PackManagementSkeleton() {
  return (
    <PageShell>
      <div className="flex items-start justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-card border border-border rounded-xl px-4 py-3">
            <Skeleton className="h-4 w-28 mb-2" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
      </div>
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
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

function PackManagementContent() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | PackStatus>("all");
  const [industryFilter, setIndustryFilter] = useState<"all" | string>("all");

  const {
    data: packs = [],
    isLoading,
    error,
    refetch,
  } = useValuePacks({
    status: statusFilter === "all" ? undefined : statusFilter,
    search: search || undefined,
  });

  const industries = useMemo(() =>
    Array.from(new Set(packs.map(p => p.industry))),
    [packs]
  );

  const filteredPacks = useMemo(() =>
    industryFilter === "all"
      ? packs
      : packs.filter(p => p.industry === industryFilter),
    [packs, industryFilter]
  );

  const stats = useMemo(() => ({
    total: packs.length,
    published: packs.filter(p => p.status === "published" || p.status === "active").length,
    draft: packs.filter(p => p.status === "draft").length,
    totalDrivers: packs.reduce((s, p) => s + (p.driver_count || 0), 0),
  }), [packs]);

  if (isLoading) {
    return (
      <PageShell>
        <PackManagementSkeleton />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load packs"
          description="An error occurred while loading pack data."
          error={error}
          onRetry={() => refetch()}
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Pack Management"
          subtitle="Create, manage, and publish value packs across industries and segments."
        />
        <Btn variant="primary"><Plus size={13} className="mr-1" /> New Pack</Btn>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Packs", value: stats.total, icon: <FolderKanban size={14} /> },
          { label: "Published", value: stats.published, icon: <CheckCircle2 size={14} />, color: "text-success" },
          { label: "Drafts", value: stats.draft, icon: <Clock size={14} />, color: "text-warning" },
          { label: "Total Drivers", value: stats.totalDrivers, icon: <ListChecks size={14} />, color: "text-primary" },
        ].map(s => (
          <div key={s.label} className="bg-card border border-border rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={s.color || "text-muted-foreground"}>{s.icon}</span>
              <span className="vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">{s.label}</span>
            </div>
            <p className={`text-2xl font-extrabold ${s.color || "text-foreground"}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 max-w-sm flex-1">
          <Search size={12} className="text-muted-foreground shrink-0" />
          <Input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search packs..."
            className="flex-1 vf-text-body-s bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
          />
        </div>
        <div className="flex items-center gap-1.5">
          {(["all", "published", "draft", "archived"] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "vf-text-caption px-2.5 py-1 rounded-full border capitalize transition-colors font-medium",
                statusFilter === s
                  ? "bg-foreground text-background border-foreground"
                  : "bg-card text-muted-foreground border-border hover:border-primary"
              )}
            >
              {s}
            </button>
          ))}
        </div>
        <Select value={industryFilter} onValueChange={setIndustryFilter}>
          <SelectTrigger className="w-full vf-text-caption">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Industries</SelectItem>
            {industries.map(ind => (
              <SelectItem key={ind} value={ind}>{ind}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Pack Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <table className="w-full vf-text-body-s">
          <thead>
            <tr className="border-b border-border bg-muted">
              {["Pack", "Industry", "Status", "Drivers", "Formulas", "Benchmarks", "Version", "Updated", ""].map(h => (
                <th key={h} className="text-left px-4 py-3 vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredPacks.map(p => (
              <tr key={p.id} className="hover:bg-muted transition-colors group">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FolderKanban size={14} className="text-primary shrink-0" />
                    <div>
                      <span className="font-medium text-foreground block">{p.name}</span>
                      {p.description && (
                        <span className="vf-text-micro text-muted-foreground line-clamp-1">{p.description}</span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{p.industry}</td>
                <td className="px-4 py-3"><PackStatusChip status={p.status} /></td>
                <td className="px-4 py-3 text-foreground">
                  <span className="flex items-center gap-1"><ListChecks size={11} /> {p.driver_count || 0}</span>
                </td>
                <td className="px-4 py-3 text-foreground">
                  <span className="flex items-center gap-1"><FlaskConical size={11} /> {p.formula_count || 0}</span>
                </td>
                <td className="px-4 py-3 text-foreground">
                  <span className="flex items-center gap-1"><BarChart3 size={11} /> {p.benchmark_count || 0}</span>
                </td>
                <td className="px-4 py-3 font-mono vf-text-caption text-muted-foreground">{p.version || "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{formatDate(p.updated_at)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="View">
                      <Eye size={13} />
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="Edit">
                      <Edit3 size={13} />
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-primary" title="Fork">
                      <GitBranch size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredPacks.length === 0 && (
          <div className="text-center py-12 text-muted-foreground vf-text-body-s">
            <FolderKanban size={32} className="mx-auto mb-3 text-muted-foreground/50" />
            No packs match your filters.
          </div>
        )}
      </div>
    </PageShell>
  );
}

export default function PackManagement() {
  return (
    <ErrorBoundary>
      <PackManagementContent />
    </ErrorBoundary>
  );
}
