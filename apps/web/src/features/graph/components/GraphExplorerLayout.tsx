import type { ReactNode } from "react";

export interface GraphExplorerLayoutProps {
  controls: ReactNode;
  canvas: ReactNode;
  inspector: ReactNode;
}

export function GraphExplorerLayout({
  controls,
  canvas,
  inspector,
}: GraphExplorerLayoutProps) {
  return (
    <div className="flex gap-4 h-[calc(100vh-280px)] min-h-[500px]">
      <div className="w-[200px] shrink-0 space-y-3">{controls}</div>
      <div className="flex-1 bg-card border border-border rounded-lg shadow-sm overflow-hidden relative">
        {canvas}
      </div>
      <div className="w-[250px] shrink-0 space-y-3">{inspector}</div>
    </div>
  );
}
