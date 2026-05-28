/**
 * GraphVisualization Component
 * Renders an interactive SVG graph with nodes, edges, zoom, and pan support.
 */

import React, { useMemo, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  VIEWBOX_WIDTH,
  VIEWBOX_HEIGHT,
  wrapTextIntoLines,
  getEntityHexColors,
  getNodeRadius,
} from "@/lib/graph-utils";
import type { GraphNode, GraphEdge } from "@/features/graph/domain/graph.model";

export interface GraphVisualizationProps {
  /** Nodes to render (must include x/y from layout) */
  nodes: Array<GraphNode & { x: number; y: number; r: number }>;
  /** Edges/relationships to render */
  edges: GraphEdge[];
  /** Currently selected node ID */
  selectedNodeId: string | null;
  /** Called when a node is clicked */
  onNodeClick: (nodeId: string) => void;
  /** Called when mouse enters/leaves a node (for hover state) */
  onNodeHover?: (nodeId: string | null) => void;
  /** View transform for zoom and pan */
  viewTransform: { x: number; y: number; scale: number };
  /** Whether user is currently dragging */
  isDragging: boolean;
  /** Additional CSS classes */
  className?: string;
}

const MAX_LABEL_LINE_LENGTH = 12;

/** Get node coordinates (all nodes in props have x/y) */
function getNodePosition(
  node: GraphNode & { x: number; y: number }
): { x: number; y: number } {
  return { x: node.x, y: node.y };
}

/**
 * Graph visualization component using SVG.
 *
 * Features:
 * - Interactive node selection
 * - Zoom and pan via viewTransform
 * - Dynamic layout positioning
 * - Color-coded nodes by entity type
 * - Multi-line text labels
 */
export function GraphVisualization({
  nodes,
  edges,
  selectedNodeId,
  onNodeClick,
  onNodeHover,
  viewTransform,
  isDragging,
  className,
}: GraphVisualizationProps) {
  const canvasRef = useRef<HTMLDivElement>(null);

  // Build a map for quick node lookup
  const nodeMap = useMemo(() => {
    return new Map(nodes.map((n) => [n.id, n]));
  }, [nodes]);

  // Calculate SVG transform string
  const transform = `translate(${viewTransform.x}, ${viewTransform.y}) scale(${viewTransform.scale})`;

  return (
    <div
      ref={canvasRef}
      className={cn(
        "relative rounded-lg border bg-card overflow-hidden",
        isDragging && "cursor-grabbing",
        !isDragging && "cursor-grab",
        className
      )}
    >
      <svg
        viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        className="w-full h-full"
        style={{ minHeight: "400px" }}
        role="img"
        aria-label="Graph visualization showing nodes and edges"
      >
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="hsl(var(--muted))"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" aria-hidden="true" />

        {/* Viewport transform group */}
        <g transform={transform}>
          {/* Edges */}
          {edges.map((edge, index) => {
            const source = nodeMap.get(edge.sourceId);
            const target = nodeMap.get(edge.targetId);
            if (!source || !target) return null;

            const sourcePos = getNodePosition(source);
            const targetPos = getNodePosition(target);

            return (
              <line
                key={`edge-${edge.sourceId}-${edge.targetId}-${index}`}
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke="hsl(var(--border))"
                strokeWidth="1.5"
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const colors = getEntityHexColors(node.entityType);
            const isSelected = node.id === selectedNodeId;
            const radius = getNodeRadius(node.entityType);
            const position = getNodePosition(node);

            const lines = wrapTextIntoLines(node.name, MAX_LABEL_LINE_LENGTH);
            const lineOffsetBase = (lines.length - 1) / 2;

            return (
              <g
                key={node.id}
                transform={`translate(${position.x}, ${position.y})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onNodeClick(node.id);
                }}
                onMouseEnter={() => onNodeHover?.(node.id)}
                onMouseLeave={() => onNodeHover?.(null)}
                className="cursor-pointer"
                style={{ cursor: "pointer" }}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    r={radius + 6}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    opacity={0.6}
                  />
                )}

                {/* Node body */}
                <circle
                  r={radius}
                  fill={colors.fill}
                  stroke={isSelected ? "hsl(var(--primary))" : colors.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                />

                {/* Label */}
                {lines.map((line, lineIndex) => (
                  <text
                    key={`${node.id}-line-${lineIndex}`}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="8"
                    fontFamily="var(--font-sans)"
                    fontWeight="600"
                    fill={colors.text}
                    pointerEvents="none"
                    y={(lineIndex - lineOffsetBase) * 11 + 1}
                  >
                    {line}
                  </text>
                ))}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
