import { safeAsync } from '@/lib/async';
/**
 * Screen 5 — Value Trees: Tree Explorer
 * Design: Refined Enterprise SaaS
 * 
 * Features:
 * - Fetch value trees from Layer 3 API using entity_id
 * - Visual tree view with collapsible nodes
 * - Outline/compact view alternative
 * - Entity selector to choose root entity
 * - Loading, error, and empty states
 */
import { useState, useMemo, useRef, type ChangeEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { 
  ChevronDown, 
  ChevronRight, 
  Plus, 
  Upload, 
  Download, 
  Loader2, 
  AlertCircle,
  RefreshCw,
  Search,
  TreeDeciduous
} from "lucide-react";
import type { EntityType } from "@/lib/entity-colors";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { useValueTree, useValueTreeCache, useValueTreePaths, useCreateValueTree, useImportValueTree } from "@/hooks/useValueTrees";
import { useEntities, type Entity } from "@/hooks/useEntities";
import type { ValueTreeNode, ValueTreeEdge, ValueTreeResponse } from "@/api/valueTrees";
import { ValueTreeResponseSchema } from "@/lib/schemas";
import { Tabs } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { EntityBadge } from "@/lib/entity-colors";

// Types for UI tree rendering
interface TreeNode {
  id: string;
  label: string;
  type: EntityType;
  children?: TreeNode[];
}

// Map backend entity types to UI EntityType
type BackendEntityType = 'Capability' | 'UseCase' | 'Persona' | 'ValueDriver' | string;

function mapEntityType(type: BackendEntityType): EntityType {
  const mapping: Record<string, EntityType> = {
    'Capability': 'capability',
    'UseCase': 'usecase',
    'Persona': 'persona',
    'ValueDriver': 'valuedriver',
  };
  return mapping[type] || 'capability';
}

// Constants for UI truncation
const ENTITY_ID_SHORT_LENGTH = 12;
const ENTITY_ID_LIST_LENGTH = 16;
const DEPTH_OPTIONS = [1, 2, 3, 4] as const;
const DIRECTION_OPTIONS = ["upward", "downward"] as const;

// Build hierarchical tree from flat nodes/edges
function buildTree(nodes: ValueTreeNode[], edges: ValueTreeEdge[], rootId: string): TreeNode | null {
  if (!nodes.length) return null;

  // Create node map for quick lookup
  const nodeMap = new Map<string, ValueTreeNode>();
  nodes.forEach(node => nodeMap.set(node.id, node));

  // Build adjacency list (parent -> children)
  const childrenMap = new Map<string, string[]>();
  edges.forEach(edge => {
    const list = childrenMap.get(edge.source) || [];
    list.push(edge.target);
    childrenMap.set(edge.source, list);
  });

  // Recursive tree builder
  function buildNode(nodeId: string): TreeNode | null {
    const node = nodeMap.get(nodeId);
    if (!node) return null;

    const childIds = childrenMap.get(nodeId) || [];
    const children = childIds
      .map(childId => buildNode(childId))
      .filter((child): child is TreeNode => child !== null);

    return {
      id: node.id,
      label: node.label,
      type: mapEntityType(node.type),
      children: children.length > 0 ? children : undefined,
    };
  }

  return buildNode(rootId);
}

const TYPE_COLORS: Record<EntityType, string> = {
  valuedriver: "bg-emerald-50 border-emerald-200 text-emerald-900",
  persona:     "bg-amber-50  border-amber-200  text-amber-900",
  usecase:     "bg-cyan-50   border-cyan-200   text-cyan-900",
  capability:  "bg-violet-50 border-violet-200 text-violet-900",
};

function TreeNodeView({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="flex flex-col items-center">
      <div
        className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg border text-[11px] font-semibold cursor-pointer select-none min-w-[120px] max-w-[140px] text-center ${TYPE_COLORS[node.type]}`}
        onClick={() => setOpen(o => !o)}
      >
        <EntityBadge type={node.type}/>
        <span className="leading-tight">{node.label}</span>
        {hasChildren && (
          <span className="text-[9px] opacity-50">{open ? "▲" : "▼"}</span>
        )}
      </div>
      {hasChildren && open && (
        <div className="flex flex-col items-center">
          <div className="w-px h-4 bg-neutral-300"/>
          <div className="flex gap-4 items-start">
            {(node.children || []).map((child) => (
              <div key={child.id} className="flex flex-col items-center">
                <div className="w-px h-4 bg-neutral-300"/>
                <TreeNodeView node={child} depth={depth + 1}/>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function OutlineNode({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      <div
        className="flex items-center gap-1.5 py-1 text-[12px] hover:bg-muted/30 rounded px-1 cursor-pointer"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => setOpen(o => !o)}
      >
        {hasChildren ? (
          open ? <ChevronDown size={11} className="text-muted-foreground/60"/> : <ChevronRight size={11} className="text-muted-foreground/60"/>
        ) : (
          <span className="w-[11px] text-neutral-300 text-[10px]">─</span>
        )}
        <EntityBadge type={node.type}/>
        <span className="text-muted-foreground">{node.label}</span>
      </div>
      {hasChildren && open && (node.children || []).map((child) => (
        <OutlineNode key={child.id} node={child} depth={depth + 1}/>
      ))}
    </div>
  );
}

function ValueTreeSkeleton({ view }: { view: "visual" | "outline" }) {
  if (view === "visual") {
    return (
      <div className="bg-card border border-border rounded-lg p-8 overflow-x-auto shadow-sm">
        <div className="flex justify-center min-w-[700px]">
          {/* Skeleton tree structure */}
          <div className="flex flex-col items-center gap-4">
            <Skeleton className="h-16 w-32 rounded-lg" />
            <div className="w-px h-8 bg-neutral-200" />
            <div className="flex gap-8">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex flex-col items-center gap-4">
                  <div className="w-px h-8 bg-neutral-200" />
                  <Skeleton className="h-14 w-28 rounded-lg" />
                  <div className="w-px h-6 bg-neutral-200" />
                  <div className="flex gap-4">
                    <Skeleton className="h-10 w-24 rounded-lg" />
                    <Skeleton className="h-10 w-24 rounded-lg" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4 shadow-sm">
      <div className="space-y-2">
        {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
          <Skeleton key={i} className="h-6" style={{ marginLeft: `${Math.min(i, 3) * 16}px` }} />
        ))}
      </div>
    </div>
  );
}

export default function ValueTreeExplorer() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("Tree Explorer");
  const [view, setView] = useState<"visual"|"outline"|"paths">("visual");
  const [showEntitySelector, setShowEntitySelector] = useState(false);
  const importFileRef = useRef<HTMLInputElement | null>(null);
  const { invalidateTree } = useValueTreeCache();
  const createTreeMutation = useCreateValueTree();
  const importTreeMutation = useImportValueTree();

  // URL-driven query controls for shareable links
  const entityId = searchParams.get("entityId");
  const rawDirection = searchParams.get("direction");
  const direction = DIRECTION_OPTIONS.includes(rawDirection as "upward" | "downward")
    ? (rawDirection as "upward" | "downward")
    : "upward";

  const rawDepth = Number(searchParams.get("depth"));
  const depth = Number.isFinite(rawDepth)
    ? Math.max(1, Math.min(4, rawDepth))
    : 4;

  const updateQueryParams = (next: {
    entityId?: string | null;
    direction?: "upward" | "downward";
    depth?: number;
  }) => {
    const params = new URLSearchParams(searchParams.toString());

    const resolvedEntityId = next.entityId !== undefined ? next.entityId : entityId;
    const resolvedDirection = next.direction ?? direction;
    const resolvedDepth = next.depth ?? depth;

    if (resolvedEntityId) {
      params.set("entityId", resolvedEntityId);
    } else {
      params.delete("entityId");
    }
    params.set("direction", resolvedDirection);
    params.set("depth", String(Math.max(1, Math.min(4, resolvedDepth))));
    setSearchParams(params.toString());
  };
  
  // Fetch value tree data
  const { 
    data: treeData, 
    isLoading: treeLoading, 
    error: treeError,
    refetch: refetchTree 
  } = useValueTree(entityId, { 
    direction, 
    maxDepth: depth
  });
  const {
    data: pathData,
    isLoading: pathsLoading,
    error: pathsError,
    refetch: refetchPaths,
  } = useValueTreePaths(entityId, {
    direction,
    maxDepth: depth,
    enabled: view === "paths",
  });

  // Fetch available entities for selection - returns EntityListResponse with results array
  const { data: entitiesResponse, isLoading: entitiesLoading } = useEntities();
  const entities = entitiesResponse?.results ?? [];

  // Build hierarchical tree for rendering
  const tree = useMemo(() => {
    if (!treeData) return null;
    return buildTree(treeData.nodes, treeData.edges, treeData.root_entity_id);
  }, [treeData]);

  // Stats for display
  const stats = useMemo(() => {
    if (!treeData) return null;
    return {
      totalNodes: treeData.stats.total_nodes,
      totalEdges: treeData.stats.total_edges,
      maxDepth: treeData.stats.max_depth,
      byLayer: treeData.stats.by_layer,
    };
  }, [treeData]);

  // Handle entity selection
  const handleSelectEntity = (id: string) => {
    updateQueryParams({ entityId: id });
    setShowEntitySelector(false);
  };

  const handleCreateTree = async () => {
    if (!entityId) {
      toast.error("Select a root entity before creating a tree.");
      return;
    }
    try {
      const createdTree = await createTreeMutation.mutateAsync({
        entity_id: entityId,
        direction,
        initialize_root: true,
      });
      invalidateTree(entityId);
      updateQueryParams({ entityId: createdTree.root_entity_id });
      toast.success("Value tree created.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create value tree.");
    }
  };

  const handleImportClick = () => {
    if (!entityId) {
      toast.error("Select a root entity before importing.");
      return;
    }
    importFileRef.current?.click();
  };

  const handleImportFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !entityId) return;
    try {
      const raw = await file.text();
      const json = JSON.parse(raw);
      const parsedTree = ValueTreeResponseSchema.parse(json) as ValueTreeResponse;
      if (parsedTree.root_entity_id !== entityId) {
        toast.error("Tenant/entity mismatch: selected root does not match imported tree root.");
        return;
      }
      const importedTree = await importTreeMutation.mutateAsync({
        entity_id: entityId,
        tree: parsedTree,
      });
      invalidateTree(entityId);
      updateQueryParams({ entityId: importedTree.root_entity_id });
      toast.success("Value tree imported successfully.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Invalid import file.");
    }
  };

  // Filter entities that could be tree roots (ValueDrivers or Capabilities)
  const rootCandidates = useMemo(() => {
    return entities.filter((entity: Entity) => 
      entity.type === 'ValueDriver' || entity.type === 'Capability' || entity.type === 'UseCase'
    );
  }, [entities]);

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        breadcrumbs={[{ label: "Value Trees" }, { label: "Tree Explorer" }]}
        title="Tree Explorer"
        subtitle={entityId 
          ? `Visualizing value hierarchy from entity: ${entityId.slice(0, ENTITY_ID_SHORT_LENGTH)}...`
          : "Select an entity to visualize its value hierarchy."
        }
        actions={
          <>
            <div className="relative">
              <Btn 
                variant="ghost" 
                onClick={() => setShowEntitySelector(!showEntitySelector)}
                className={showEntitySelector ? "bg-muted/30" : ""}
              >
                {entityId ? "Change Root Entity ▾" : "Select Tree ▾"}
              </Btn>
              {showEntitySelector && (
                <div className="absolute top-full right-0 mt-1 w-80 bg-card border border-border rounded-lg shadow-lg z-50">
                  <div className="p-3 border-b border-border/50">
                    <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                      <Search size={12} />
                      <span>Select root entity</span>
                    </div>
                  </div>
                  <div className="max-h-64 overflow-y-auto p-2 space-y-1">
                    {entitiesLoading ? (
                      <div className="p-4 text-center text-muted-foreground text-[12px]">
                        <Loader2 size={14} className="animate-spin inline mr-2" />
                        Loading entities...
                      </div>
                    ) : rootCandidates.length === 0 ? (
                      <div className="p-4 text-center text-muted-foreground text-[12px]">
                        No entities available. 
                        <a href="/discover/knowledge/entities" className="text-blue-600 hover:underline ml-1">
                          Browse entities
                        </a>
                      </div>
                    ) : (
                      rootCandidates.map((entity: Entity) => (
                        <button
                          key={entity.id}
                          onClick={() => handleSelectEntity(entity.id)}
                          className={`w-full text-left px-3 py-2 rounded-lg text-[12px] transition-colors ${
                            entityId === entity.id 
                              ? "bg-blue-50 text-blue-700" 
                              : "hover:bg-muted/20 text-muted-foreground"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <EntityBadge type={mapEntityType(entity.type)} />
                            <span className="font-medium truncate">{entity.name}</span>
                          </div>
                          <div className="text-[10px] text-muted-foreground/60 mt-1">
                            {entity.id.slice(0, ENTITY_ID_LIST_LENGTH)}...
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
            <Btn
              variant="primary"
              disabled={!entityId || createTreeMutation.isPending || importTreeMutation.isPending}
              onClick={() => safeAsync(handleCreateTree(), "valueTree.create")}
            >
              {createTreeMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12}/>} New Tree
            </Btn>
            <Btn
              variant="ghost"
              disabled={!entityId || importTreeMutation.isPending || createTreeMutation.isPending}
              onClick={handleImportClick}
            >
              {importTreeMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12}/>} Import
            </Btn>
            <input ref={importFileRef} type="file" accept="application/json" className="hidden" onChange={(e) => safeAsync(handleImportFile(e), "valueTree.import")} />
            <Btn 
              variant="ghost" 
              onClick={() => {
                // Export as JSON
                if (treeData) {
                  const blob = new Blob([JSON.stringify(treeData, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `value-tree-${entityId}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }
              }}
              disabled={!treeData}
            >
              <Download size={12}/> Export
            </Btn>
          </>
        }
      />

      <Tabs
        tabs={["Tree Explorer", "Normalization", "Formulas"]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* Stats bar */}
      {stats && (
        <div className="flex gap-4 mb-4">
          <SectionCard className="flex-1 py-3">
            <div className="flex items-center gap-4 text-[12px]">
              <div>
                <span className="text-muted-foreground/60 uppercase tracking-wider text-[10px]">Nodes</span>
                <p className="font-bold text-foreground text-[18px]">{stats.totalNodes}</p>
              </div>
              <div className="w-px h-8 bg-neutral-200" />
              <div>
                <span className="text-muted-foreground/60 uppercase tracking-wider text-[10px]">Edges</span>
                <p className="font-bold text-foreground text-[18px]">{stats.totalEdges}</p>
              </div>
              <div className="w-px h-8 bg-neutral-200" />
              <div>
                <span className="text-muted-foreground/60 uppercase tracking-wider text-[10px]">Max Depth</span>
                <p className="font-bold text-foreground text-[18px]">{stats.maxDepth}</p>
              </div>
              <div className="ml-auto flex gap-2">
                {Object.entries(stats.byLayer).map(([layer, count]) => (
                  <div key={layer} className="text-center px-2 py-1 bg-muted/20 rounded">
                    <span className="text-[10px] text-muted-foreground/60">L{layer}</span>
                    <p className="font-semibold text-muted-foreground">{count}</p>
                  </div>
                ))}
              </div>
            </div>
          </SectionCard>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <Btn variant={view === "visual" ? "primary" : "ghost"} onClick={() => setView("visual")}>Visual</Btn>
        <Btn variant={view === "outline" ? "primary" : "ghost"} onClick={() => setView("outline")}>Outline</Btn>
        <Btn variant={view === "paths" ? "primary" : "ghost"} onClick={() => setView("paths")}>Paths</Btn>
        <div className="ml-2 flex items-center gap-1">
          {DIRECTION_OPTIONS.map((option) => (
            <Btn
              key={option}
              variant={direction === option ? "outline" : "ghost"}
              onClick={() => updateQueryParams({ direction: option })}
              className="capitalize"
            >
              {option}
            </Btn>
          ))}
        </div>
        <div className="flex items-center gap-1">
          {DEPTH_OPTIONS.map((option) => (
            <Btn
              key={option}
              variant={depth === option ? "outline" : "ghost"}
              onClick={() => updateQueryParams({ depth: option })}
            >
              D{option}
            </Btn>
          ))}
        </div>
        {tree && (
          <Btn
            variant="ghost"
            className="ml-auto text-[11px]"
            onClick={() => {
              safeAsync(refetchTree(), "valueTree.refetchTree");
              if (view === "paths") {
                safeAsync(refetchPaths(), "valueTree.refetchPaths");
              }
            }}
          >
            <RefreshCw size={12} className="mr-1" /> Refresh
          </Btn>
        )}
      </div>

      {/* Loading State */}
      {treeLoading && <ValueTreeSkeleton view={view === "paths" ? "outline" : view} />}

      {/* Error State */}
      {!treeLoading && treeError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-3" />
          <h3 className="text-[14px] font-semibold text-red-800 mb-1">Failed to load value tree</h3>
          <p className="text-[12px] text-red-600 mb-4">
            {treeError instanceof Error ? treeError.message : 'An unexpected error occurred'}
          </p>
          <div className="flex justify-center gap-2">
            <Btn variant="outline" onClick={() => refetchTree()}>
              <RefreshCw size={12} className="mr-1" /> Retry
            </Btn>
          </div>
        </div>
      )}

      {/* Empty State - No entity selected */}
      {!entityId && !treeLoading && !treeError && (
        <div className="bg-muted/20 border border-border rounded-lg p-12 text-center">
          <TreeDeciduous className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-[14px] font-semibold text-muted-foreground mb-2">No Entity Selected</h3>
          <p className="text-[12px] text-muted-foreground mb-4 max-w-md mx-auto">
            Select a root entity (Value Driver, Persona, or Capability) to visualize its value hierarchy.
          </p>
          <Btn variant="primary" onClick={() => setShowEntitySelector(true)}>
            <Search size={12} className="mr-1" /> Select Entity
          </Btn>
        </div>
      )}

      {/* Empty State - No tree data */}
      {entityId && !treeLoading && !treeError && !tree && (
        <div className="bg-muted/20 border border-border rounded-lg p-12 text-center">
          <TreeDeciduous className="w-12 h-12 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-[14px] font-semibold text-muted-foreground mb-2">No Value Tree Found</h3>
          <p className="text-[12px] text-muted-foreground mb-4 max-w-md mx-auto">
            This entity doesn&apos;t have any connected value relationships. Try selecting a different entity or create relationships in the knowledge graph.
          </p>
          <Btn variant="outline" onClick={() => setShowEntitySelector(true)}>
            Select Different Entity
          </Btn>
        </div>
      )}

      {/* Success State - Tree/Path Display */}
      {!treeLoading && !treeError && tree && (
        view === "visual" ? (
          <div className="bg-card border border-border rounded-lg p-8 overflow-x-auto shadow-sm">
            <div className="flex justify-center min-w-[700px]">
              <TreeNodeView node={tree}/>
            </div>
          </div>
        ) : view === "outline" ? (
          <div className="bg-card border border-border rounded-lg p-4 shadow-sm">
            <OutlineNode node={tree}/>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-lg p-4 shadow-sm">
            {pathsLoading && (
              <div className="text-[12px] text-muted-foreground p-2">
                <Loader2 size={14} className="animate-spin inline mr-2" />
                Loading paths...
              </div>
            )}
            {!pathsLoading && pathsError && (
              <div className="text-[12px] text-red-600 p-2">
                Failed to load path exploration data: {pathsError.message}
              </div>
            )}
            {!pathsLoading && !pathsError && (pathData?.length ?? 0) === 0 && (
              <div className="text-[12px] text-muted-foreground p-2">
                No paths found for this entity and direction.
              </div>
            )}
            {!pathsLoading && !pathsError && (pathData?.length ?? 0) > 0 && (
              <div className="space-y-2">
                {(pathData ?? []).map((path, pathIndex) => (
                  <div
                    key={`${pathIndex}-${path.length}`}
                    className="border border-border/60 rounded-md p-2 text-[12px]"
                  >
                    <div className="text-[10px] text-muted-foreground mb-1">
                      Path {pathIndex + 1} · length {path.length}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {path.nodes.map((node, nodeIndex) => (
                        <div key={`${node.id}-${nodeIndex}`} className="inline-flex items-center gap-1.5">
                          <EntityBadge type={mapEntityType(node.type)} />
                          <span className="text-foreground/90">{node.name}</span>
                          {nodeIndex < path.nodes.length - 1 && (
                            <ChevronRight size={11} className="text-muted-foreground/70" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}
