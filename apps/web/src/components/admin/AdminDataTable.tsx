/**
 * AdminDataTable — Data table tailored for admin workflows.
 *
 * Wraps the shared DataTable with admin-specific empty/loading/error states.
 */
import {
  DataTable,
  type DataTableProps,
  type DataTableColumn,
} from "@/components/ui/fabric";
import { LoadingState } from "@/components/states/LoadingState";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { Inbox, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type AdminDataTableColumn<T> = DataTableColumn<T>;

export interface AdminDataTableProps<T>
  extends Omit<DataTableProps<T>, "emptyMessage"> {
  isLoading?: boolean;
  error?: Error | unknown;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyIcon?: LucideIcon;
  emptyAction?: React.ReactNode;
  className?: string;
  tableClassName?: string;
}

export function AdminDataTable<T>({
  isLoading,
  error,
  onRetry,
  data,
  emptyTitle = "No data available",
  emptyDescription,
  emptyIcon: EmptyIcon,
  emptyAction,
  className,
  tableClassName,
  columns,
  ...tableProps
}: AdminDataTableProps<T>) {
  if (isLoading) {
    return (
      <div className={cn("rounded-xl border border-border bg-card", className)}>
        <LoadingState message="Loading data…" className="py-16" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("rounded-xl border border-border bg-card", className)}>
        <ErrorState
          title="Failed to load data"
          description="An error occurred while loading this table."
          error={error}
          onRetry={onRetry}
        />
      </div>
    );
  }

  const safeData = data ?? [];
  const showEmpty = safeData.length === 0;

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card shadow-sm overflow-hidden",
        className
      )}
    >
      {!showEmpty && (
        <DataTable
          data={safeData}
          columns={columns}
          emptyMessage=""
          className={tableClassName}
          {...tableProps}
        />
      )}
      {showEmpty && (
        <EmptyState
          icon={EmptyIcon ?? Inbox}
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
          className="py-12"
        />
      )}
    </div>
  );
}

export { DataTableColumn };
