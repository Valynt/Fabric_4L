/**
 * MyModels — Personal and Shared Value Models
 *
 * Features:
 * - Folder sidebar for quick filtering (All, My Models, Shared, Favorites)
 * - Search, sort, and industry filter bar
 * - 3-column responsive card grid with view toggle (grid/list)
 * - Create new model dialog
 * - Loading skeletons and empty states
 *
 * Route: /library/models
 * Integrates with: useModels, useModelFolders, useCreateModel
 */

import { useState, useMemo, useCallback } from "react";
import { useNavigation } from "@/hooks/useNavigation";
import {
  Plus, Search, SortAsc, Filter, LayoutGrid, List,
  Folder, FolderOpen, Users, Star, Clock, Loader2,
  MoreHorizontal, Trash2, Share2, GitBranch, FlaskConical,
  Boxes, AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useModels,
  useModelFolders,
  useCreateModel,
  type ValueModel,
  type ModelFilters,
  type ModelFolder,
} from "@/hooks/useModels";
import { PageHeader, Btn } from "@/components/ui/fabric";

// ── Constants ────────────────────────────────────────────────────────────────

const SORT_OPTIONS = [
  { value: "updatedAt", label: "Last Updated" },
  { value: "name", label: "Name" },
  { value: "createdAt", label: "Date Created" },
] as const;

const INDUSTRY_OPTIONS = [
  "All Industries",
  "SaaS / B2B",
  "Financial Services",
  "Energy / Utilities",
  "Life Sciences",
];

const FOLDER_ICONS: Record<string, React.ReactNode> = {
  all: <Folder size={14} />,
  "my-models": <FolderOpen size={14} />,
  shared: <Users size={14} />,
  favorites: <Star size={14} />,
};

const STATUS_STYLES: Record<string, string> = {
  active: "bg-success/10 text-success border-success/20",
  draft: "bg-warning/10 text-warning border-warning/20",
  archived: "bg-muted text-muted-foreground border-border",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString();
}

// ── Sub-components ───────────────────────────────────────────────────────────

function FolderSidebar({
  folders,
  activeFolder,
  onSelect,
  isLoading,
}: {
  folders: ModelFolder[];
  activeFolder: string;
  onSelect: (id: string) => void;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="w-[200px] shrink-0 space-y-2 p-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-full rounded-md" />
        ))}
      </div>
    );
  }

  return (
    <nav className="w-[200px] shrink-0 border-r border-border bg-muted/30 rounded-l-lg p-3 space-y-0.5">
      <div className="vf-text-micro font-bold uppercase tracking-wider text-muted-foreground px-2 pb-2">
        Folders
      </div>
      {folders.map((folder) => (
        <button
          key={folder.id}
          onClick={() => onSelect(folder.id)}
          className={cn(
            "flex items-center gap-2 w-full px-2 py-1.5 rounded-md vf-text-body-s font-medium transition-colors text-left",
            activeFolder === folder.id
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="shrink-0">{FOLDER_ICONS[folder.id] || <Folder size={14} />}</span>
          <span className="truncate flex-1">{folder.name}</span>
          <span className="vf-text-micro text-muted-foreground tabular-nums">{folder.count}</span>
        </button>
      ))}
    </nav>
  );
}

function ModelCard({
  model,
  onClick,
}: {
  model: ValueModel;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-card border border-border rounded-lg p-4 text-left hover:border-primary/30 hover:shadow-sm transition-all group w-full"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-[13px] font-bold text-foreground leading-snug line-clamp-1 group-hover:text-primary transition-colors">
          {model.name}
        </h3>
        <span
          className={cn(
            "inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold border shrink-0",
            STATUS_STYLES[model.status] || STATUS_STYLES.draft
          )}
        >
          {model.status.charAt(0).toUpperCase() + model.status.slice(1)}
        </span>
      </div>

      <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2 mb-3">
        {model.description}
      </p>

      <div className="flex items-center gap-3 text-[10px] text-muted-foreground mb-3">
        <span className="flex items-center gap-1">
          <GitBranch size={10} />
          {model.driverCount} drivers
        </span>
        <span className="flex items-center gap-1">
          <FlaskConical size={10} />
          {model.formulaCount} formulas
        </span>
        <span className="flex items-center gap-1">
          <Boxes size={10} />
          {model.entityCount} entities
        </span>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 flex-wrap">
          {model.tags.slice(0, 3).map((tag) => (
            <Badge
              key={tag}
              variant="secondary"
              className="text-[9px] px-1.5 py-0 h-4"
            >
              {tag}
            </Badge>
          ))}
        </div>
        <span className="vf-text-micro text-muted-foreground flex items-center gap-1">
          <Clock size={10} />
          {formatRelativeDate(model.updatedAt)}
        </span>
      </div>

      {model.isShared && (
        <div className="flex items-center gap-1 mt-2 vf-text-micro text-muted-foreground">
          <Share2 size={10} />
          <span>Shared by {model.owner}</span>
        </div>
      )}
    </button>
  );
}

function ModelListRow({
  model,
  onClick,
}: {
  model: ValueModel;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-4 w-full px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors text-left last:border-0"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[12px] font-bold text-foreground truncate">{model.name}</span>
          <span
            className={cn(
              "inline-flex items-center px-1.5 py-0 rounded text-[9px] font-semibold border shrink-0",
              STATUS_STYLES[model.status] || STATUS_STYLES.draft
            )}
          >
            {model.status}
          </span>
          {model.isShared && (
            <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
              <Share2 size={10} /> {model.owner}
            </span>
          )}
        </div>
        <p className="text-[11px] text-muted-foreground truncate">{model.description}</p>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        {model.tags.slice(0, 2).map((tag) => (
          <Badge key={tag} variant="secondary" className="text-[9px] px-1.5 py-0 h-4">
            {tag}
          </Badge>
        ))}
      </div>

      <div className="flex items-center gap-4 text-[10px] text-muted-foreground shrink-0 w-[180px] justify-end">
        <span>{model.formulaCount} formulas</span>
        <span>{model.entityCount} entities</span>
        <span>{formatRelativeDate(model.updatedAt)}</span>
      </div>
    </button>
  );
}

function GridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-card border border-border rounded-lg p-4 space-y-3">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-4 w-12 rounded-full" />
            <Skeleton className="h-4 w-14 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({
  folder,
  search,
  onCreateClick,
}: {
  folder: string;
  search: string;
  onCreateClick?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
        <AlertCircle size={20} className="text-muted-foreground" />
      </div>
      <h3 className="text-[14px] font-bold text-foreground mb-1">
        {search ? "No models match your search" : "No models yet"}
      </h3>
      <p className="text-[12px] text-muted-foreground max-w-[300px] mb-4">
        {search
          ? `Try adjusting your search term or clearing filters.`
          : folder === "shared"
            ? "Models shared with you will appear here."
            : folder === "favorites"
              ? "Star models to add them to your favorites."
              : "Create your first value model to get started."}
      </p>
      {!search && folder !== "shared" && folder !== "favorites" && onCreateClick && (
        <Btn variant="primary" onClick={onCreateClick}>
          <Plus size={14} />
          Create First Model
        </Btn>
      )}
    </div>
  );
}

function NewModelDialog({
  open,
  onClose,
  onCreate,
  isCreating,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; description: string; industry: string }) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [industry, setIndustry] = useState("SaaS / B2B");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!name.trim()) return;
      onCreate({ name: name.trim(), description: description.trim(), industry });
    },
    [name, description, industry, onCreate]
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-xl shadow-xl w-full max-w-md p-6 mx-4">
        <h2 className="text-[16px] font-extrabold text-foreground mb-1">New Value Model</h2>
        <p className="text-[11px] text-muted-foreground mb-5">
          Create a new model to organize value drivers, formulas, and entities.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[11px] font-bold text-foreground mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. SaaS Revenue Optimization"
              className="w-full px-3 py-2 text-[12px] border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-foreground mb-1">Industry</label>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full px-3 py-2 text-[12px] border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            >
              {INDUSTRY_OPTIONS.filter((i) => i !== "All Industries").map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-bold text-foreground mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this value model..."
              rows={3}
              className="w-full px-3 py-2 text-[12px] border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-[12px] font-medium text-muted-foreground hover:text-foreground transition-colors rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 text-[12px] font-bold text-white bg-primary rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {isCreating && <Loader2 size={12} className="animate-spin" />}
              Create Model
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function MyModels() {
  // State
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFolder, setActiveFolder] = useState("all");
  const [sortBy, setSortBy] = useState<"updatedAt" | "name" | "createdAt">("updatedAt");
  const [industryFilter, setIndustryFilter] = useState("All Industries");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [showNewDialog, setShowNewDialog] = useState(false);

  // Filters
  const filters: ModelFilters = useMemo(
    () => ({
      search: searchQuery || undefined,
      folder: activeFolder !== "all" ? activeFolder : undefined,
      industry: industryFilter !== "All Industries" ? industryFilter : undefined,
      sortBy,
      sortDir: "desc" as const,
    }),
    [searchQuery, activeFolder, sortBy, industryFilter]
  );

  // Data
  const { data: models, isLoading, isError } = useModels(filters);
  const { data: folders, isLoading: foldersLoading } = useModelFolders();
  const createModel = useCreateModel();

  // Handlers
  const handleCreate = useCallback(
    (data: { name: string; description: string; industry: string }) => {
      createModel.mutate(data, {
        onSuccess: () => setShowNewDialog(false),
      });
    },
    [createModel]
  );

  const handleModelClick = useCallback((model: ValueModel) => {
    // Navigate to model detail page
    const { navigateTo } = useNavigation();
    navigateTo('model-detail', { modelId: model.id });
  }, []);

  return (
    <div className="h-full flex flex-col p-6">
      <PageHeader
        title="My Models"
        subtitle="Personal and shared value models"
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center border border-border rounded-md overflow-hidden">
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "p-1.5 transition-colors",
                  viewMode === "grid"
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
                title="Grid view"
              >
                <LayoutGrid size={14} />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={cn(
                  "p-1.5 transition-colors",
                  viewMode === "list"
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
                title="List view"
              >
                <List size={14} />
              </button>
            </div>
            <Btn variant="primary" onClick={() => setShowNewDialog(true)}>
              <Plus size={14} />
              New Model
            </Btn>
          </div>
        }
      />

      <div className="flex-1 flex bg-card border border-border rounded-lg overflow-hidden">
        {/* Folder sidebar */}
        <FolderSidebar
          folders={folders || []}
          activeFolder={activeFolder}
          onSelect={setActiveFolder}
          isLoading={foldersLoading}
        />

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Search + Filter bar */}
          <div className="flex items-center gap-2 p-3 border-b border-border bg-muted/20">
            <div className="relative flex-1 max-w-[300px]">
              <Search
                size={14}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search models..."
                className="w-full pl-8 pr-3 py-1.5 text-[12px] border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>

            <div className="flex items-center gap-1.5">
              <SortAsc size={12} className="text-muted-foreground" />
              <select
                value={sortBy}
                onChange={(e) =>
                  setSortBy(e.target.value as "updatedAt" | "name" | "createdAt")
                }
                className="px-2 py-1.5 text-[11px] border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <Filter size={12} className="text-muted-foreground" />
              <select
                value={industryFilter}
                onChange={(e) => setIndustryFilter(e.target.value)}
                className="px-2 py-1.5 text-[11px] border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                {INDUSTRY_OPTIONS.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind}
                  </option>
                ))}
              </select>
            </div>

            {(searchQuery || industryFilter !== "All Industries") && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setIndustryFilter("All Industries");
                }}
                className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {/* Content area */}
          <div className="flex-1 overflow-y-auto p-4">
            {isLoading ? (
              <GridSkeleton />
            ) : isError ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <AlertCircle size={20} className="text-destructive mb-2" />
                <p className="text-[12px] text-destructive">Failed to load models</p>
              </div>
            ) : !models || models.length === 0 ? (
              <EmptyState
                folder={activeFolder}
                search={searchQuery}
                onCreateClick={() => setShowNewDialog(true)}
              />
            ) : viewMode === "grid" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {models.map((model) => (
                  <ModelCard
                    key={model.id}
                    model={model}
                    onClick={() => handleModelClick(model)}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-card border border-border rounded-lg overflow-hidden">
                {models.map((model) => (
                  <ModelListRow
                    key={model.id}
                    model={model}
                    onClick={() => handleModelClick(model)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* New Model Dialog */}
      <NewModelDialog
        open={showNewDialog}
        onClose={() => setShowNewDialog(false)}
        onCreate={handleCreate}
        isCreating={createModel.isPending}
      />
    </div>
  );
}
