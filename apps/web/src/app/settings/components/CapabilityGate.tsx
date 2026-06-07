import { useEffect, type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { captureMessage } from "@/lib/telemetry";
import {
  type SettingsCapability,
  describeDenialReason,
  useSettingsAccess,
} from "../access";

interface CapabilityGateProps {
  capability: SettingsCapability;
  children: ReactNode;
  fallbackTitle?: string;
  fallbackDescription?: string;
  className?: string;
}

export function CapabilityGate({
  capability,
  children,
  fallbackTitle = "Access restricted",
  fallbackDescription = "Your role does not include the permission required to view this settings section.",
  className,
}: CapabilityGateProps) {
  const { role, getCapabilityDecision } = useSettingsAccess();
  const decision = getCapabilityDecision(capability);

  useEffect(() => {
    if (!decision.allowed) {
      captureMessage("Privileged UI action denied", "warn", {
        feature: "settings-capability-gate",
        userId: role,
        errorCode: "UI_PRIVILEGED_ACTION_DENIED",
        capability,
        denialReasons: decision.reasons,
      });
    }
  }, [capability, decision.allowed, decision.reasons, role]);

  if (decision.allowed) return <>{children}</>;

  return (
    <section className={cn("rounded-lg border border-warning/20 bg-warning/10 p-5 dark:border-amber-900 dark:bg-amber-950", className)}>
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning dark:text-amber-300" />
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-amber-900 dark:text-amber-100">{fallbackTitle}</h3>
          <p className="text-xs text-warning dark:text-amber-200">{fallbackDescription}</p>
          <ul className="mt-1 list-disc pl-4 text-xs text-warning dark:text-amber-200">
            {decision.reasons.map((reason) => <li key={reason}>{describeDenialReason(reason)}</li>)}
          </ul>
          <p className="vf-text-caption uppercase tracking-wide text-warning/80 dark:text-amber-300/80">
            Current role: {role.replace("_", " ")}
          </p>
        </div>
      </div>
    </section>
  );
}
