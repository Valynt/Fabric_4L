/**
 * Admin Components — Shared primitives for enterprise admin console pages.
 */

export { AdminShell, type AdminShellProps } from "./AdminShell";
export { AdminTabs, type AdminTab, type AdminTabsProps } from "./AdminTabs";
export {
  AdminStatCard,
  AdminStatsRow,
  type AdminStatCardProps,
  type AdminStatsRowProps,
  type AdminStatColor,
} from "./AdminStatCard";
export {
  AdminDataTable,
  type AdminDataTableProps,
  type AdminDataTableColumn,
} from "./AdminDataTable";
export {
  AdminFilterBar,
  type AdminFilterBarProps,
  type FilterChip,
} from "./AdminFilterBar";
export {
  AdminConfirmDialog,
  type AdminConfirmDialogProps,
} from "./AdminConfirmDialog";
export {
  AdminIconButton,
  AdminIconButtonGroup,
  type AdminIconButtonProps,
  type AdminIconButtonVariant,
  type AdminIconButtonGroupProps,
} from "./AdminIconButton";
export { AdminEmptyState, type AdminEmptyStateProps } from "./AdminEmptyState";
export { AdminLoadingState, type AdminLoadingStateProps } from "./AdminLoadingState";
export { AdminErrorState, type AdminErrorStateProps } from "./AdminErrorState";
