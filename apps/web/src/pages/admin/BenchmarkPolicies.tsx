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
  BarChart3, Plus, Search, Edit3, Trash2, Eye,
  Globe, Database, CheckCircle2, AlertTriangle, TrendingUp,
  Download, Info, AlertCircle, RefreshCw,
} from "lucide-react";
import { Skeleton, ErrorBoundary } from "@/components";
import { cn } from "@/lib/utils";
import {
  useBenchmarks,
  type Benchmark,
  type ConfidenceLevel,
  type BenchmarkStatus,
} from "@/hooks";
import { formatDate } from "@/lib/formatters";
import { PageShell } from "@/components";
import { ErrorState, EmptyState } from "@/components/states";
import { Input } from "@/components/ui/input";
import { PageHeader, Btn } from "@/components/ui/fabric";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

function BenchmarkPoliciesSkeleton() {
  return (
    <PageShell>
      <div className="flex items-start justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>

      {/* Stats Row Skeleton */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-card border border-border rounded-xl px-4 py-3">
            <Skeleton className="h-4 w-28 mb-2" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
      </div>

      {/* Table Skeleton */}
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


function BenchmarkPoliciesContent() {
  const [search, setSearch] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState<"all" | ConfidenceLevel>("all");
  const [industryFilter, setIndustryFilter] = useState<"all" | string>("all");

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

  const isLoading = benchmarksLoading;
  const error = benchmarksError;

  if (isLoading) {
    return (
      <PageShell>
        <BenchmarkPoliciesSkeleton />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell>
        <ErrorState
          title="Failed to load benchmark policies"
          description="An error occurred while loading benchmark data."
          error={error}
          onRetry={() => refetchBenchmarks()}
        />
      </PageShell>
    );
  }

  return (
    <PageShell>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Benchmark Policies"
          subtitle="Define and manage industry benchmarks used in formula evaluation and business case generation."
        />
        <Btn variant="primary"><Plus size={13} className="mr-1"/> Add Benchmark</Btn>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Benchmarks", value: stats.total, icon: <BarChart3 size={14}/> },
          { label: "High Confidence", value: stats.highConfidence, icon: <CheckCircle2 size={14}/>, color: "text-success" },
          { label: "Active", value: stats.active, icon: <TrendingUp size={14}/>, color: "text-primary" },
          { label: "Total Usage", value: stats.totalUsage, icon: <Database size={14}/>, color: "text-primary" },
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
              <Search size={12} className="text-muted-foreground shrink-0"/>
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search benchmarks..."
                className="flex-1 border-0 shadow-none focus-visible:ring-0 bg-transparent"
              />
            </div>
            <Select value={confidenceFilter} onValueChange={(value) => setConfidenceFilter(value === "all" ? "all" : value as ConfidenceLevel)}>
              <SelectTrigger className="w-full vf-text-caption">
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
            <div className="ml-auto flex items-center gap-2">
              <button className="flex items-center gap-1.5 px-3 py-1.5 vf-text-caption font-medium text-muted-foreground hover:bg-muted rounded-lg transition-colors">
                <Download size={12}/> Export
              </button>
            </div>
          </div>

          {/* Benchmark Table */}
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <table className="w-full vf-text-body-s">
              <thead>
                <tr className="border-b border-border bg-muted">
                  {["Benchmark", "Industry", "Value Range", "Confidence", "Source", "Status", "Usage", ""].map(h => (
                    <th key={h} className="text-left px-4 py-3 vf-text-micro uppercase tracking-wider text-muted-foreground font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredBenchmarks.map(b => (
                  <tr key={b.id} className="hover:bg-muted transition-colors group">
                    <td className="px-4 py-3">
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
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {b.industry}
                      {b.vertical && <span className="text-muted-foreground"> / {b.vertical}</span>}
                    </td>
                    <td className="px-4 py-3 font-mono vf-text-caption text-foreground">{b.value_range}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center">
                        <ConfidenceBadge level={b.confidence}/>
                        <StaleWarningBadge lastVerified={b.last_verified} />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Globe size={10}/>
                        {b.source} {b.year}
                      </div>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={b.status}/></td>
                    <td className="px-4 py-3 text-foreground">{b.usage_count || 0} formulas</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="View">
                          <Eye size={13}/>
                        </button>
                        <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="Edit">
                          <Edit3 size={13}/>
                        </button>
                        <button className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive" title="Delete">
                          <Trash2 size={13}/>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredBenchmarks.length === 0 && (
              <EmptyState
                icon={BarChart3}
                title="No benchmarks match your filters"
                description="Try adjusting your search or filter criteria."
              />
            )}
      </div>
    </PageShell>
  );
}

export default function BenchmarkPolicies() {
  return (
    <ErrorBoundary>
      <BenchmarkPoliciesContent />
    </ErrorBoundary>
  );
}
