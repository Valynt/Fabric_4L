import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  data?: T[];
  columns: DataTableColumn<T>[] | string[];
  keyExtractor?: (item: T, idx: number) => string;
  rows?: React.ReactNode[][];
  emptyMessage?: string;
  className?: string;
  onRowClick?: (item: T) => void;
  selectedKey?: string;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  rows,
  emptyMessage = "No data available",
  className,
  onRowClick,
  selectedKey,
}: DataTableProps<T>) {
  // Legacy API: columns as string[], rows as ReactNode[][]
  if (rows !== undefined) {
    const legacyColumns = columns as string[];
    const safeRows = rows ?? [];
    return (
      <div className={cn("rounded-lg border border-border overflow-hidden overflow-x-auto", className)}>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50 hover:bg-muted/50">
              {legacyColumns.map((col, idx) => (
                <TableHead
                  key={idx}
                  className="h-10 px-4 vf-text-body-s font-medium text-muted-foreground uppercase tracking-wider"
                >
                  {col}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {safeRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={legacyColumns.length} className="h-32 text-center text-muted-foreground text-sm">
                  {emptyMessage}
                </TableCell>
              </TableRow>
            ) : (
              safeRows.map((row, rowIdx) => (
                <TableRow
                  key={rowIdx}
                  className="h-12 border-t border-border hover:bg-muted/30 transition-colors"
                >
                  {row.map((cell, cellIdx) => (
                    <TableCell key={cellIdx} className="px-4 vf-text-body-m text-foreground">
                      {cell}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    );
  }

  // Typed API: columns as DataTableColumn<T>[], data as T[]
  const safeData = data ?? [];
  const typedColumns = columns as DataTableColumn<T>[];
  const safeKeyExtractor = keyExtractor ?? ((item: T, idx: number) => String(idx));

  const handleKeyDown = (item: T, e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onRowClick?.(item);
    }
  };

  return (
    <div className={cn("rounded-lg border border-border overflow-hidden overflow-x-auto", className)}>
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            {typedColumns.map((col) => (
              <TableHead
                key={String(col.key)}
                className={cn("h-10 px-4 vf-text-body-s font-medium text-muted-foreground uppercase tracking-wider", col.className)}
              >
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {safeData.length === 0 ? (
            <TableRow>
              <TableCell colSpan={typedColumns.length} className="h-32 text-center text-muted-foreground text-sm">
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            safeData.map((item, idx) => (
              <TableRow
                key={safeKeyExtractor(item, idx)}
                onClick={() => onRowClick?.(item)}
                onKeyDown={(e) => handleKeyDown(item, e)}
                tabIndex={onRowClick ? 0 : -1}
                role={onRowClick ? "button" : "row"}
                className={cn(
                  "h-12 border-t border-border hover:bg-muted/30 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  onRowClick && "cursor-pointer",
                  selectedKey === safeKeyExtractor(item, idx) && "bg-primary/5"
                )}
              >
                {typedColumns.map((col) => (
                  <TableCell key={String(col.key)} className={cn("px-4 vf-text-body-m text-foreground", col.className)}>
                    {col.render ? col.render(item) : String((item as Record<string, unknown>)[col.key as string] ?? "")}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
