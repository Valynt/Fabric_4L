import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { usePlatformSettings, useUpdatePlatformSettings } from "@/hooks/usePlatformSettings";
import { CapabilityGate } from "../components/CapabilityGate";
import { safeAsync } from '@/lib/async';
import { SettingsPageShell } from "../components/SettingsPageShell";

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

  const dirty = useMemo(() => {
    if (!settings) return false;
    return (
      brandingDraft.logo_url !== (settings.branding?.logo_url ?? "") ||
      brandingDraft.primary_color !== (settings.branding?.primary_color ?? "") ||
      brandingDraft.custom_domain !== (settings.branding?.custom_domain ?? "") ||
      webhookDraft !== (settings.notifications.webhook_url ?? "")
    );
  }, [brandingDraft, webhookDraft, settings]);

  return (
    <CapabilityGate capability="billing">
      <SettingsPageShell
        title="Workspace Profile"
        description="Live tenant metadata and branding settings backed by Layer 4 tenant configuration."
        data={settings}
        isLoading={isLoading}
        error={error}
        loadingLabel="Loading workspace settings..."
        errorTitle="Failed to load workspace settings"
        metricGridClassName="md:grid-cols-3"
        metrics={(currentSettings) => [
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
        onSave={() => safeAsync(handleSave(), "billing.save")}
        isPending={updateSettings.isPending}
        saveLabel="Save workspace"
        dirty={dirty}
      >
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
      </SettingsPageShell>
    </CapabilityGate>
  );
}
