import { useEffect, useState } from "react";
import { toast } from "sonner";
import { usePlatformSettings, useUpdatePlatformSettings } from "@/hooks/usePlatformSettings";
import { CapabilityGate } from "../components/CapabilityGate";
import { safeAsync } from '@/lib/async';
import {
  SettingsMetricGrid,
  SettingsQueryState,
  SettingsSaveButton,
} from "../components/SettingsState";

export function BillingWorkspace() {
  const { data: settings, isLoading, error } = usePlatformSettings();
  const updateSettings = useUpdatePlatformSettings();
  const [brandingDraft, setBrandingDraft] = useState({
    logo_url: "",
    primary_color: "",
    custom_domain: "",
  });
  const [webhookDraft, setWebhookDraft] = useState("");

  useEffect(() => {
    if (!settings) {
      return;
    }

    setBrandingDraft({
      logo_url: settings.branding?.logo_url ?? "",
      primary_color: settings.branding?.primary_color ?? "",
      custom_domain: settings.branding?.custom_domain ?? "",
    });
    setWebhookDraft(settings.notifications.webhook_url ?? "");
  }, [settings]);

  const handleSave = async () => {
    try {
      await updateSettings.mutateAsync({
        branding: brandingDraft,
        notifications: { webhook_url: webhookDraft || undefined },
      });
      toast.success("Workspace settings updated");
    } catch (mutationError) {
      toast.error(
        mutationError instanceof Error
          ? mutationError.message
          : "Failed to update workspace settings"
      );
    }
  };

  return (
    <CapabilityGate capability="billing">
      <div className="space-y-6">
        <section className="rounded-lg border bg-card p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold">Workspace Profile</h3>
              <p className="text-xs text-muted-foreground">
                Live tenant metadata and branding settings backed by Layer 4 tenant configuration.
              </p>
            </div>
            <SettingsSaveButton
              onClick={() => safeAsync(handleSave(), "billing.save")}
              isPending={updateSettings.isPending}
            >
              Save workspace
            </SettingsSaveButton>
          </div>

          <SettingsQueryState
            data={settings}
            isLoading={isLoading}
            error={error}
            loadingLabel="Loading workspace settings..."
            errorTitle="Failed to load workspace settings"
          >
            {(currentSettings) => (
              <div className="mt-4 space-y-6">
                <SettingsMetricGrid
                  className="md:grid-cols-3"
                  metrics={[
                    { label: "Workspace name", value: currentSettings.tenant_name },
                    { label: "Tenant slug", value: currentSettings.tenant_slug ?? "n/a" },
                    {
                      label: "Status",
                      value: (
                        <span className="capitalize">
                          {currentSettings.tenant_status ?? "active"}
                        </span>
                      ),
                    },
                  ]}
                />

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-1 text-sm">
                    <span className="text-xs text-muted-foreground">Logo URL</span>
                    <input
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                      value={brandingDraft.logo_url}
                      onChange={(event) => setBrandingDraft((current) => ({ ...current, logo_url: event.target.value }))}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-xs text-muted-foreground">Primary color</span>
                    <input
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                      value={brandingDraft.primary_color}
                      onChange={(event) => setBrandingDraft((current) => ({ ...current, primary_color: event.target.value }))}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-xs text-muted-foreground">Custom domain</span>
                    <input
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                      value={brandingDraft.custom_domain}
                      onChange={(event) => setBrandingDraft((current) => ({ ...current, custom_domain: event.target.value }))}
                    />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-xs text-muted-foreground">Incident webhook</span>
                    <input
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                      value={webhookDraft}
                      onChange={(event) => setWebhookDraft(event.target.value)}
                    />
                  </label>
                </div>
              </div>
            )}
          </SettingsQueryState>
        </section>
      </div>
    </CapabilityGate>
  );
}
