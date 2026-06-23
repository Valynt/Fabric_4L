/**
 * BenchmarkPolicies — Admin Tier 3 Page
 *
 * Industry benchmark management - Benchmark Library view.
 *
 * Features:
 * - Confidence scoring and source tracking
 * - Industry/vertical filtering
 */

import { useState, useMemo } from "react";
import {
  BarChart3, Plus, Eye, Edit3, Trash2,
  Globe, Database, CheckCircle2, AlertTriangle, TrendingUp,
  Download, Info,
} from "lucide-react";
import { formatDate } from "@/lib/formatters";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useBenchmarks,
  type Benchmark,
  type ConfidenceLevel,
  type BenchmarkStatus,
} from "@/hooks";
import { Btn } from "@/components/ui/fabric";
import {
  AdminShell,
  AdminStatCard,
  AdminStatsRow,
  AdminFilterBar,
  AdminDataTable,
  AdminIconButton,
  AdminIconButtonGroup,
  AdminConfirmDialog,
  type AdminDataTableColumn,
} from "@/components/admin";

// ── Styling Constants ───────────────────────────────────────────────────────────

const CONFIDENCE_STYLES: Record<ConfidenceLevel, { color: string; bg: string; icon: React.ReactNode }> = {
  High:   { color: "text-success", bg: "bg-success/10", icon: <CheckCircle2 size={12}/> },
  Medium: { color: "text-warning", bg: "bg-warning/10", icon: <Info size={12}/> },
  Low:    { color: "text-destructive", bg: "bg-destructive/10", icon: <AlertTriangle size={12}/> },
};

const STATUS_STYLES: Record<BenchmarkStatus, string> = {
  active: "bg-success/10 text-success border-success/20",
  draft: "bg-muted text-muted-foreground border-border",
  deprecated: "bg-destructive/10 text-destructive border-destructive/20",
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const style = CONFIDENCE_STYLES[level];
  return (
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full ${style.bg} ${style.color}`}>
      {style.icon} {level}
    </span>
  );
}

function StatusBadge({ status }: { status: BenchmarkStatus }) {
  return (
    <span className={`inline-flex items-center vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}

function StaleWarningBadge({ lastVerified }: { lastVerified?: string }) {
  if (!lastVerified) return null;
  const lastVerifiedDate = new Date(lastVerified);
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

  if (lastVerifiedDate > oneYearAgo) return null;

  return (
    <span className="inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full bg-warning/10 text-warning border border-warning/20 ml-2">
      <AlertTriangle size={10}/> Stale — Last verified {lastVerifiedDate.getFullYear()}
    </span>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

function BenchmarkPoliciesContent() {
  const [search, setSearch] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState<"all" | ConfidenceLevel>("all");
  const [industryFilter, setIndustryFilter] = useState<"all" | string>("all");
  const [deleteTarget, setDeleteTarget] = useState<Benchmark | null>(null);

  const {
    data: benchmarks = [],
    isLoading: benchmarksLoading,
    error: benchmarksError,
    refetch: refetchBenchmarks
  } = useBenchmarks({
    confidence: confidenceFilter === "all" ? undefined : confidenceFilter,
    search: search || undefined,
  });

  const industries = useMemo(() =>
    Array.from(new Set(benchmarks.map((b: Benchmark) => b.industry))),
    [benchmarks]
  );

  const filteredBenchmarks = useMemo(() =>
    industryFilter === "all"
      ? benchmarks
      : benchmarks.filter((b: Benchmark) => b.industry === industryFilter),
    [benchmarks, industryFilter]
  );

  const stats = useMemo(() => ({
    total: benchmarks.length,
    highConfidence: benchmarks.filter((b: Benchmark) => b.confidence === "High").length,
    active: benchmarks.filter((b: Benchmark) => b.status === "active").length,
    totalUsage: benchmarks.reduce((s: number, b: Benchmark) => s + (b.usage_count || 0), 0),
  }), [benchmarks]);

  const benchmarkColumns: AdminDataTableColumn<Benchmark>[] = [
    {
      key: "name",
      header: "Benchmark",
      render: (b) => (
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-primary shrink-0"/>
          <div>
            <span className="font-medium text-foreground block">{b.name}</span>
            {b.tags.length > 0 && (
              <div className="flex items-center gap-1 mt-1">
                {b.tags.map(tag => (
                  <span key={tag} className="vf-text-micro px-1.5 py-0.5 bg-muted text-muted-foreground rounded">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "industry",
      header: "Industry",
      render: (b) => (
        <span className="text-muted-foreground">
          {b.industry}
          {b.vertical && <span className="text-muted-foreground"> / {b.vertical}</span>}
        </span>
      ),
    },
    {
      key: "value_range",
      header: "Value Range",
      render: (b) => <span className="font-mono vf-text-caption text-foreground">{b.value_range}</span>,
    },
    {
      key: "confidence",
      header: "Confidence",
      render: (b) => (
        <div className="flex items-center">
          <ConfidenceBadge level={b.confidence}/>
          <StaleWarningBadge lastVerified={b.last_verified} />
        </div>
      ),
    },
    {
      key: "source",
      header: "Source",
      render: (b) => (
        <span className="text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Globe size={10}/> {b.source} {b.year}
          </span>
        </span>
      ),
    },
    { key: "status", header: "Status", render: (b) => <StatusBadge status={b.status}/> },
    { key: "usage_count", header: "Usage", render: (b) => <span className="text-foreground">{b.usage_count || 0} formulas</span> },
    {
      key: "actions",
      header: "",
      className: "w-24",
      render: (b) => (
        <AdminIconButtonGroup>
          <AdminIconButton icon={Eye} label="View benchmark" />
          <AdminIconButton icon={Edit3} label="Edit benchmark" />
          <AdminIconButton
            icon={Trash2}
            label="Delete benchmark"
            variant="destructive"
            onClick={() => setDeleteTarget(b)}
          />
        </AdminIconButtonGroup>
      ),
    },
  ];

  return (
    <AdminShell
      title="Benchmark Policies"
      subtitle="Define and manage industry benchmarks used in formula evaluation and business case generation."
      fullWidth
      actions={
        <Btn variant="primary">
          <Plus size={13} className="mr-1"/> Add Benchmark
        </Btn>
      }
    >
      <AdminStatsRow columns={4}>
        <AdminStatCard
          label="Total Benchmarks"
          value={stats.total}
          icon={<BarChart3 size={14}/>}
        />
        <AdminStatCard
          label="High Confidence"
          value={stats.highConfidence}
          icon={<CheckCircle2 size={14}/>}
          color="success"
        />
        <AdminStatCard
          label="Active"
          value={stats.active}
          icon={<TrendingUp size={14}/>}
          color="primary"
        />
        <AdminStatCard
          label="Total Usage"
          value={stats.totalUsage}
          icon={<Database size={14}/>}
          color="primary"
        />
      </AdminStatsRow>

      <AdminFilterBar
        searchPlaceholder="Search benchmarks..."
        searchValue={search}
        onSearchChange={setSearch}
        filters={
          <>
            <Select value={confidenceFilter} onValueChange={(value) => setConfidenceFilter(value === "all" ? "all" : value as ConfidenceLevel)}>
              <SelectTrigger className="w-40 vf-text-caption">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Confidence</SelectItem>
                <SelectItem value="High">High</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Select value={industryFilter} onValueChange={setIndustryFilter}>
              <SelectTrigger className="w-40 vf-text-caption">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Industries</SelectItem>
                {industries.map(ind => (
                  <SelectItem key={ind} value={ind}>{ind}</SelectItem>
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

      <AdminDataTable
        data={filteredBenchmarks}
        columns={benchmarkColumns}
        keyExtractor={(b) => b.id}
        isLoading={benchmarksLoading}
        error={benchmarksError}
        onRetry={() => refetchBenchmarks()}
        emptyTitle="No benchmarks match your filters"
        emptyDescription="Try adjusting your search or filter criteria."
        emptyIcon={BarChart3}
      />

      <AdminConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Benchmark"
        description="This benchmark will be permanently deleted. Any formulas using it may fail to evaluate."
        itemName={deleteTarget?.name}
        tenantName="Current tenant"
        actionLabel="Delete Benchmark"
        variant="destructive"
        onConfirm={() => {
          setDeleteTarget(null);
        }}
      />
    </AdminShell>
  );
}

export default function BenchmarkPolicies() {
  return (
    <ErrorBoundary>
      <BenchmarkPoliciesContent />
    </ErrorBoundary>
  );
}
