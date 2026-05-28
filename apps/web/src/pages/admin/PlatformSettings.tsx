/**
 * PlatformSettings — Admin Tier 3 Page
 * 
 * Tenant-level platform configuration:
 * - Feature flags (advanced analytics, AI assistant, etc.)
 * - Notification preferences (email, Slack, webhooks)
 * - Security settings (2FA, session timeout, IP allowlist)
 * - Resource limits (users, API calls, storage)
 * - Branding customization (logo, colors)
 * 
 * Connected to Layer 4 governance endpoints
 */

import { useState, useMemo } from "react";
import {
  Settings, Bell, Shield, Zap, Users, Database,
  Palette, Save, Loader2, AlertCircle, RefreshCw,
  CheckCircle2, ExternalLink, Info
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import ErrorBoundary from "@/components/ErrorBoundary";
import { cn } from "@/lib/utils";
import {
  usePlatformSettings,
  useUpdatePlatformSettings,
  type TenantSettings,
  type UpdateSettingsPayload,
} from "@/hooks/usePlatformSettings";
import { createFeatureLogger } from "@/lib/telemetry";
import { PageHeader, Btn } from "@/components/ui/fabric";

const log = createFeatureLogger('PlatformSettings');

// ── Types ────────────────────────────────────────────────────────────────────

type TabType = "features" | "notifications" | "security" | "branding";

// ── Styling Constants ───────────────────────────────────────────────────────────

const FEATURE_DESCRIPTIONS: Record<keyof TenantSettings['features'], string> = {
  advanced_analytics: "Enable advanced data visualization and custom dashboards",
  custom_integrations: "Allow custom API integrations and webhooks",
  ai_assistant: "Enable AI-powered formula suggestions and business case insights",
  audit_trail: "Track all user actions with detailed audit logs",
};

const FEATURE_ICONS: Record<keyof TenantSettings['features'], React.ReactNode> = {
  advanced_analytics: <Database size={16} />,
  custom_integrations: <ExternalLink size={16} />,
  ai_assistant: <Zap size={16} />,
  audit_trail: <Info size={16} />,
};

// ── Helper Functions ───────────────────────────────────────────────────────────

function formatNumber(num: number): string {
  return num.toLocaleString();
}

// ── Sub-components ───────────────────────────────────────────────────────────

function FeatureToggle({
  feature,
  enabled,
  onToggle,
  disabled,
}: {
  feature: keyof TenantSettings['features'];
  enabled: boolean;
  onToggle: (value: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-start justify-between p-4 bg-card border border-border rounded-xl">
      <div className="flex items-start gap-3">
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
          enabled ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
        )}>
          {FEATURE_ICONS[feature]}
        </div>
        <div>
          <h4 className="text-[13px] font-semibold text-foreground capitalize">
            {feature.replace('_', ' ')}
          </h4>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            {FEATURE_DESCRIPTIONS[feature]}
          </p>
        </div>
      </div>
      <Switch
        checked={enabled}
        onCheckedChange={onToggle}
        disabled={disabled}
      />
    </div>
  );
}

function NotificationsPanel({
  settings,
  onUpdate,
  isPending,
}: {
  settings: TenantSettings['notifications'];
  onUpdate: (updates: Partial<TenantSettings['notifications']>) => void;
  isPending: boolean;
}) {
  const [localWebhook, setLocalWebhook] = useState(settings.webhook_url || '');
  const [localSlack, setLocalSlack] = useState(settings.slack_webhook || '');

  return (
    <div className="space-y-4">
      {/* Email Alerts Toggle */}
      <div className="flex items-center justify-between p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Bell size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Email Alerts</h4>
            <p className="text-[11px] text-muted-foreground">Receive notifications via email</p>
          </div>
        </div>
        <Switch
          checked={settings.email_alerts}
          onCheckedChange={(checked) => onUpdate({ email_alerts: checked })}
          disabled={isPending}
        />
      </div>

      {/* Slack Webhook */}
      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 text-purple-600 flex items-center justify-center shrink-0">
            <ExternalLink size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Slack Integration</h4>
            <p className="text-[11px] text-muted-foreground">Post alerts to Slack channel</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={localSlack}
            onChange={(e) => setLocalSlack(e.target.value)}
            placeholder="https://hooks.slack.com/services/..."
            className="flex-1 px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <Btn
            variant="outline"
            onClick={() => onUpdate({ slack_webhook: localSlack || undefined })}
            disabled={isPending}
          >
            Save
          </Btn>
        </div>
      </div>

      {/* Custom Webhook */}
      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-violet-500/10 text-violet-600 flex items-center justify-center shrink-0">
            <ExternalLink size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Custom Webhook</h4>
            <p className="text-[11px] text-muted-foreground">POST events to custom URL</p>
          </div>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={localWebhook}
            onChange={(e) => setLocalWebhook(e.target.value)}
            placeholder="https://your-domain.com/webhook"
            className="flex-1 px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <Btn
            variant="outline"
            onClick={() => onUpdate({ webhook_url: localWebhook || undefined })}
            disabled={isPending}
          >
            Save
          </Btn>
        </div>
      </div>
    </div>
  );
}

function SecurityPanel({
  settings,
  onUpdate,
  isPending,
}: {
  settings: TenantSettings['security'];
  onUpdate: (updates: Partial<TenantSettings['security']>) => void;
  isPending: boolean;
}) {
  const [localTimeout, setLocalTimeout] = useState(settings.session_timeout_minutes);
  const [newIp, setNewIp] = useState('');

  const addIp = () => {
    if (newIp && !settings.ip_allowlist.includes(newIp)) {
      onUpdate({ ip_allowlist: [...settings.ip_allowlist, newIp] });
      setNewIp('');
    }
  };

  const removeIp = (ip: string) => {
    onUpdate({ ip_allowlist: settings.ip_allowlist.filter(i => i !== ip) });
  };

  return (
    <div className="space-y-4">
      {/* 2FA Toggle */}
      <div className="flex items-center justify-between p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-600 flex items-center justify-center shrink-0">
            <Shield size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Require Two-Factor Auth</h4>
            <p className="text-[11px] text-muted-foreground">Mandate 2FA for all tenant users</p>
          </div>
        </div>
        <Switch
          checked={settings.require_2fa}
          onCheckedChange={(checked) => onUpdate({ require_2fa: checked })}
          disabled={isPending}
        />
      </div>

      {/* Session Timeout */}
      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-600 flex items-center justify-center shrink-0">
            <Users size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Session Timeout</h4>
            <p className="text-[11px] text-muted-foreground">Auto-logout after inactivity</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={15}
            max={480}
            step={15}
            value={localTimeout}
            onChange={(e) => setLocalTimeout(parseInt(e.target.value))}
            className="flex-1"
          />
          <span className="text-[13px] font-medium text-foreground w-24">
            {localTimeout} min
          </span>
          <Btn
            variant="outline"
            onClick={() => onUpdate({ session_timeout_minutes: localTimeout })}
            disabled={isPending || localTimeout === settings.session_timeout_minutes}
          >
            Save
          </Btn>
        </div>
      </div>

      {/* IP Allowlist */}
      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Shield size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">IP Allowlist</h4>
            <p className="text-[11px] text-muted-foreground">Restrict access to specific IPs (empty = allow all)</p>
          </div>
        </div>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={newIp}
            onChange={(e) => setNewIp(e.target.value)}
            placeholder="192.168.1.1 or 10.0.0.0/8"
            className="flex-1 px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            onKeyDown={(e) => e.key === 'Enter' && addIp()}
          />
          <Btn variant="outline" onClick={addIp} disabled={!newIp}>
            Add
          </Btn>
        </div>
        {settings.ip_allowlist.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {settings.ip_allowlist.map(ip => (
              <span
                key={ip}
                className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary text-[11px] rounded-lg"
              >
                {ip}
                <button
                  onClick={() => removeIp(ip)}
                  className="hover:text-primary/80"
                  disabled={isPending}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function BrandingPanel({
  branding,
  onUpdate,
  isPending,
}: {
  branding?: TenantSettings['branding'];
  onUpdate: (updates: Partial<TenantSettings['branding']>) => void;
  isPending: boolean;
}) {
  const [localLogo, setLocalLogo] = useState(branding?.logo_url || '');
  const [localColor, setLocalColor] = useState(branding?.primary_color || '#2563eb');
  const [localFavicon, setLocalFavicon] = useState(branding?.favicon_url || '');

  return (
    <div className="space-y-4">
      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-pink-500/10 text-pink-600 flex items-center justify-center shrink-0">
            <Palette size={16} />
          </div>
          <div>
            <h4 className="text-[13px] font-semibold text-foreground">Custom Branding</h4>
            <p className="text-[11px] text-muted-foreground">Customize your tenant appearance</p>
          </div>
        </div>

        {/* Logo URL */}
        <div className="mb-4">
          <label className="block text-[11px] font-medium text-muted-foreground mb-1.5">
            Logo URL
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={localLogo}
              onChange={(e) => setLocalLogo(e.target.value)}
              placeholder="https://cdn.example.com/logo.png"
              className="flex-1 px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        {/* Primary Color */}
        <div className="mb-4">
          <label className="block text-[11px] font-medium text-muted-foreground mb-1.5">
            Primary Color
          </label>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={localColor}
              onChange={(e) => setLocalColor(e.target.value)}
              className="w-10 h-10 rounded-lg border border-border cursor-pointer"
            />
            <input
              type="text"
              value={localColor}
              onChange={(e) => setLocalColor(e.target.value)}
              className="flex-1 px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono"
            />
          </div>
        </div>

        {/* Favicon URL */}
        <div className="mb-4">
          <label className="block text-[11px] font-medium text-muted-foreground mb-1.5">
            Favicon URL
          </label>
          <input
            type="text"
            value={localFavicon}
            onChange={(e) => setLocalFavicon(e.target.value)}
            placeholder="https://cdn.example.com/favicon.ico"
            className="w-full px-3 py-2 text-[12px] border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <Btn
          variant="primary"
          onClick={() => onUpdate({
            logo_url: localLogo || undefined,
            primary_color: localColor,
            favicon_url: localFavicon || undefined,
          })}
          disabled={isPending}
        >
          {isPending ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />}
          Save Branding
        </Btn>
      </div>
    </div>
  );
}

function PlatformSettingsSkeleton() {
  return (
    <div className="p-6 max-w-6xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-9 w-28" />
      </div>

      {/* Tabs Skeleton */}
      <div className="flex items-center gap-1 border-b border-border mb-6">
        {[1, 2, 3, 4].map(i => (
          <Skeleton key={i} className="h-10 w-24 mx-1" />
        ))}
      </div>

      {/* Content Skeleton */}
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-start gap-4">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-3 w-64" />
              </div>
              <Skeleton className="h-6 w-11 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

function PlatformSettingsContent() {
  const [activeTab, setActiveTab] = useState<TabType>("features");
  const [saveSuccess, setSaveSuccess] = useState(false);

  const {
    data: settings,
    isLoading,
    error,
    refetch,
  } = usePlatformSettings();

  const updateMutation = useUpdatePlatformSettings();

  const handleUpdate = async (payload: UpdateSettingsPayload) => {
    try {
      await updateMutation.mutateAsync(payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      log.error('Failed to update settings', { errorCode: String(err) });
    }
  };

  const handleFeatureToggle = (feature: keyof TenantSettings['features'], enabled: boolean) => {
    handleUpdate({
      features: { [feature]: enabled },
    });
  };

  const stats = useMemo(() => {
    if (!settings) return null;
    const enabledCount = Object.values(settings.features).filter(Boolean).length;
    const totalCount = Object.keys(settings.features).length;
    return {
      enabledCount,
      totalCount,
      utilizationPercent: Math.round((settings.limits.max_users / 100) * 100), // Assuming 100 is base
    };
  }, [settings]);

  if (isLoading) {
    return <PlatformSettingsSkeleton />;
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl">
        <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-8 h-8 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-[14px] font-semibold text-destructive-foreground mb-1">
                Failed to load platform settings
              </h3>
              <p className="text-[12px] text-destructive/80">
                {error instanceof Error ? error.message : "An unexpected error occurred"}
              </p>
              <button
                onClick={() => refetch()}
                className="mt-4 flex items-center gap-1.5 px-3 py-1.5 bg-destructive/20 text-destructive text-[12px] font-medium rounded-lg hover:bg-destructive/30 transition-colors"
              >
                <RefreshCw size={14} /> Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="p-6 max-w-6xl">
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-6">
          <h3 className="text-[14px] font-semibold text-amber-900 dark:text-amber-100">No Settings Available</h3>
          <p className="text-[12px] text-amber-700 dark:text-amber-300 mt-1">
            Platform settings could not be loaded. Please contact support.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Platform Settings"
          subtitle={`Configure tenant settings for ${settings.tenant_name}`}
        />
        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="flex items-center gap-1 text-[12px] text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 size={14} /> Saved
            </span>
          )}
          <Btn
            variant="primary"
            onClick={() => refetch()}
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? (
              <Loader2 size={14} className="animate-spin mr-1" />
            ) : (
              <RefreshCw size={14} className="mr-1" />
            )}
            Refresh
          </Btn>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Features Enabled", value: `${stats.enabledCount}/${stats.totalCount}`, icon: <Zap size={14} /> },
            { label: "Max Users", value: formatNumber(settings.limits.max_users), icon: <Users size={14} /> },
            { label: "Daily API Limit", value: formatNumber(settings.limits.max_api_calls_per_day), icon: <Database size={14} /> },
            { label: "Storage", value: `${settings.limits.storage_gb} GB`, icon: <Database size={14} /> },
          ].map(s => (
            <div key={s.label} className="bg-card border border-border rounded-xl px-4 py-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-muted-foreground">{s.icon}</span>
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                  {s.label}
                </span>
              </div>
              <p className="text-[22px] font-extrabold text-foreground">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border mb-6">
        {[
          { id: "features" as const, label: "Features", icon: <Zap size={13} /> },
          { id: "notifications" as const, label: "Notifications", icon: <Bell size={13} /> },
          { id: "security" as const, label: "Security", icon: <Shield size={13} /> },
          { id: "branding" as const, label: "Branding", icon: <Palette size={13} /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2.5 text-[12px] font-medium transition-colors relative flex items-center gap-2",
              activeTab === tab.id
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.icon} {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "features" && (
        <div className="space-y-3">
          {(Object.keys(settings.features) as Array<keyof TenantSettings['features']>).map(feature => (
            <FeatureToggle
              key={feature}
              feature={feature}
              enabled={settings.features[feature]}
              onToggle={(enabled) => handleFeatureToggle(feature, enabled)}
              disabled={updateMutation.isPending}
            />
          ))}
        </div>
      )}

      {activeTab === "notifications" && (
        <NotificationsPanel
          settings={settings.notifications}
          onUpdate={(updates) => handleUpdate({ notifications: updates })}
          isPending={updateMutation.isPending}
        />
      )}

      {activeTab === "security" && (
        <SecurityPanel
          settings={settings.security}
          onUpdate={(updates) => handleUpdate({ security: updates })}
          isPending={updateMutation.isPending}
        />
      )}

      {activeTab === "branding" && (
        <BrandingPanel
          branding={settings.branding}
          onUpdate={(updates) => handleUpdate({ branding: updates })}
          isPending={updateMutation.isPending}
        />
      )}
    </div>
  );
}

export default function PlatformSettings() {
  return (
    <ErrorBoundary>
      <PlatformSettingsContent />
    </ErrorBoundary>
  );
}
