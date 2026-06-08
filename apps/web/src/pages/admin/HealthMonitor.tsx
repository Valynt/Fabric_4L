/**
 * HealthMonitor — Admin Tier 3 Page
 *
 * System health monitoring dashboard:
 * - Real-time service status grid (L1-L6 layers)
 * - Health alerts and incidents
 * - Response time metrics
 * - Uptime statistics
 * - Auto-refresh every 30 seconds
 *
 * Connected to Layer 4 health endpoints
 */

import { useState, useMemo } from "react";
import {
  Activity, AlertCircle, CheckCircle2, Clock, RefreshCw,
  AlertTriangle, XCircle, Server, Database, Zap,
  Globe, Shield, Loader2, Bell, ExternalLink,
  ChevronDown, ChevronUp, Filter
} from "lucide-react";
import { Skeleton, ErrorBoundary } from "@/components";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import {
  useSystemHealth,
  useHealthAlerts,
  type ServiceStatus,
  type ServiceHealth,
  type HealthAlert,
} from "@/hooks";
import { PageHeader, Btn } from "@/components/ui/fabric";
import {
  AdminShell,
  AdminStatCard,
  AdminStatsRow,
  AdminFilterBar,
  AdminEmptyState,
  AdminErrorState,
} from "@/components/admin";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Types ────────────────────────────────────────────────────────────────────

type FilterStatus = "all" | ServiceStatus;
type AlertSeverity = "all" | "critical" | "warning" | "info";

// ── Styling Constants ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ServiceStatus, {
  label: string;
  color: string;
  bgColor: string;
  icon: React.ReactNode;
}> = {
  healthy: {
    label: "Healthy",
    color: "text-success",
    bgColor: "bg-success/10",
    icon: <CheckCircle2 size={16} />,
  },
  degraded: {
    label: "Degraded",
    color: "text-warning",
    bgColor: "bg-warning/10",
    icon: <AlertTriangle size={16} />,
  },
  unhealthy: {
    label: "Unhealthy",
    color: "text-destructive",
    bgColor: "bg-destructive/10",
    icon: <XCircle size={16} />,
  },
  unknown: {
    label: "Unknown",
    color: "text-muted-foreground",
    bgColor: "bg-muted",
    icon: <AlertCircle size={16} />,
  },
};

const ALERT_SEVERITY_CONFIG: Record<HealthAlert['severity'], {
  color: string;
  bgColor: string;
  icon: React.ReactNode;
}> = {
  critical: {
    color: "text-destructive",
    bgColor: "bg-destructive/10",
    icon: <XCircle size={14} />,
  },
  warning: {
    color: "text-warning",
    bgColor: "bg-warning/10",
    icon: <AlertTriangle size={14} />,
  },
  info: {
    color: "text-primary",
    bgColor: "bg-primary/10",
    icon: <Bell size={14} />,
  },
};

const SERVICE_ICONS: Record<string, React.ReactNode> = {
  "l1-ingestion": <Globe size={18} />,
  "l2-extraction": <Zap size={18} />,
  "l3-knowledge": <Database size={18} />,
  "l4-agents": <Server size={18} />,
  "l5-truth": <Shield size={18} />,
  "l6-benchmarks": <Activity size={18} />,
};

// ── Helper Functions ────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
}

// ── Sub-components ───────────────────────────────────────────────────────────

function ServiceCard({ service }: { service: ServiceHealth }) {
  const status = STATUS_CONFIG[service.status];
  const icon = SERVICE_ICONS[service.name] || <Server size={18} />;

  return (
    <div className="bg-card border border-border rounded-xl p-4 hover:border-primary transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center",
            status.bgColor, status.color
          )}>
            {icon}
          </div>
          <div>
            <h4 className="vf-text-body-m font-semibold text-foreground">
              {service.name.replace(/-/g, ' ').replace(/^l\d-/, 'L$1 ')}
            </h4>
            <p className="vf-text-caption text-muted-foreground">v{service.version}</p>
          </div>
        </div>
        <span className={cn(
          "inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full",
          status.bgColor, status.color
        )}>
          {status.icon} {status.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 vf-text-caption">
        <div className="bg-muted rounded-lg p-2">
          <span className="text-muted-foreground block">Uptime</span>
          <span className="text-foreground font-medium">
            {formatDuration(service.uptime_seconds)}
          </span>
        </div>
        <div className="bg-muted rounded-lg p-2">
          <span className="text-muted-foreground block">Response</span>
          <span className={cn(
            "font-medium",
            service.response_time_ms > 1000 ? "text-warning" : "text-foreground"
          )}>
            {service.response_time_ms}ms
          </span>
        </div>
      </div>

      {service.error_message && (
        <div className="mt-3 p-2 bg-destructive/10 border border-destructive/20 rounded-lg vf-text-caption text-destructive">
          {service.error_message}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between vf-text-micro text-muted-foreground">
        <span>Last check: {formatTimeAgo(service.last_check_at)}</span>
        <Btn variant="ghost" size="sm" className="h-auto px-0 py-0">
          Details <ExternalLink size={10} />
        </Btn>
      </div>
    </div>
  );
}

function AlertCard({ alert }: { alert: HealthAlert }) {
  const severity = ALERT_SEVERITY_CONFIG[alert.severity];

  return (
    <div className={cn(
      "flex items-start gap-3 p-3 rounded-lg border",
      alert.resolved_at
        ? "bg-muted border-border opacity-60"
        : severity.bgColor.replace('bg-', 'bg-opacity-50 bg-') + " " + severity.bgColor.replace('bg-', 'border-')
    )}>
      <span className={cn("shrink-0 mt-0.5", severity.color)}>
        {severity.icon}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="vf-text-body-s font-medium text-foreground">
            {alert.service_name}
          </span>
          <span className={cn(
            "vf-text-micro px-1.5 py-0.5 rounded font-semibold uppercase",
            severity.bgColor, severity.color
          )}>
            {alert.severity}
          </span>
        </div>
        <p className="vf-text-caption text-muted-foreground mt-0.5 truncate">
          {alert.message}
        </p>
        <div className="flex items-center gap-3 mt-1.5 vf-text-micro text-muted-foreground">
          <span>Started: {formatTimeAgo(alert.started_at)}</span>
          {alert.resolved_at && (
            <span className="text-success">
              Resolved: {formatTimeAgo(alert.resolved_at)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function HealthMonitorSkeleton() {
  return (
    <AdminShell title="System Health" subtitle="Loading...">
      <AdminStatsRow columns={4}>
        {[1, 2, 3, 4].map(i => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </AdminStatsRow>
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <Skeleton key={i} className="h-36 rounded-xl" />
        ))}
      </div>
    </AdminShell>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

function HealthMonitorContent() {
  const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity>("all");
  const [showResolved, setShowResolved] = useState(false);

  const {
    data: health,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth,
    dataUpdatedAt,
  } = useSystemHealth();

  const {
    data: alerts,
    isLoading: alertsLoading,
    error: alertsError,
    refetch: refetchAlerts,
  } = useHealthAlerts();

  const isLoading = healthLoading || alertsLoading;
  const error = healthError || alertsError;

  const filteredServices = useMemo(() => {
    if (!health?.services) return [];
    if (statusFilter === "all") return health.services;
    return health.services.filter(s => s.status === statusFilter);
  }, [health?.services, statusFilter]);

  const filteredAlerts = useMemo(() => {
    if (!alerts) return [];
    return alerts.filter(a => {
      if (!showResolved && a.resolved_at) return false;
      if (severityFilter !== "all" && a.severity !== severityFilter) return false;
      return true;
    });
  }, [alerts, severityFilter, showResolved]);

  const lastUpdated = useMemo(() => {
    if (!dataUpdatedAt) return "Never";
    return formatTimeAgo(new Date(dataUpdatedAt).toISOString());
  }, [dataUpdatedAt]);

  const handleRefresh = () => {
    refetchHealth();
    refetchAlerts();
  };

  if (isLoading) {
    return <HealthMonitorSkeleton />;
  }

  if (error) {
    return (
      <AdminShell
        title="System Health"
        subtitle="Monitor real-time status of all platform services"
      >
        <AdminErrorState
          title="Failed to load health data"
          description="An error occurred while loading system health information."
          error={error}
          onRetry={handleRefresh}
        />
      </AdminShell>
    );
  }

  if (!health) {
    return (
      <AdminShell
        title="System Health"
        subtitle="Monitor real-time status of all platform services"
      >
        <AdminEmptyState
          title="No Health Data"
          description="System health information is unavailable. Please check the API status."
          icon={Activity}
        />
      </AdminShell>
    );
  }

  const overallStatus = STATUS_CONFIG[health.overall_status];

  return (
    <AdminShell
      title="System Health"
      subtitle="Monitor real-time status of all platform services"
      actions={
        <div className="flex items-center gap-2">
          <span className="vf-text-caption text-muted-foreground">
            Updated {lastUpdated}
          </span>
          <Btn variant="outline" onClick={handleRefresh}>
            <RefreshCw size={14} className="mr-1" />
            Refresh
          </Btn>
        </div>
      }
    >
      {/* Overall Status Banner */}
      <div className={cn(
        "mb-6 p-4 rounded-xl border flex items-center gap-3",
        overallStatus.bgColor, overallStatus.bgColor.replace('bg-', 'border-')
      )}>
        <div className={cn("w-12 h-12 rounded-full flex items-center justify-center bg-card", overallStatus.color)}>
          {overallStatus.icon}
        </div>
        <div className="flex-1">
          <h3 className={cn("text-base font-bold", overallStatus.color)}>
            System {overallStatus.label}
          </h3>
          <p className="vf-text-body-s text-muted-foreground">
            {health.summary.healthy} of {health.summary.total} services operating normally
            {health.summary.degraded > 0 && ` • ${health.summary.degraded} degraded`}
            {health.summary.unhealthy > 0 && ` • ${health.summary.unhealthy} unhealthy`}
          </p>
        </div>
        <div className="text-right">
          <p className="vf-text-caption text-muted-foreground">Last check</p>
          <p className="vf-text-body-s font-medium text-foreground">
            {formatTimeAgo(health.checked_at)}
          </p>
        </div>
      </div>

      {/* Summary Grid */}
      <AdminStatsRow columns={4}>
        <AdminStatCard
          label="Healthy"
          value={health.summary.healthy}
          icon={<CheckCircle2 size={14} />}
          color="success"
        />
        <AdminStatCard
          label="Degraded"
          value={health.summary.degraded}
          icon={<AlertTriangle size={14} />}
          color="warning"
        />
        <AdminStatCard
          label="Unhealthy"
          value={health.summary.unhealthy}
          icon={<XCircle size={14} />}
          color="destructive"
        />
        <AdminStatCard
          label="Unknown"
          value={health.summary.unknown}
          icon={<AlertCircle size={14} />}
          color="default"
        />
      </AdminStatsRow>

      {/* Services Section */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="vf-text-body-l font-semibold text-foreground">Services</h3>
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-muted-foreground" />
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as FilterStatus)}>
              <SelectTrigger className="w-full vf-text-caption">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="healthy">Healthy</SelectItem>
                <SelectItem value="degraded">Degraded</SelectItem>
                <SelectItem value="unhealthy">Unhealthy</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {filteredServices.map(service => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>

        {filteredServices.length === 0 && (
          <AdminEmptyState
            icon={Server}
            title="No services match"
            description="No services match the selected filter."
          />
        )}
      </div>

      {/* Alerts Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="vf-text-body-l font-semibold text-foreground">
            Active Alerts {filteredAlerts.length > 0 && `(${filteredAlerts.length})`}
          </h3>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 vf-text-caption text-muted-foreground cursor-pointer">
              <Checkbox
                checked={showResolved}
                onCheckedChange={(checked) => setShowResolved(Boolean(checked))}
              />
              Show resolved
            </label>
            <Select value={severityFilter} onValueChange={(value) => setSeverityFilter(value as AlertSeverity)}>
              <SelectTrigger className="w-full vf-text-caption">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          {filteredAlerts.map(alert => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>

        {filteredAlerts.length === 0 && (
          <AdminEmptyState
            icon={Bell}
            title={showResolved ? "No alerts found" : "No active alerts"}
            description={showResolved ? "There are no alerts in the selected range." : "All systems are operating normally."}
          />
        )}
      </div>
    </AdminShell>
  );
}

export default function HealthMonitor() {
  return (
    <ErrorBoundary>
      <HealthMonitorContent />
    </ErrorBoundary>
  );
}
