/**
 * GraphInspectorPanel Component
 * Displays details for a selected graph node with properties and metadata.
 */

import React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from "@/components/ui/empty";
import { Info, BarChart3, FileText, MousePointer2, RotateCcw } from "lucide-react";
import type { GraphNode } from "@/features/graph/domain/graph.model";
import { getEntityBadgeClasses } from "@/lib/graph-utils";
import { Btn } from "@/components/ui/fabric";

/** Node details for the inspector panel */
export type GraphNodeDetails = GraphNode;

export interface GraphInspectorPanelProps {
  /** Selected node details (null shows empty state) */
  node: GraphNodeDetails | null;
  /** Called when user clicks Reset View button */
  onReset?: () => void;
  /** Called when user clicks Focus button */
  onFocus?: (nodeId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

const DEFAULT_CONFIDENCE = 0.8;

/**
 * Inspector panel for viewing node details.
 *
 * Shows:
 * - Entity name and type badge
 * - Confidence score with visual bar
 * - Description
 * - Properties list
 * - Action buttons (Focus, Reset)
 */
export function GraphInspectorPanel({
  node,
  onReset,
  onFocus,
  className,
}: GraphInspectorPanelProps) {
  if (!node) {
    return (
      <Card className={cn("h-full", className)}>
        <CardContent className="flex items-center justify-center h-full py-12">
          <Empty>
            <EmptyHeader>
              <Info className="h-10 w-10 text-muted-foreground/60" />
              <EmptyTitle>Select a Node</EmptyTitle>
              <EmptyDescription>
                Click on any node in the graph to view its properties and relationships
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        </CardContent>
      </Card>
    );
  }

  const badgeClasses = getEntityBadgeClasses(node.entityType);
  const typeLabel = node.entityType
    ? node.entityType.charAt(0).toUpperCase() + node.entityType.slice(1)
    : "Unknown";

  return (
    <Card className={cn("h-full overflow-auto", className)}>
      <CardHeader className="border-b">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base font-semibold truncate">{node.name}</CardTitle>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full vf-text-micro font-medium border shrink-0",
              badgeClasses.bg,
              badgeClasses.text,
              "border-current/20"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", badgeClasses.dot)} />
            {typeLabel}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        {/* Confidence */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <BarChart3 className="h-4 w-4" />
            <span>Confidence</span>
          </div>
          <ConfidenceBar value={node.confidenceScore ?? DEFAULT_CONFIDENCE} />
        </div>

        {/* Description */}
        {node.description && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>Description</span>
            </div>
            <p className="text-sm leading-relaxed text-foreground">{node.description}</p>
          </div>
        )}

        {/* Properties */}
        {node.properties && Object.keys(node.properties).length > 0 && (
          <div className="space-y-1.5">
            <div className="vf-text-micro font-semibold text-muted-foreground/60 uppercase tracking-wider">
              Properties
            </div>
            <dl className="space-y-1">
              {Object.entries(node.properties).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <dt className="text-muted-foreground">{key}</dt>
                  <dd className="font-medium text-foreground">{String(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* ID */}
        <div className="space-y-1.5">
          <div className="vf-text-micro font-semibold text-muted-foreground/60 uppercase tracking-wider">
            ID
          </div>
          <div className="vf-text-caption font-mono text-muted-foreground truncate">
            {node.id.slice(0, 16)}...
          </div>
        </div>

        {/* Actions */}
        {(onFocus || onReset) && (
          <div className="flex flex-col gap-1.5 pt-3 border-t border-border/50">
            {onFocus && (
              <Btn variant="ghost" className="vf-text-caption justify-center" onClick={() => onFocus(node.id)}>
                <MousePointer2 className="w-3 h-3 mr-1" /> Focus
              </Btn>
            )}
            {onReset && (
              <Btn variant="outline" className="vf-text-caption justify-center" onClick={onReset}>
                <RotateCcw className="w-3 h-3 mr-1" /> Reset View
              </Btn>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Visual confidence bar with color coding based on score.
 */
function ConfidenceBar({ value }: { value: number }) {
  const percentage = Math.round(value * 100);
  const colorClass =
    value >= 0.8 ? "bg-success/100" : value >= 0.6 ? "bg-warning/100" : "bg-destructive/100";

  return (
    <div className="space-y-1">
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", colorClass)} style={{ width: `${percentage}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">{percentage}%</p>
    </div>
  );
}
