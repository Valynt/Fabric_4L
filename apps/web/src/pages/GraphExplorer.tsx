/**
 * Screen 7 — Knowledge Graph Explorer
 * Refactored: ~180 lines (was 589)
 */
import { useState, useCallback } from "react";
import { Loader2, AlertCircle, RefreshCw, Move } from "lucide-react";
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyMedia } from "@/components/ui/empty";
import { PageShell } from "@/components/layout/PageShell";
import { GraphVisualization } from "@/components/graph/GraphVisualization";
import { GraphInspectorPanel } from "@/components/graph/GraphInspectorPanel";
import { GraphExplorerControls } from "@/features/graph/components/GraphExplorerControls";
import { GraphExplorerLayout } from "@/features/graph/components/GraphExplorerLayout";
import { useSubgraph, useEntityContext, useEntityTraversal, useGraphQuery } from "@/hooks/useGraphQuery";
import type { GraphNode, GraphEdge } from "@/features/graph/domain/graph.model";
import { useGraphCanvas } from "@/hooks/useGraphCanvas";
import { useGraphData } from "@/hooks/useGraphData";
import { getEntityBadgeClasses } from "@/lib/graph-utils";
import { cn } from "@/lib/utils";
import { PageHeader as WfPageHeader } from "@/components/ui/fabric";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";

// Constants for graph configuration
const GRAPH_NODE_LIMIT = 100;
const SEARCH_MAX_RESULTS = 20;
const DEFAULT_DEPTH = 2;
const CANVAS_MIN_HEIGHT = 500;
const HEADER_OFFSET_PX = 280;

export default function GraphExplorer() {
  const [selected, setSelected] = useState<string | null>(null);
  const [queryText, setQueryText] = useState("");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<{ entities: GraphNode[]; relationships: GraphEdge[] } | null>(null);

  const { data: subgraph, isLoading: subgraphLoading, error: subgraphError, refetch: refetchSubgraph } = useSubgraph({
    query: '',
    depth: DEFAULT_DEPTH,
    limit: GRAPH_NODE_LIMIT,
  });

  const { data: entityContext, isLoading: contextLoading } = useEntityContext(selected, 2);
  const entityTraversal = useEntityTraversal();
  const graphQuery = useGraphQuery();
  const canvas = useGraphCanvas();

  const { data: graphData, isEmpty, nodeTypeCounts } = useGraphData({
    subgraph: subgraph,
    entityContext: entityContext,
    searchResults: searchResults,
  });

  const isLoading = subgraphLoading || contextLoading || graphQuery.isPending;
  const error = subgraphError?.message || graphQuery.error?.message || searchError;

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelected(prev => nodeId === prev ? null : nodeId);
  }, []);

  const handleSearch = useCallback(async () => {
    if (!queryText.trim()) {
      setSearchResults(null);
      return;
    }
    setSearchError(null);
    try {
      const results = await graphQuery.mutateAsync({
        query: queryText,
        max_hops: DEFAULT_DEPTH,
        max_results: SEARCH_MAX_RESULTS,
      });
      setSearchResults({
        entities: results.entities,
        relationships: results.relationships,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Search failed';
      setSearchError(message);
    }
  }, [queryText, graphQuery]);



  const selectedNodeData = graphData.nodes.find(n => n.id === selected) || null;

  const handleReset = () => {
    setSelected(null);
    setSearchResults(null);
    setQueryText("");
    canvas.actions.resetView();
    refetchSubgraph();
  };

  return (
    <PageShell>
      <WfPageHeader
        breadcrumbs={[{ label: "Knowledge Graph" }, { label: "Graph Explorer" }]}
        title="Graph Explorer"
        subtitle="Visualize and navigate the knowledge graph"
      />

      {/* 3-Panel Layout: Control | Canvas | Inspector */}
      <GraphExplorerLayout
        controls={
          <GraphExplorerControls
            queryText={queryText}
            onQueryChange={setQueryText}
            onSearch={handleSearch}
            onZoomIn={canvas.actions.zoomIn}
            onZoomOut={canvas.actions.zoomOut}
            onResetView={canvas.actions.resetView}
            scale={canvas.view.scale}
            isSearching={graphQuery.isPending}
          />
        }
        canvas={
          <>
            {isLoading && (
              <div className="flex flex-col items-center justify-center min-h-[380px] gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Loading knowledge graph...</span>
              </div>
            )}

            {error && !isLoading && (
              <div className="flex items-center justify-center min-h-[380px]">
                <Empty className="border-0">
                  <EmptyMedia variant="icon">
                    <AlertCircle className="text-destructive" />
                  </EmptyMedia>
                  <EmptyHeader>
                    <EmptyTitle className="text-destructive">Error loading graph</EmptyTitle>
                    <EmptyDescription>{error}</EmptyDescription>
                  </EmptyHeader>
                  <Btn variant="outline" onClick={() => refetchSubgraph()} className="text-xs">
                    <RefreshCw className="w-3 h-3 mr-1" /> Retry
                  </Btn>
                </Empty>
              </div>
            )}

            {isEmpty && !isLoading && !error && (
              <div className="flex items-center justify-center min-h-[380px]">
                <Empty className="border-0">
                  <EmptyHeader>
                    <EmptyTitle>No matching entities found</EmptyTitle>
                    <EmptyDescription>
                      Try adjusting your search query or filters to see more results
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              </div>
            )}

            {/* Pan/Drag hint overlay */}
            {!isLoading && !error && !isEmpty && (
              <div className="absolute top-3 left-3 z-10 flex items-center gap-2 bg-card/90 backdrop-blur-sm px-3 py-1.5 rounded-md border border-border shadow-sm">
                <Move className="w-3 h-3 text-muted-foreground" />
                <span className="vf-text-caption text-muted-foreground">Drag to pan</span>
              </div>
            )}

            {/* Truncation indicator */}
            {!isLoading && !error && !isEmpty && graphData.nodes.length >= GRAPH_NODE_LIMIT && (
              <div className="absolute bottom-3 left-3 z-10 flex items-center gap-1.5 bg-warning/10 backdrop-blur-sm px-3 py-1.5 rounded-md border border-warning/20 shadow-sm">
                <AlertCircle className="w-3 h-3 text-warning" />
                <span className="vf-text-caption text-warning-foreground">
                  Showing {GRAPH_NODE_LIMIT} nodes. Refine search to see more.
                </span>
              </div>
            )}

            {!isLoading && !error && !isEmpty && (
              <div {...canvas.handlers} className="w-full h-full">
                <GraphVisualization
                  nodes={graphData.nodes}
                  edges={graphData.edges}
                  selectedNodeId={selected}
                  onNodeClick={handleNodeClick}
                  viewTransform={canvas.view}
                  isDragging={canvas.isDragging}
                  className="w-full h-full"
                />
              </div>
            )}
          </>
        }
        inspector={
          <>
            <GraphInspectorPanel
              node={selectedNodeData}
              onFocus={(id) => setSelected(id)}
              onReset={handleReset}
              className="h-[calc(100%-140px)]"
            />

            {/* Stats */}
            <SectionCard title="Graph Statistics" className="h-[130px]">
              <div className="space-y-1.5">
                <div className="flex justify-between vf-text-body-s">
                  <span className="text-muted-foreground">Nodes</span>
                  <span className="font-bold text-foreground">{graphData.stats.totalNodes.toLocaleString()}</span>
                </div>
                <div className="flex justify-between vf-text-body-s">
                  <span className="text-muted-foreground">Edges</span>
                  <span className="font-bold text-foreground">{graphData.stats.totalEdges.toLocaleString()}</span>
                </div>
                <div className="flex justify-between vf-text-body-s">
                  <span className="text-muted-foreground">Density</span>
                  <span className="font-bold text-foreground">{graphData.stats.density.toFixed(2)}</span>
                </div>
                <div className="border-t border-border/50 pt-1.5 mt-1 space-y-1">
                  {Object.entries(nodeTypeCounts).slice(0, 3).map(([nodeType, count]) => {
                    const classes = getEntityBadgeClasses(nodeType);
                    return (
                      <div key={nodeType} className="flex items-center gap-2 vf-text-caption">
                        <div className={cn("w-2 h-2 rounded-full shrink-0", classes.dot)}/>
                        <span className="text-muted-foreground flex-1 truncate">{nodeType}</span>
                        <span className="font-semibold text-foreground">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </SectionCard>
          </>
        }
      />
    </PageShell>
  );
}
