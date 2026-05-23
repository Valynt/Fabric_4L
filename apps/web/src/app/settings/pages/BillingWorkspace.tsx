import { useEffect, useState } from "react";
import { toast } from "sonner";
import { usePlatformSettings, useUpdatePlatformSettings } from "@/hooks/usePlatformSettings";
import { CapabilityGate } from "../components/CapabilityGate";
import { safeAsync } from '@/lib/async';

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
            <button
              type="button"
              onClick={() => safeAsync(handleSave(), "billing.save")}
              disabled={updateSettings.isPending}
              className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {updateSettings.isPending ? "Saving..." : "Save workspace"}
            </button>
          </div>

          {isLoading ? (
            <div className="mt-4 rounded-md border p-4 text-sm text-muted-foreground">
              Loading workspace settings...
            </div>
          ) : error ? (
            <div className="mt-4 rounded-md border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
              {error.message}
            </div>
          ) : settings ? (
            <div className="mt-4 space-y-6">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-md border p-4">
                  <p className="text-xs text-muted-foreground">Workspace name</p>
                  <p className="mt-1 text-sm font-medium">{settings.tenant_name}</p>
                </div>
                <div className="rounded-md border p-4">
                  <p className="text-xs text-muted-foreground">Tenant slug</p>
                  <p className="mt-1 text-sm font-medium">{settings.tenant_slug ?? "n/a"}</p>
                </div>
                <div className="rounded-md border p-4">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <p className="mt-1 text-sm font-medium capitalize">{settings.tenant_status ?? "active"}</p>
                </div>
              </div>

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
          ) : null}
        </section>
      </div>
    </CapabilityGate>
  );
}
