/**
 * Screen — Value Packs
 * Design: Refined Enterprise SaaS — production layout
 * Spec: Value Packs as first-class product objects — reusable domain-specific
 * packages combining ontology, value drivers, formulas, benchmarks, and workflows.
 *
 * Layout: 2-column grid (main + 280px sidebar).
 *   Main:    Filter bar → 3-col pack grid → My Packs row
 *   Sidebar: Preview panel → Pack actions
 */
import { useState, useMemo, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { EmptyState, ErrorState } from "@/components/states";
import {
  Skeleton,
  ErrorBoundary,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  PageShell,
} from "@/components";
import { Input } from "@/components/ui/input";
import { VirtualList } from "@/components/ui/virtual-list";
import { SectionCard } from "@/components/blocks/SectionCard";
import {
  useValuePacks,
  useValuePack,
  useApplyValuePack,
  useValuePackFrameworkList,
  useValuePackOntologyMap,
  useValuePackTemplates,
  useValuePackComparison,
  useSuggestValuePacks,
  type ValuePack,
  type PackStatus,
  type ValuePackFrameworkData,
  type ValuePackSuggestion,
} from "@/hooks";
import {
  Package, Search, Filter, AlertCircle, RefreshCw, Loader2,
  Upload, Eye, GitCompare, Map, BookOpen, Lightbulb, Layers,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, Btn } from "@/components/ui/fabric";

// ── Constants ────────────────────────────────────────────────────────────────

/** Layout constants for consistent sizing */
const LAYOUT = {
  MAX_WIDTH: "1280px",
  SIDEBAR_WIDTH: "280px",
  PACK_GRID_COLS: 3,
  MY_PACKS_SLOTS: 4,
} as const;

/** Industry filter options - synchronized with pack-manifest.json */
const INDUSTRIES = [
  "All",
  "AI & Technology",
  "Energy & Utilities",
  "Financial Services",
  "Life Sciences",
  "Manufacturing",
  "Retail & Consumer",
  "Software",
];
const STATUSES: Array<"all" | PackStatus> = ["all", "active", "draft", "published", "archived"];
const STATUS_LABELS: Record<string, string> = {
  all: "All Statuses", active: "Active", draft: "Draft", published: "Published", archived: "Archived",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format a date string into a human-readable relative time.
 * Handles edge cases: undefined input, invalid dates, and future dates.
 *
 * @param dateStr - ISO date string or undefined
 * @returns Human-readable string (e.g., "Today", "3 days ago", "Jan 15, 2024")
 */
function formatLastUpdated(dateStr: string | undefined): string {
  if (!dateStr) return "Unknown";

  const date = new Date(dateStr);
  // Handle invalid date strings
  if (isNaN(date.getTime())) return "Invalid date";

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  // Handle future dates (shouldn't happen but guard against clock skew)
  if (diffMs < 0) return date.toLocaleDateString();

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

// ── Pack Card (simplified) ─────────────────────────────────────

interface PackCardProps {
  pack: ValuePack;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
}

function PackCard({ pack, isSelected, onSelect }: PackCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(pack.pack_id)}
      className={`text-left bg-card border rounded-lg shadow-sm hover:shadow-md transition-all cursor-pointer group w-full ${
        isSelected
          ? "border-primary ring-2 ring-primary/10"
          : "border-border hover:border-border/80"
      }`}
    >
      {/* Title + description */}
      <div className="px-4 pt-4 pb-3">
        <h3 className="vf-text-body-m font-bold text-foreground leading-tight mb-1.5 truncate">
          {pack.name}
        </h3>
        <div className="space-y-1">
          <p className="vf-text-caption text-muted-foreground/60 leading-relaxed line-clamp-2">
            {pack.description || "No description available"}
          </p>
        </div>
      </div>

      {/* Tags: industry + version */}
      <div className="px-4 pb-3 flex items-center gap-2">
        <span className="vf-text-micro font-medium text-muted-foreground bg-muted border border-border px-2 py-0.5 rounded">
          {pack.industry}
        </span>
        {pack.version && (
          <span className="vf-text-micro font-medium text-muted-foreground bg-muted/20 border border-border px-2 py-0.5 rounded">
            v{pack.version}
          </span>
        )}
      </div>
    </button>
  );
}

function PackCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-lg shadow-sm">
      <div className="px-4 pt-4 pb-3 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
      <div className="px-4 pb-3 flex items-center gap-2">
        <Skeleton className="h-5 w-16 rounded" />
        <Skeleton className="h-5 w-10 rounded" />
      </div>
    </div>
  );
}

// ── Preview Panel ────────────────────────────────────────────────────────────

function PreviewPanel({ packId }: { packId: string | null }) {
  const { data: pack, isLoading } = useValuePack(packId);

  if (isLoading) return <PreviewPanelSkeleton />;

  if (!pack) {
    return (
      <div className="border border-border rounded-lg bg-card p-4" data-testid="preview-panel">
        <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3">Preview Panel</h4>
        <div className="space-y-2.5">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-3 bg-muted/30 rounded w-full" />
          ))}
        </div>
        <p className="vf-text-caption text-muted-foreground/60 mt-4 text-center">Select a pack to preview</p>
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg bg-card p-4" data-testid="preview-panel">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3">Preview Panel</h4>
      <h3 className="vf-text-body-l font-bold text-foreground mb-1">{pack.name}</h3>
      <p className="vf-text-caption text-muted-foreground mb-3 leading-relaxed">
        {pack.description || "No description available"}
      </p>
      <div className="space-y-2 vf-text-caption">
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Industry</span>
          <span className="font-medium text-muted-foreground">{pack.industry}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Status</span>
          <span className="font-medium text-muted-foreground capitalize">{pack.status}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Version</span>
          <span className="font-medium text-muted-foreground">{pack.version || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Drivers</span>
          <span className="font-medium text-muted-foreground">{pack.driver_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Formulas</span>
          <span className="font-medium text-muted-foreground">{pack.formula_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Benchmarks</span>
          <span className="font-medium text-muted-foreground">{pack.benchmark_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground/60">Updated</span>
          <span className="font-medium text-muted-foreground">{formatLastUpdated(pack.updated_at)}</span>
        </div>
      </div>
    </div>
  );
}

function PreviewPanelSkeleton() {
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <Skeleton className="h-3 w-24 mb-3" />
      <Skeleton className="h-5 w-3/4 mb-1" />
      <Skeleton className="h-3 w-full mb-3" />
      <div className="space-y-2">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex justify-between">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-12" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Pack Actions ─────────────────────────────────────────────────────────────

interface PackActionsProps {
  selectedPackId: string | null;
  onDeploy: (packId: string) => void;
  isDeploying: boolean;
  error?: string | null;
  onClearError?: () => void;
}

function PackActions({ selectedPackId, onDeploy, isDeploying, error, onClearError }: PackActionsProps) {
  return (
    <div className="border border-border rounded-lg bg-card p-4" data-testid="pack-actions">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3">Pack Actions</h4>

      {error && (
        <div className="mb-3 p-2 bg-destructive/10 border border-destructive/20 rounded vf-text-caption text-destructive flex items-start gap-1.5">
          <AlertCircle size={12} className="shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          {onClearError && (
            <button onClick={onClearError} className="text-destructive/70 hover:text-destructive shrink-0">×</button>
          )}
        </div>
      )}

      <Btn
        variant="primary"
        className="w-full mb-2"
        onClick={() => selectedPackId && onDeploy(selectedPackId)}
        disabled={!selectedPackId || isDeploying}
      >
        {isDeploying ? (
          <><Loader2 size={12} className="animate-spin" /> Deploying...</>
        ) : (
          "Deploy to Account"
        )}
      </Btn>
      <Btn
        variant="ghost"
        className="w-full"
        disabled={!selectedPackId}
      >
        <Eye size={12} /> View Details
      </Btn>
    </div>
  );
}

// ── My Packs Section ─────────────────────────────────────────────────────────

interface MyPacksSectionProps {
  /** All available packs - tenant-scoped packs will be displayed */
  packs: ValuePack[];
}

/**
 * Displays tenant-scoped packs ("My Packs") in a grid.
 * Shows up to LAYOUT.MY_PACKS_SLOTS packs with empty slot placeholders.
 */
function MyPacksSection({ packs }: MyPacksSectionProps) {
  const myPacks = useMemo(
    () => packs.filter(p => p.scope === "tenant").slice(0, LAYOUT.MY_PACKS_SLOTS),
    [packs]
  );

  const emptySlotCount = Math.max(0, LAYOUT.MY_PACKS_SLOTS - myPacks.length);

  return (
    <div data-testid="my-packs-section">
      <SectionCard title="My Packs" noPad>
        {/* grid-cols-4 matches LAYOUT.MY_PACKS_SLOTS - using static class for Tailwind build-time detection */}
        <div className="grid grid-cols-4 gap-3 p-4">
          {myPacks.length === 0 && (
            <p className="col-span-4 vf-text-caption text-muted-foreground/60 text-center py-4">No deployed packs yet.</p>
          )}
          {myPacks.map((pack) => (
            <div
              key={pack.pack_id}
              className="bg-card border border-border rounded-lg px-3 py-3"
              title={pack.name}
            >
              <h5 className="vf-text-body-s font-bold text-foreground truncate mb-1">
                {pack.name}
              </h5>
              <p className="vf-text-micro text-muted-foreground/60 truncate">{pack.industry}</p>
              <div className="h-2 w-3/4 mt-2 bg-muted/30 rounded" />
            </div>
          ))}
          {/* Fill remaining slots with empty placeholders */}
          {emptySlotCount > 0 && Array.from({ length: emptySlotCount }).map((_, i) => (
            <div key={`empty-${i}`} className="bg-muted/20 border border-dashed border-border rounded-lg px-3 py-3">
              <p className="vf-text-caption text-muted-foreground/40 text-center py-2">Empty slot</p>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

function MyPacksSkeleton() {
  return (
    <div>
      <Skeleton className="h-3 w-28 mb-3" />
      <div className="grid grid-cols-4 gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-card border border-border rounded-lg px-3 py-3 space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-2 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}


// ── Framework Browser Panel ──────────────────────────────────────────────────
function FrameworkBrowserPanel() {
  const [search, setSearch] = useState("");
  const { data: frameworks, isLoading } = useValuePackFrameworkList(undefined, search || undefined);
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3 flex items-center gap-1.5">
        <Layers size={12} /> Framework Library
      </h4>
      <Input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Search frameworks…"
        className="w-full vf-text-caption mb-3"
      />
      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-8 w-full" />)}</div>
      ) : frameworks && frameworks.length > 0 ? (
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
          {frameworks.map((fw: ValuePackFrameworkData) => (
            <div key={fw.industry_id} className="flex items-center justify-between p-2 bg-muted/10 rounded-md hover:bg-muted/20 cursor-pointer">
              <div>
                <div className="vf-text-caption font-semibold text-foreground">{fw.display_name}</div>
                <div className="vf-text-micro text-muted-foreground">Tier {fw.tier} · {fw.primary_value_drivers?.length ?? 0} drivers</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="vf-text-caption text-muted-foreground/60 text-center py-3">No frameworks found.</p>
      )}
    </div>
  );
}

// ── Ontology Map Panel ───────────────────────────────────────────────────────
function OntologyMapPanel() {
  const { data: ontologyMap, isLoading } = useValuePackOntologyMap();
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3 flex items-center gap-1.5">
        <Map size={12} /> Ontology Map
      </h4>
      {isLoading ? (
        <div className="space-y-2">{[1,2].map(i => <Skeleton key={i} className="h-6 w-full" />)}</div>
      ) : ontologyMap ? (
        <div className="space-y-2 vf-text-caption">
          {ontologyMap.shared_drivers.map((mapping) => (
            <div key={mapping.id} className="flex items-center justify-between p-1.5 bg-muted/10 rounded">
              <span className="text-muted-foreground">{mapping.name || mapping.id}</span>
              <span className="vf-text-micro text-muted-foreground/60">→</span>
              <span className="font-medium text-foreground">{mapping.industries.join(", ")}</span>
              <span className="vf-text-micro text-success">{mapping.count} industries</span>
            </div>
          )) ?? <p className="text-muted-foreground/60 text-center py-2">No mappings available.</p>}
        </div>
      ) : (
        <p className="vf-text-caption text-muted-foreground/60 text-center py-3">Load ontology map to view mappings.</p>
      )}
    </div>
  );
}

// ── Template Library Panel ───────────────────────────────────────────────────
function TemplateLibraryPanel() {
  const { data: templates, isLoading } = useValuePackTemplates();
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3 flex items-center gap-1.5">
        <BookOpen size={12} /> Template Library
      </h4>
      {isLoading ? (
        <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-8 w-full" />)}</div>
      ) : templates && templates.templates?.length > 0 ? (
        <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
          {templates.templates.map((template) => (
            <div key={template.template_id} className="p-2 bg-muted/10 rounded-md hover:bg-muted/20 cursor-pointer">
              <div className="vf-text-caption font-semibold text-foreground">{template.template_name}</div>
              {template.formula_pattern && <div className="vf-text-micro text-muted-foreground mt-0.5 line-clamp-1">{template.formula_pattern}</div>}
              <div className="vf-text-micro text-muted-foreground/60 mt-0.5">{template.applicable_industries[0] || "General"}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="vf-text-caption text-muted-foreground/60 text-center py-3">No templates available.</p>
      )}
    </div>
  );
}

// ── Comparison Tool ──────────────────────────────────────────────────────────
function ComparisonPanel({ packs }: { packs: ValuePack[] }) {
  const [packA, setPackA] = useState<string>("");
  const [packB, setPackB] = useState<string>("");
  const comparison = useValuePackComparison();
  const handleCompare = () => {
    if (packA && packB) {
      comparison.mutate({ industry_ids: [packA, packB] });
    }
  };
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3 flex items-center gap-1.5">
        <GitCompare size={12} /> Compare Packs
      </h4>
      <div className="space-y-2 mb-3">
        <Select value={packA} onValueChange={v => setPackA(v)}>
          <SelectTrigger className="w-full vf-text-caption"><SelectValue placeholder="Select Pack A" /></SelectTrigger>
          <SelectContent>
            {packs.map(p => <SelectItem key={p.pack_id} value={p.pack_id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={packB} onValueChange={v => setPackB(v)}>
          <SelectTrigger className="w-full vf-text-caption"><SelectValue placeholder="Select Pack B" /></SelectTrigger>
          <SelectContent>
            {packs.map(p => <SelectItem key={p.pack_id} value={p.pack_id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <Btn variant="outline" className="w-full" disabled={!packA || !packB || comparison.isPending}
        onClick={handleCompare}>
        {comparison.isPending ? <Loader2 size={12} className="animate-spin" /> : <GitCompare size={12} />}
        Compare
      </Btn>
      {comparison.data && (
        <div className="mt-3 space-y-1.5 vf-text-caption">
          {Object.entries(comparison.data.differentiation_analysis || {}).map(([key, val]: [string, string], i: number) => (
            <div key={i} className="flex items-center justify-between p-1.5 bg-muted/10 rounded vf-text-micro">
              <span className="font-medium text-muted-foreground">{key}</span>
              <span className="text-foreground">{val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Suggestion Engine ────────────────────────────────────────────────────────
function SuggestionPanel() {
  const [industry, setIndustry] = useState("");
  const [dealSize, setDealSize] = useState("");
  const suggestions = useSuggestValuePacks();
  const [suggestionResults, setSuggestionResults] = useState<ValuePackSuggestion[]>([]);
  const handleSuggest = () => {
    if (industry) {
      setSuggestionResults(suggestions.suggest({
        industry,
        annual_revenue: dealSize || undefined,
      }) );
    }
  };
  return (
    <div className="border border-border rounded-lg bg-card p-4">
      <h4 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground/60 mb-3 flex items-center gap-1.5">
        <Lightbulb size={12} /> Pack Suggestions
      </h4>
      <div className="space-y-2 mb-3">
        <Input value={industry} onChange={e => setIndustry(e.target.value)}
          placeholder="Industry (e.g., SaaS)"
          className="w-full vf-text-caption" />
        <Input value={dealSize} onChange={e => setDealSize(e.target.value)}
          placeholder="Deal size (optional)"
          className="w-full vf-text-caption" />
      </div>
      <Btn variant="outline" className="w-full" disabled={!industry || false}
        onClick={handleSuggest}>
        {false ? <Loader2 size={12} className="animate-spin" /> : <Lightbulb size={12} />}
        Get Suggestions
      </Btn>
      {suggestionResults && suggestionResults.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {suggestionResults.map((s) => (
            <div key={s.industry_id} className="p-2 bg-success/10 border border-success/20 rounded-md">
              <div className="flex justify-between items-center">
                <span className="vf-text-caption font-semibold text-foreground">{s.display_name}</span>
                <span className="vf-text-micro font-bold text-success">{Math.round(s.match_score * 100)}%</span>
              </div>
              <div className="vf-text-micro text-muted-foreground mt-0.5">{s.recommended_drivers?.[0]?.relevance || "Matched"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Content ─────────────────────────────────────────────────────────────

function ValuePacksContent() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL search params
  const [industry, setIndustry] = useState(searchParams.get('industry') || "All");
  const [status, setStatus] = useState<"all" | PackStatus>((searchParams.get('status') as "all" | PackStatus) || "all");
  const [category, setCategory] = useState(searchParams.get('category') || "All");
  const [search, setSearch] = useState(searchParams.get('search') || "");
  const [selectedPackId, setSelectedPackId] = useState<string | null>(searchParams.get('pack') || null);
  const [deployError, setDeployError] = useState<string | null>(null);

  // Sync filter state to URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (industry && industry !== "All") params.set('industry', industry);
    if (status && status !== "all") params.set('status', status);
    if (category && category !== "All") params.set('category', category);
    if (search) params.set('search', search);
    if (selectedPackId) params.set('pack', selectedPackId);
    setSearchParams(params, { replace: true });
  }, [industry, status, category, search, selectedPackId, setSearchParams]);

  // Memoize filter config to prevent unnecessary query re-fetches
  const filters = useMemo(() => ({
    industry: industry === "All" ? "all" as const : industry,
    status: status === "all" ? "all" as const : status,
    category: category === "All" ? "all" as const : category,
    search: search || undefined,
  }), [industry, status, category, search]);

  const { data: packs = [], isLoading, error, refetch } = useValuePacks(filters);
  const applyMutation = useApplyValuePack();

  // Derive unique categories from data
  const categories = useMemo(() => {
    const cats = Array.from(new Set(packs.map(p => p.category).filter(Boolean))) as string[];
    return ["All", ...cats];
  }, [packs]);

  // Client-side filtering for search + industry + status + category
  const filtered = useMemo(() => {
    const searchLower = search.toLowerCase();
    return packs.filter(p =>
      (industry === "All" || p.industry === industry) &&
      (status === "all" || p.status === status) &&
      (category === "All" || p.category === category) &&
      (search === "" ||
       p.name.toLowerCase().includes(searchLower) ||
       p.description?.toLowerCase().includes(searchLower))
    );
  }, [packs, industry, status, category, search]);

  const handleDeploy = useCallback(async (packId: string) => {
    setDeployError(null);
    try {
      await applyMutation.mutateAsync({ packId });
      toast.success("Pack deployed successfully");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to deploy pack";
      setDeployError(message);
      toast.error(message);
      // Error already logged by mutation's onError; UI handles display
    }
  }, [applyMutation]);

  const handleSelectPack = useCallback((packId: string) => {
    setSelectedPackId(prev => (prev === packId ? null : packId));
  }, []);

  return (
    <PageShell>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Value Packs"
          subtitle="Browse and deploy value pack content"
        />
        <div className="flex items-center gap-2 shrink-0">
          <Btn variant="ghost">
            <Filter size={13} className="mr-1" /> Filter
          </Btn>
          <Btn variant="primary">
            <Upload size={13} className="mr-1" /> Import Pack
          </Btn>
        </div>
      </div>

      {/* Two-column grid: main + sidebar */}
      <div className="grid gap-5 grid-cols-[1fr_280px]">
        {/* ── Left column: filter bar + pack grid + my packs ── */}
        <div className="min-w-0">
          {/* Filter Bar */}
          <div className="bg-card border border-border rounded-lg px-4 py-3 mb-5">
            <div className="flex items-center gap-3 flex-wrap">
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="h-8 vf-text-caption min-w-[120px]">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(c => (
                    <SelectItem key={c} value={c} className="vf-text-caption">{c === "All" ? "All Categories" : c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={industry} onValueChange={setIndustry}>
                <SelectTrigger className="h-8 vf-text-caption min-w-[140px]">
                  <SelectValue placeholder="Industry" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map(ind => (
                    <SelectItem key={ind} value={ind} className="vf-text-caption">{ind === "All" ? "All Industries" : ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={status} onValueChange={v => setStatus(v as "all" | PackStatus)}>
                <SelectTrigger className="h-8 vf-text-caption min-w-[120px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  {STATUSES.map(s => (
                    <SelectItem key={s} value={s} className="vf-text-caption">{STATUS_LABELS[s]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <div className="relative flex items-center gap-2 flex-1 min-w-[160px]">
                <Search size={12} className="text-muted-foreground/60 shrink-0 absolute left-3 top-1/2 -translate-y-1/2" />
                <Input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search packs…"
                  className="flex-1 vf-text-caption pl-8"
                />
              </div>
            </div>
          </div>

          {/* Error state */}
          {error && (
            <ErrorState
              title="Failed to load value packs"
              description={error instanceof Error ? error.message : "An unexpected error occurred"}
              error={error}
              onRetry={refetch}
              retryLabel="Try again"
            />
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="grid grid-cols-3 gap-4 mb-6" data-testid="packs-loading">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <PackCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Pack Grid */}
          {!isLoading && !error && (
            <>
              <SectionCard title="Pack Grid" className="mb-6" noPad>
                {filtered.length > 0 ? (
                  <div className="h-[500px] p-4">
                    <VirtualList
                      items={filtered}
                      estimateSize={180}
                      columns={3}
                      overscan={2}
                      renderItem={(pack) => (
                        <PackCard
                          pack={pack}
                          isSelected={selectedPackId === pack.pack_id}
                          onSelect={handleSelectPack}
                        />
                      )}
                    />
                  </div>
                ) : (
                  <div className="p-4">
                    <EmptyState
                      icon={Package}
                      title="No value packs match your filters"
                      description="Try adjusting your search or filter criteria"
                    />
                  </div>
                )}
              </SectionCard>

              {/* My Packs Section */}
              <MyPacksSection packs={packs} />
            </>
          )}

          {isLoading && <MyPacksSkeleton />}
        </div>

        {/* ── Right column: preview panel + pack actions ── */}
        <div className="space-y-4">
          <PreviewPanel packId={selectedPackId} />
          <PackActions
            selectedPackId={selectedPackId}
            onDeploy={handleDeploy}
            isDeploying={applyMutation.isPending}
            error={deployError}
            onClearError={() => setDeployError(null)}
          />
          <ComparisonPanel packs={packs} />
          <FrameworkBrowserPanel />
          <TemplateLibraryPanel />
          <OntologyMapPanel />
          <SuggestionPanel />
        </div>
      </div>
    </PageShell>
  );
}

/**
 * Value Packs page component - Entry point with error boundary.
 *
 * Displays domain-specific value packs that users can browse, filter, and deploy.
 * Features: industry/category filtering, search, pack preview, deployment to tenant.
 *
 * @example
 * // In router configuration
 * { path: '/value-packs', element: <ValuePacks /> }
 */
export default function ValuePacks() {
  return (
    <ErrorBoundary>
      <ValuePacksContent />
    </ErrorBoundary>
  );
}
