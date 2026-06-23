import { Shield, ShieldCheck, ShieldAlert, Lock } from "lucide-react";
import { useAccountGates } from "@/hooks/useGates";
import { Skeleton } from "@/components/ui/skeleton";

interface GateStatusBannerProps {
  accountId: string;
}

export function GateStatusBanner({ accountId }: GateStatusBannerProps) {
  const { data: gateSummary, isLoading, error } = useAccountGates(accountId);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 mb-4">
        <Skeleton className="h-5 w-48 mb-2" />
        <div className="flex gap-3">
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-6 w-20" />
          <Skeleton className="h-6 w-20" />
        </div>
      </div>
    );
  }

  if (error || !gateSummary) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4 mb-4 text-destructive text-sm">
        Unable to load gate status. Export and sharing may be unavailable.
      </div>
    );
  }

  const { all_passed, gates } = gateSummary;

  if (all_passed) {
    return (
      <div className="rounded-lg border border-success/20 bg-success/10 p-4 mb-4 flex items-center gap-3">
        <ShieldCheck className="h-5 w-5 text-success shrink-0" />
        <div>
          <p className="text-sm font-medium text-success">All gates closed</p>
          <p className="text-xs text-success">This account is ready for export and CRM push.</p>
        </div>
      </div>
    );
  }

  const openGates = gates.filter((g) => g.status === "open");

  return (
    <div className="rounded-lg border border-warning/20 bg-warning/10 p-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <ShieldAlert className="h-5 w-5 text-warning shrink-0" />
        <p className="text-sm font-medium text-warning">
          {openGates.length} gate{openGates.length > 1 ? "s" : ""} open — export blocked
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {gates.map((gate) => {
          const isClosed = gate.status !== "open";
          return (
            <span
              key={gate.type}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                isClosed
                  ? "bg-success/10 text-success"
                  : "bg-warning/10 text-warning"
              }`}
              title={gate.reason || undefined}
            >
              {isClosed ? (
                <ShieldCheck className="h-3 w-3" />
              ) : (
                <Lock className="h-3 w-3" />
              )}
              {gate.type}
            </span>
          );
        })}
      </div>
    </div>
  );
}
