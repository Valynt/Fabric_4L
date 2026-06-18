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

import { EmptyState, ErrorState } from "@/components/states";
import { useState, useMemo } from "react";
import {
  Settings, Bell, Shield, Zap, Users, Database,
  Palette, Save, Loader2, AlertCircle, RefreshCw,
  CheckCircle2, ExternalLink, Info, Trash2
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import ErrorBoundary from "@/components/ErrorBoundary";
import { cn } from "@/lib/utils";
import {
  usePlatformSettings,
  useUpdatePlatformSettings,
  type TenantSettings,
  type UpdateSettingsPayload} from "@/hooks/usePlatformSettings";
import { createFeatureLogger } from "@/lib/telemetry";
import { Input } from "@/components/ui/input";
import { Btn } from "@/components/ui/fabric";
import {
  AdminShell,
  AdminTabs,
  AdminTabPanel,
  AdminStatCard,
  AdminStatsRow,
  AdminConfirmDialog,
} from "@/components/admin";

const log = createFeatureLogger('PlatformSettings');

// ── Types ────────────────────────────────────────────────────────────────────

type TabType = "features" | "notifications" | "security" | "branding";

// ── Styling Constants ───────────────────────────────────────────────────────────

const FEATURE_DESCRIPTIONS: Record<keyof TenantSettings['features'], string> = {
  advanced_analytics: "Enable advanced data visualization and custom dashboards",
  custom_integrations: "Allow custom API integrations and webhooks",
  ai_assistant: "Enable AI-powered formula suggestions and business case insights",
  audit_trail: "Track all user actions with detailed audit logs"};

const FEATURE_ICONS: Record<keyof TenantSettings['features'], React.ReactNode> = {
  advanced_analytics: <Database size={16} />,
  custom_integrations: <ExternalLink size={16} />,
  ai_assistant: <Zap size={16} />,
  audit_trail: <Info size={16} />};

// ── Helper Functions ───────────────────────────────────────────────────────────

function formatNumber(num: number): string {
  return num.toLocaleString();
}

// ── Sub-components ───────────────────────────────────────────────────────────

function FeatureToggle({
  feature,
  enabled,
  onToggle,
  disabled}: {
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
          <h4 className="vf-text-body-m font-semibold text-foreground capitalize">
            {feature.replace('_', ' ')}
          </h4>
          <p className="vf-text-caption text-muted-foreground mt-0.5">
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
  isPending}: {
  settings: TenantSettings['notifications'];
  onUpdate: (updates: Partial<TenantSettings['notifications']>) => void;
  isPending: boolean;
}) {
  const [localWebhook, setLocalWebhook] = useState(settings.webhook_url || '');
  const [localSlack, setLocalSlack] = useState(settings.slack_webhook || '');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Bell size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Email Alerts</h4>
            <p className="vf-text-caption text-muted-foreground">Receive notifications via email</p>
          </div>
        </div>
        <Switch
          checked={settings.email_alerts}
          onCheckedChange={(checked) => onUpdate({ email_alerts: checked })}
          disabled={isPending}
        />
      </div>

      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <ExternalLink size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Slack Integration</h4>
            <p className="vf-text-caption text-muted-foreground">Post alerts to Slack channel</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Input
            type="text"
            value={localSlack}
            onChange={(e) => setLocalSlack(e.target.value)}
            placeholder="https://hooks.slack.com/services/..."
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

      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <ExternalLink size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Custom Webhook</h4>
            <p className="vf-text-caption text-muted-foreground">POST events to custom URL</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Input
            type="text"
            value={localWebhook}
            onChange={(e) => setLocalWebhook(e.target.value)}
            placeholder="https://your-domain.com/webhook"
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
  isPending}: {
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
      <div className="flex items-center justify-between p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-success/10 text-success flex items-center justify-center shrink-0">
            <Shield size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Require Two-Factor Auth</h4>
            <p className="vf-text-caption text-muted-foreground">Mandate 2FA for all tenant users</p>
          </div>
        </div>
        <Switch
          checked={settings.require_2fa}
          onCheckedChange={(checked) => onUpdate({ require_2fa: checked })}
          disabled={isPending}
        />
      </div>

      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-warning/10 text-warning flex items-center justify-center shrink-0">
            <Users size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Session Timeout</h4>
            <p className="vf-text-caption text-muted-foreground">Auto-logout after inactivity</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Input
            type="range"
            min={15}
            max={480}
            step={15}
            value={localTimeout}
            onChange={(e) => setLocalTimeout(parseInt(e.target.value))}
            className="flex-1"
          />
          <span className="vf-text-body-m font-medium text-foreground w-24">
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

      <div className="p-4 bg-card border border-border rounded-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Shield size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">IP Allowlist</h4>
            <p className="vf-text-caption text-muted-foreground">Restrict access to specific IPs (empty = allow all)</p>
          </div>
        </div>
        <div className="flex gap-2 mb-3">
          <Input
            type="text"
            value={newIp}
            onChange={(e) => setNewIp(e.target.value)}
            placeholder="192.168.1.1 or 10.0.0.0/8"
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
                className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary vf-text-caption rounded-lg"
              >
                {ip}
                <Btn
                  variant="ghost"
                  size="icon"
                  className="h-4 w-4"
                  onClick={() => removeIp(ip)}
                  disabled={isPending}
                  aria-label={`Remove ${ip}`}
                >
                  ×
                </Btn>
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
  isPending}: {
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
          <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Palette size={16} />
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">Custom Branding</h4>
            <p className="vf-text-caption text-muted-foreground">Customize your tenant appearance</p>
          </div>
        </div>

        <div className="mb-4">
          <label className="block vf-text-caption font-medium text-muted-foreground mb-1.5">
            Logo URL
          </label>
          <Input
            type="text"
            value={localLogo}
            onChange={(e) => setLocalLogo(e.target.value)}
            placeholder="https://cdn.example.com/logo.png"
          />
        </div>

        <div className="mb-4">
          <label className="block vf-text-caption font-medium text-muted-foreground mb-1.5">
            Primary Color
          </label>
          <div className="flex items-center gap-3">
            <Input
              type="color"
              value={localColor}
              onChange={(e) => setLocalColor(e.target.value)}
              className="w-10 h-10 rounded-lg border border-border cursor-pointer p-0.5"
            />
            <Input
              type="text"
              value={localColor}
              onChange={(e) => setLocalColor(e.target.value)}
              className="flex-1 font-mono"
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block vf-text-caption font-medium text-muted-foreground mb-1.5">
            Favicon URL
          </label>
          <Input
            type="text"
            value={localFavicon}
            onChange={(e) => setLocalFavicon(e.target.value)}
            placeholder="https://cdn.example.com/favicon.ico"
          />
        </div>

        <Btn
          variant="primary"
          onClick={() => onUpdate({
            logo_url: localLogo || undefined,
            primary_color: localColor,
            favicon_url: localFavicon || undefined})}
          disabled={isPending}
        >
          {isPending ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />}
          Save Branding
        </Btn>
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
    refetch} = usePlatformSettings();

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
      features: { [feature]: enabled }});
  };

  const stats = useMemo(() => {
    if (!settings) return null;
    const enabledCount = Object.values(settings.features).filter(Boolean).length;
    const totalCount = Object.keys(settings.features).length;
    return {
      enabledCount,
      totalCount,
      utilizationPercent: Math.round((settings.limits.max_users / 100) * 100)};
  }, [settings]);

  if (isLoading) {
    return (
      <AdminShell title="Platform Settings" subtitle="Loading configuration...">
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-card border border-border rounded-xl p-4 animate-pulse">
              <div className="h-4 bg-muted rounded w-1/3 mb-2" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </div>
          ))}
        </div>
      </AdminShell>
    );
  }

  if (error) {
    return (
      <AdminShell title="Platform Settings" subtitle="Tenant configuration">
        <ErrorState
          title="Failed to load platform settings"
          description="Ensure you have admin access and the API is available."
          error={error}
          onRetry={refetch}
        />
      </AdminShell>
    );
  }

  if (!settings) {
    return (
      <AdminShell title="Platform Settings" subtitle="Tenant configuration">
        <EmptyState
          title="No Settings Available"
          description="Platform settings could not be loaded. Please contact support."
          icon={Settings}
        />
      </AdminShell>
    );
  }

  return (
    <AdminShell
      title="Platform Settings"
      subtitle={`Configure tenant settings for ${settings.tenant_name}`}
      fullWidth
      actions={
        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="flex items-center gap-1 vf-text-body-s text-success">
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
      }
      tabs={
        <AdminTabs
          tabs={[
            { id: "features", label: "Features", icon: <Zap size={13} /> },
            { id: "notifications", label: "Notifications", icon: <Bell size={13} /> },
            { id: "security", label: "Security", icon: <Shield size={13} /> },
            { id: "branding", label: "Branding", icon: <Palette size={13} /> },
          ]}
          activeTab={activeTab}
          onChange={(tabId) => setActiveTab(tabId as TabType)}
        />
      }
    >
      {stats && (
        <AdminStatsRow columns={4}>
          <AdminStatCard label="Features Enabled" value={`${stats.enabledCount}/${stats.totalCount}`} icon={<Zap size={14} />} />
          <AdminStatCard label="Max Users" value={formatNumber(settings.limits.max_users)} icon={<Users size={14} />} />
          <AdminStatCard label="Daily API Limit" value={formatNumber(settings.limits.max_api_calls_per_day)} icon={<Database size={14} />} />
          <AdminStatCard label="Storage" value={`${settings.limits.storage_gb} GB`} icon={<Database size={14} />} />
        </AdminStatsRow>
      )}

      <AdminTabPanel tabId="features" activeTab={activeTab}>
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
      </AdminTabPanel>

      <AdminTabPanel tabId="notifications" activeTab={activeTab}>
        <NotificationsPanel
          settings={settings.notifications}
          onUpdate={(updates) => handleUpdate({ notifications: updates })}
          isPending={updateMutation.isPending}
        />
      </AdminTabPanel>

      <AdminTabPanel tabId="security" activeTab={activeTab}>
        <SecurityPanel
          settings={settings.security}
          onUpdate={(updates) => handleUpdate({ security: updates })}
          isPending={updateMutation.isPending}
        />
      </AdminTabPanel>

      <AdminTabPanel tabId="branding" activeTab={activeTab}>
        <BrandingPanel
          branding={settings.branding}
          onUpdate={(updates) => handleUpdate({ branding: updates })}
          isPending={updateMutation.isPending}
        />
      </AdminTabPanel>
    </AdminShell>
  );
}

export default function PlatformSettings() {
  return (
    <ErrorBoundary>
      <PlatformSettingsContent />
    </ErrorBoundary>
  );
}
