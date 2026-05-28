/**
 * RelationshipMap — Visual graph of type relationships
 *
 * Right panel of the Ontology Editor showing:
 * - Nodes representing ontology types
 * - Edges representing relationships between types
 * - Simple force-directed layout visualization
 */

import { useMemo, useRef, useEffect, useState } from 'react';
import { Box, Layers, Users, TrendingUp, Puzzle, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { OntologyType, TypeRelationship } from '@/hooks/useOntology';

interface RelationshipMapProps {
  types: OntologyType[];
  relationships: TypeRelationship[];
  selectedTypeId: string | null;
  onSelectType: (id: string) => void;
  className?: string;
}

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  capability: { bg: 'bg-violet-100', border: 'border-violet-300', text: 'text-violet-800' },
  feature: { bg: 'bg-violet-50', border: 'border-violet-200', text: 'text-violet-600' },
  usecase: { bg: 'bg-cyan-100', border: 'border-cyan-300', text: 'text-cyan-800' },
  persona: { bg: 'bg-amber-100', border: 'border-amber-300', text: 'text-amber-800' },
  valuedriver: { bg: 'bg-emerald-100', border: 'border-emerald-300', text: 'text-emerald-800' },
};

const RELATIONSHIP_COLORS: Record<string, string> = {
  depends_on: '#ef4444', // red
  extends: '#8b5cf6', // violet
  relates_to: '#06b6d4', // cyan
  contains: '#f59e0b', // amber
};

function getTypeColor(typeId: string) {
  const normalizedId = typeId.toLowerCase().replace(/_/g, '');
  for (const [key, colors] of Object.entries(TYPE_COLORS)) {
    if (normalizedId.includes(key)) return colors;
  }
  return { bg: 'bg-muted', border: 'border-border', text: 'text-foreground' };
}

function getTypeIcon(typeId: string) {
  const normalizedId = typeId.toLowerCase().replace(/_/g, '');
  if (normalizedId.includes('capability')) return <Box size={12} />;
  if (normalizedId.includes('feature')) return <Puzzle size={12} />;
  if (normalizedId.includes('usecase')) return <Layers size={12} />;
  if (normalizedId.includes('persona')) return <Users size={12} />;
  if (normalizedId.includes('valuedriver')) return <TrendingUp size={12} />;
  return <Box size={12} />;
}

export function RelationshipMap({
  types,
  relationships,
  selectedTypeId,
  onSelectType,
  className,
}: RelationshipMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (containerRef.current) {
      const { width, height } = containerRef.current.getBoundingClientRect();
      setDimensions({ width, height });
    }

    const handleResize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Simple layout: arrange types in a circle
  const nodePositions = useMemo(() => {
    const positions = new Map<string, { x: number; y: number }>();
    if (dimensions.width === 0 || dimensions.height === 0) return positions;

    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;
    const radius = Math.min(dimensions.width, dimensions.height) * 0.35;

    types.forEach((type, index) => {
      const angle = (index / types.length) * 2 * Math.PI - Math.PI / 2;
      positions.set(type.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });

    return positions;
  }, [types, dimensions]);

  if (types.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center h-full p-4", className)}>
        <p className="text-sm text-muted-foreground">No types to display</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="px-3 py-2 border-b border-border">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          Relationship Map
        </h3>
      </div>

      {/* Legend */}
      <div className="px-3 py-2 border-b border-border bg-muted/30">
        <div className="flex flex-wrap gap-2">
          {Object.entries(RELATIONSHIP_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-muted-foreground capitalize">
                {type.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden bg-muted/10">
        <svg
          width={dimensions.width}
          height={dimensions.height}
          className="absolute inset-0"
          role="img"
          aria-label="Relationship map showing ontology types and their connections"
        >
          {/* Edges */}
          {relationships.map((rel) => {
            const source = nodePositions.get(rel.sourceTypeId);
            const target = nodePositions.get(rel.targetTypeId);
            if (!source || !target) return null;

            const color = RELATIONSHIP_COLORS[rel.relationshipType] || '#94a3b8';

            return (
              <g key={rel.id}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={color}
                  strokeWidth={2}
                  strokeDasharray={rel.relationshipType === 'depends_on' ? '4,4' : undefined}
                />
                {/* Arrow head */}
                <polygon
                  points={`0,-4 8,0 0,4`}
                  fill={color}
                  transform={`translate(${target.x}, ${target.y}) rotate(${
                    (Math.atan2(target.y - source.y, target.x - source.x) * 180) / Math.PI
                  }) translate(-20, 0)`}
                />
              </g>
            );
          })}
        </svg>

        {/* Nodes */}
        {types.map((type) => {
          const pos = nodePositions.get(type.id);
          if (!pos) return null;

          const colors = getTypeColor(type.id);
          const isSelected = selectedTypeId === type.id;

          return (
            <button
              key={type.id}
              onClick={() => onSelectType(type.id)}
              className={cn(
                "absolute transform -translate-x-1/2 -translate-y-1/2",
                "flex flex-col items-center gap-1 p-2 rounded-lg border transition-all",
                colors.bg,
                colors.border,
                isSelected
                  ? "ring-2 ring-primary ring-offset-2 scale-110 z-10"
                  : "hover:scale-105 hover:shadow-md"
              )}
              style={{ left: pos.x, top: pos.y }}
            >
              <span className={cn("text-muted-foreground", colors.text)}>
                {getTypeIcon(type.id)}
              </span>
              <span className={cn("text-[10px] font-medium whitespace-nowrap", colors.text)}>
                {type.name}
              </span>
            </button>
          );
        })}
      </div>

      {/* Selected Type Info */}
      {selectedTypeId && (
        <div className="px-3 py-2 border-t border-border bg-muted/30">
          {(() => {
            const type = types.find((t) => t.id === selectedTypeId);
            if (!type) return null;

            const incoming = relationships.filter((r) => r.targetTypeId === selectedTypeId);
            const outgoing = relationships.filter((r) => r.sourceTypeId === selectedTypeId);

            return (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {getTypeIcon(type.id)}
                  <span className="text-[12px] font-semibold">{type.name}</span>
                </div>
                <div className="flex gap-4 text-[10px] text-muted-foreground">
                  <span>{type.properties.length} properties</span>
                  <span>{incoming.length} incoming</span>
                  <span>{outgoing.length} outgoing</span>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

export default RelationshipMap;
