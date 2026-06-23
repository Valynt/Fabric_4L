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
  CheckCircle2, Clock, Archive,
  ListChecks, FlaskConical, BarChart3,
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
  useValuePacks,
  type ValuePack,
  type PackStatus,
} from "@/hooks/useValuePacks";
import { Btn } from "@/components/ui/fabric";
import {
  AdminShell,
  AdminStatCard,
  AdminStatsRow,
  AdminFilterBar,
  AdminDataTable,
  AdminIconButton,
  AdminIconButtonGroup,
  type AdminDataTableColumn,
} from "@/components/admin";

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

// ── Main Component ─────────────────────────────────────────────────────────────

const STATUS_CHIPS = [
  { value: "all", label: "All" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "archived", label: "Archived" },
];

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

  const packColumns: AdminDataTableColumn<ValuePack>[] = [
    {
      key: "name",
      header: "Pack",
      render: (p) => (
        <div className="flex items-center gap-2">
          <FolderKanban size={14} className="text-primary shrink-0" />
          <div>
            <span className="font-medium text-foreground block">{p.name}</span>
            {p.description && (
              <span className="vf-text-micro text-muted-foreground line-clamp-1">{p.description}</span>
            )}
          </div>
        </div>
      ),
    },
    { key: "industry", header: "Industry", render: (p) => <span className="text-muted-foreground">{p.industry}</span> },
    { key: "status", header: "Status", render: (p) => <PackStatusChip status={p.status} /> },
    {
      key: "driver_count",
      header: "Drivers",
      render: (p) => (
        <span className="flex items-center gap-1 text-foreground">
          <ListChecks size={11} /> {p.driver_count || 0}
        </span>
      ),
    },
    {
      key: "formula_count",
      header: "Formulas",
      render: (p) => (
        <span className="flex items-center gap-1 text-foreground">
          <FlaskConical size={11} /> {p.formula_count || 0}
        </span>
      ),
    },
    {
      key: "benchmark_count",
      header: "Benchmarks",
      render: (p) => (
        <span className="flex items-center gap-1 text-foreground">
          <BarChart3 size={11} /> {p.benchmark_count || 0}
        </span>
      ),
    },
    {
      key: "version",
      header: "Version",
      render: (p) => <span className="font-mono vf-text-caption text-muted-foreground">{p.version || "—"}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      render: (p) => <span className="text-muted-foreground">{formatDate(p.updated_at)}</span>,
    },
    {
      key: "actions",
      header: "",
      className: "w-24",
      render: () => (
        <AdminIconButtonGroup>
          <AdminIconButton icon={Eye} label="View pack" />
          <AdminIconButton icon={Edit3} label="Edit pack" />
          <AdminIconButton icon={GitBranch} label="Fork pack" variant="primary" />
        </AdminIconButtonGroup>
      ),
    },
  ];

  return (
    <AdminShell
      title="Pack Management"
      subtitle="Create, manage, and publish value packs across industries and segments."
      fullWidth
      actions={
        <Btn variant="primary">
          <Plus size={13} className="mr-1" /> New Pack
        </Btn>
      }
    >
      <AdminStatsRow columns={4}>
        <AdminStatCard
          label="Total Packs"
          value={stats.total}
          icon={<FolderKanban size={14} />}
        />
        <AdminStatCard
          label="Published"
          value={stats.published}
          icon={<CheckCircle2 size={14} />}
          color="success"
        />
        <AdminStatCard
          label="Drafts"
          value={stats.draft}
          icon={<Clock size={14} />}
          color="warning"
        />
        <AdminStatCard
          label="Total Drivers"
          value={stats.totalDrivers}
          icon={<ListChecks size={14} />}
          color="primary"
        />
      </AdminStatsRow>

      <AdminFilterBar
        searchPlaceholder="Search packs..."
        searchValue={search}
        onSearchChange={setSearch}
        chips={STATUS_CHIPS}
        chipValue={statusFilter}
        onChipChange={(value) => setStatusFilter(value as "all" | PackStatus)}
        filters={
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
        }
      />

      <AdminDataTable
        data={filteredPacks}
        columns={packColumns}
        keyExtractor={(p) => p.id}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        emptyTitle="No packs match your filters"
        emptyDescription="Try adjusting your search or filter criteria."
        emptyIcon={FolderKanban}
      />
    </AdminShell>
  );
}

export default function PackManagement() {
  return (
    <ErrorBoundary>
      <PackManagementContent />
    </ErrorBoundary>
  );
}
