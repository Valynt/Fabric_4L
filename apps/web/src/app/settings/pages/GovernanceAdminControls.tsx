import { Link } from "react-router-dom";
import { AlertTriangle, Shield, Workflow } from "lucide-react";
import { usePlatformSettings } from "@/hooks/usePlatformSettings";
import { useAuthContext } from "@/contexts/AuthContext";
import { CapabilityGate } from "../components/CapabilityGate";
import { SettingsMetricGrid, SettingsQueryState } from "../components/SettingsState";
import { governanceAdminControlMetrics } from "../schemas";

export function GovernanceAdminControls() {
  const { data: settings, isLoading, error } = usePlatformSettings();
  const { currentTenantSlug, user } = useAuthContext();
  const isSuperAdmin = user?.role === "super_admin";
  const tenantSettingsBase = currentTenantSlug
    ? `/t/${currentTenantSlug}/settings`
    : "/settings";

  return (
    <CapabilityGate capability="governance">
      <div className="space-y-6">
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-start gap-3">
            <Shield className="mt-0.5 h-4 w-4 text-primary" />
            <div>
              <h3 className="text-sm font-semibold">Tenant Security Controls</h3>
              <p className="text-xs text-muted-foreground">
                Canonical security and notification controls are now managed through
                live tenant settings rather than shell-only toggles.
              </p>
            </div>
          </div>

          <SettingsQueryState
            data={settings}
            isLoading={isLoading}
            error={error}
            loadingLabel="Loading current controls..."
            errorTitle="Failed to load tenant security controls"
          >
            {(currentSettings) => (
              <SettingsMetricGrid
                metrics={governanceAdminControlMetrics.map((metric) => ({
                  label: metric.label,
                  value:
                    metric.key === "tenantStatus" ? (
                      <span className="capitalize">
                        {currentSettings.tenant_status ?? "active"}
                      </span>
                    ) : metric.key === "mfaRequirement" ? (
                      currentSettings.security.require_2fa ? "Required" : "Optional"
                    ) : metric.key === "sessionTimeout" ? (
                      `${currentSettings.security.session_timeout_minutes} minutes`
                    ) : currentSettings.features.audit_trail ? (
                      "Enabled"
                    ) : (
                      "Disabled"
                    ),
                }))}
              />
            )}
          </SettingsQueryState>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to={`${tenantSettingsBase}/workspace`}
              className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90"
            >
              Manage tenant settings
            </Link>
            <Link
              to={`${tenantSettingsBase}/governance/health`}
              className="inline-flex h-8 items-center gap-1 rounded-md border px-3 text-xs font-medium hover:bg-accent"
            >
              <Workflow className="h-3.5 w-3.5" />
              Review health
            </Link>
          </div>
        </section>

        <section className="rounded-lg border border-destructive/20 bg-destructive/5 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 text-destructive" />
            <div className="space-y-2">
              <div>
                <h3 className="text-sm font-semibold text-destructive">Privileged Operations</h3>
                <p className="text-xs text-muted-foreground">
                  Suspend, export, and delete flows remain super-admin operations and should
                  stay outside tenant-admin self-service screens.
                </p>
              </div>
              <p className="text-xs text-muted-foreground">
                {isSuperAdmin
                  ? "Your current role can use the super-admin tenant management surfaces for destructive platform actions."
                  : "Your current role does not include destructive tenant lifecycle permissions."}
              </p>
            </div>
          </div>
        </section>
      </div>
    </CapabilityGate>
  );
}
