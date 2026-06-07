/**
 * TypeTree — Hierarchical tree view of ontology types
 *
 * Left panel of the Ontology Editor showing:
 * - Expandable/collapsible type hierarchy
 * - Type selection with visual feedback
 * - Icons indicating type category
 */

import { useMemo } from 'react';
import { ChevronRight, ChevronDown, Box, Layers, Users, TrendingUp, Puzzle } from 'lucide-react';
import { cn } from '@/lib/utils';
import useOntologyStore from '@/stores/ontologyStore';
import type { OntologyType } from '@/hooks/useOntology';

interface TypeTreeProps {
  types: OntologyType[];
  className?: string;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  capability: <Box size={14} className="text-primary" />,
  feature: <Puzzle size={14} className="text-primary" />,
  usecase: <Layers size={14} className="text-info" />,
  persona: <Users size={14} className="text-warning" />,
  valuedriver: <TrendingUp size={14} className="text-success" />,
};

function getTypeIcon(typeId: string): React.ReactNode {
  const normalizedId = typeId.toLowerCase().replace(/_/g, '');
  for (const [key, icon] of Object.entries(TYPE_ICONS)) {
    if (normalizedId.includes(key)) return icon;
  }
  return <Box size={14} className="text-muted-foreground" />;
}

export function TypeTree({ types, className }: TypeTreeProps) {
  const {
    selectedTypeId,
    expandedTypeIds,
    selectType,
    toggleTypeExpanded,
  } = useOntologyStore();

  // Build tree structure
  const tree = useMemo(() => {
    const typeMap = new Map<string, OntologyType>();
    types.forEach(type => typeMap.set(type.id, type));

    const rootTypes: OntologyType[] = [];
    const childrenMap = new Map<string, OntologyType[]>();

    types.forEach(type => {
      if (type.parentTypeId) {
        const siblings = childrenMap.get(type.parentTypeId) || [];
        siblings.push(type);
        childrenMap.set(type.parentTypeId, siblings);
      } else {
        rootTypes.push(type);
      }
    });

    return { rootTypes, childrenMap, typeMap };
  }, [types]);

  if (types.length === 0) {
    return (
      <div className={cn("p-4 text-center", className)}>
        <p className="text-sm text-muted-foreground">No types defined</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      <div className="px-3 py-2 border-b border-border">
        <h3 className="vf-text-caption font-bold uppercase tracking-wider text-muted-foreground">
          Type Tree
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto py-2">
        {tree.rootTypes.map(type => (
          <TypeTreeNode
            key={type.id}
            type={type}
            depth={0}
            childrenMap={tree.childrenMap}
            selectedTypeId={selectedTypeId}
            expandedTypeIds={expandedTypeIds}
            onSelect={selectType}
            onToggleExpand={toggleTypeExpanded}
          />
        ))}
      </div>
    </div>
  );
}

interface TypeTreeNodeProps {
  type: OntologyType;
  depth: number;
  childrenMap: Map<string, OntologyType[]>;
  selectedTypeId: string | null;
  expandedTypeIds: Set<string>;
  onSelect: (id: string) => void;
  onToggleExpand: (id: string) => void;
}

function TypeTreeNode({
  type,
  depth,
  childrenMap,
  selectedTypeId,
  expandedTypeIds,
  onSelect,
  onToggleExpand,
}: TypeTreeNodeProps) {
  const isSelected = selectedTypeId === type.id;
  const isExpanded = expandedTypeIds.has(type.id);
  const children = childrenMap.get(type.id) || [];
  const hasChildren = children.length > 0;

  const indentClass = depth === 0 ? '' : `ml-${depth * 3}`;

  return (
    <div className={indentClass}>
      <button
        onClick={() => onSelect(type.id)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-1.5 text-left transition-colors",
          "hover:bg-muted/50",
          isSelected && "bg-primary/10 hover:bg-primary/10"
        )}
      >
        <span
          onClick={(e) => {
            if (hasChildren) {
              e.stopPropagation();
              onToggleExpand(type.id);
            }
          }}
          className={cn(
            "flex items-center justify-center w-4 h-4 rounded",
            hasChildren && "cursor-pointer hover:bg-muted"
          )}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown size={12} className="text-muted-foreground" />
            ) : (
              <ChevronRight size={12} className="text-muted-foreground" />
            )
          ) : (
            <span className="w-3" />
          )}
        </span>

        {getTypeIcon(type.id)}

        <span
          className={cn(
            "vf-text-body-s truncate",
            isSelected ? "font-semibold text-primary" : "text-foreground"
          )}
        >
          {type.name}
        </span>

        <span className="ml-auto vf-text-micro text-muted-foreground">
          {type.properties.length}
        </span>
      </button>

      {hasChildren && isExpanded && (
        <div className="border-l border-border ml-4 mt-0.5">
          {children.map(child => (
            <TypeTreeNode
              key={child.id}
              type={child}
              depth={depth + 1}
              childrenMap={childrenMap}
              selectedTypeId={selectedTypeId}
              expandedTypeIds={expandedTypeIds}
              onSelect={onSelect}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default TypeTree;
