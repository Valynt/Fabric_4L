/**
 * AdminEmptyState — Admin-styled empty state wrapper.
 */
import { EmptyState } from "@/components/states/EmptyState";
import type { LucideIcon } from "lucide-react";

export interface AdminEmptyStateProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}

export function AdminEmptyState({
  title,
  description,
  icon,
  action,
  className,
}: AdminEmptyStateProps) {
  return (
    <EmptyState
      title={title}
      description={description}
      icon={icon}
      action={action}
      className={className}
    />
  );
}
