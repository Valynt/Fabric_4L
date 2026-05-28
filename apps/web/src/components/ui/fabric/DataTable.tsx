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
  data: T[];
  columns: DataTableColumn<T>[];
  keyExtractor: (item: T) => string;
  emptyMessage?: string;
  className?: string;
  onRowClick?: (item: T) => void;
  selectedKey?: string;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  emptyMessage = "No data available",
  className,
  onRowClick,
  selectedKey,
}: DataTableProps<T>) {
  // Ensure data is always an array to prevent runtime errors
  const safeData = data ?? [];

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
            {columns.map((col) => (
              <TableHead
                key={String(col.key)}
                className={cn("h-10 px-4 text-[12px] font-medium text-muted-foreground uppercase tracking-wider", col.className)}
              >
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {safeData.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-32 text-center text-muted-foreground text-sm">
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            safeData.map((item) => (
              <TableRow
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                onKeyDown={(e) => handleKeyDown(item, e)}
                tabIndex={onRowClick ? 0 : -1}
                role={onRowClick ? "button" : "row"}
                className={cn(
                  "h-12 border-t border-border hover:bg-muted/30 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  onRowClick && "cursor-pointer",
                  selectedKey === keyExtractor(item) && "bg-primary/5"
                )}
              >
                {columns.map((col) => (
                  <TableCell key={String(col.key)} className={cn("px-4 text-[13px] text-foreground", col.className)}>
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
