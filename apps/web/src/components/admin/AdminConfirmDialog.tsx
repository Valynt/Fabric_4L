/**
 * AdminConfirmDialog — Destructive-action confirmation for admin workflows.
 *
 * Security requirement: displays tenant scope and action impact before
 * destructive operations (delete, revoke, deactivate, etc.).
 */
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { AlertTriangle, Building2 } from "lucide-react";

export interface AdminConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  itemName?: string;
  tenantName?: string;
  tenantId?: string;
  actionLabel?: string;
  cancelLabel?: string;
  variant?: "destructive" | "warning";
  onConfirm: () => void;
  isPending?: boolean;
}

export function AdminConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  itemName,
  tenantName,
  tenantId,
  actionLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "destructive",
  onConfirm,
  isPending,
}: AdminConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle
              className={cn(
                "h-5 w-5",
                variant === "destructive" ? "text-destructive" : "text-warning"
              )}
            />
            <AlertDialogTitle className="vf-heading-l font-semibold">
              {title}
            </AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div className="vf-text-body-m space-y-3">
              {description && <p>{description}</p>}
              {itemName && (
                <p className="font-medium text-foreground">
                  Target: <span className="font-semibold">{itemName}</span>
                </p>
              )}
              {(tenantName || tenantId) && (
                <div
                  className={cn(
                    "flex items-start gap-2 rounded-lg border p-3",
                    variant === "destructive"
                      ? "border-destructive/20 bg-destructive/5"
                      : "border-warning/20 bg-warning/5"
                  )}
                >
                  <Building2
                    className={cn(
                      "h-4 w-4 mt-0.5 shrink-0",
                      variant === "destructive" ? "text-destructive" : "text-warning"
                    )}
                  />
                  <div className="space-y-0.5">
                    <p
                      className={cn(
                        "vf-text-caption font-semibold",
                        variant === "destructive" ? "text-destructive" : "text-warning"
                      )}
                    >
                      Tenant scope
                    </p>
                    <p className="vf-text-caption text-foreground">
                      {tenantName || "Unknown tenant"}
                      {tenantId && (
                        <span className="block font-mono text-muted-foreground">
                          ID: {tenantId}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isPending}>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              onConfirm();
            }}
            disabled={isPending}
            className={cn(
              variant === "destructive" &&
                "bg-destructive text-destructive-foreground hover:bg-destructive/90"
            )}
          >
            {isPending ? "Please wait…" : actionLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
