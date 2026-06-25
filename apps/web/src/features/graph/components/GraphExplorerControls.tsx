import { Search, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { SectionCard } from "@/components/blocks/SectionCard";
import { Btn } from "@/components/ui/fabric";
import { GraphLegend } from "@/components/ui/fabric";

export interface GraphExplorerControlsProps {
  queryText: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  scale: number;
  isSearching: boolean;
}

export function GraphExplorerControls({
  queryText,
  onQueryChange,
  onSearch,
  onZoomIn,
  onZoomOut,
  onResetView,
  scale,
  isSearching,
}: GraphExplorerControlsProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      onSearch();
    }
  };

  return (
    <>
      <SectionCard title="Control Panel" className="h-fit">
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search entities..."
              className="pl-8 h-9 text-sm"
              value={queryText}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>

          {/* Zoom Controls */}
          <div className="space-y-2">
            <div className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider">
              Zoom
            </div>
            <div className="flex gap-2">
              <Btn
                variant="ghost"
                className="flex-1 vf-text-caption"
                onClick={onZoomIn}
                aria-label="Zoom in"
              >
                <ZoomIn className="w-3 h-3 mr-1" /> In
              </Btn>
              <Btn
                variant="ghost"
                className="flex-1 vf-text-caption"
                onClick={onZoomOut}
                aria-label="Zoom out"
              >
                <ZoomOut className="w-3 h-3 mr-1" /> Out
              </Btn>
            </div>
            <div className="vf-text-micro text-muted-foreground/70 text-center">
              {Math.round(scale * 100)}%
            </div>
          </div>

          {/* View Controls */}
          <div className="space-y-2">
            <div className="vf-text-caption font-semibold text-muted-foreground uppercase tracking-wider">
              View
            </div>
            <Btn
              variant="ghost"
              className="w-full vf-text-caption justify-center"
              onClick={onResetView}
              aria-label="Reset view"
            >
              <RotateCcw className="w-3 h-3 mr-1" /> Reset View
            </Btn>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Legend" className="h-fit">
        <GraphLegend />
      </SectionCard>
    </>
  );
}
