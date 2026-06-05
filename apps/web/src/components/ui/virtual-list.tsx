/**
 * VirtualList — Windowed list rendering for large datasets.
 *
 * Built on @tanstack/react-virtual. Renders only visible items
 * plus a small overscan buffer for smooth scrolling.
 */

import { Fragment, useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { cn } from "@/lib/utils";

interface VirtualListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  estimateSize: number;
  overscan?: number;
  className?: string;
  itemClassName?: string;
  columns?: number;
}

export function VirtualList<T>({
  items,
  renderItem,
  estimateSize,
  overscan = 5,
  className,
  itemClassName,
  columns = 1,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowCount = Math.ceil(items.length / columns);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  return (
    <div
      ref={parentRef}
      className={cn("overflow-auto", className)}
      style={{ contain: "strict" }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const rowStartIndex = virtualItem.index * columns;
          const rowItems = items.slice(rowStartIndex, rowStartIndex + columns);

          return (
            <div
              key={virtualItem.key}
              className={cn("absolute left-0 top-0 w-full", itemClassName)}
              style={{
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {columns > 1 ? (
                <div className="grid h-full" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`, gap: '0.75rem' }}>
                  {rowItems.map((item, colIndex) => (
                    <Fragment key={rowStartIndex + colIndex}>
                      {renderItem(item, rowStartIndex + colIndex)}
                    </Fragment>
                  ))}
                </div>
              ) : (
                renderItem(items[virtualItem.index], virtualItem.index)
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
