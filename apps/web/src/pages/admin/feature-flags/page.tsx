/**
 * Fabric_4L Admin — Feature Flag Management Page
 * v1.2.0
 *
 * Provides:
 *   • Table view of all feature flags (key, status, default, overrides)
 *   • Toggle flag default value (with confirmation modal)
 *   • Edit override rules (tenant tier, percentage rollout)
 *   • View audit log for each flag
 *   • Kill switch arm/disarm controls
 *
 * Uses shadcn/ui: Table, Switch, Dialog, Badge, Button, Card, Input, Select.
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";

// ── shadcn/ui components (assumed available in the host app) ──
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";

// ── Types (mirrored from SDK) ─────────────────────────────────

interface FlagRule {
  tenantTier?: "shared" | "dedicated" | "enterprise";
  tenantIds?: string[];
  percentage?: number;
  userSegments?: string[];
}

interface FeatureFlag {
  id: number;
  flagKey: string;
  description: string;
  defaultValue: boolean;
  createdAt: string;
  updatedAt: string;
  overrideCount: number;
  rules: FlagRule[];
}

interface AuditEvent {
  id: number;
  flagKey: string;
  actor: string;
  action: string;
  oldValue: Record<string, unknown> | null;
  newValue: Record<string, unknown> | null;
  timestamp: string;
}

interface KillSwitchStatus {
  flagKey: string;
  killed: boolean;
  armedAt?: string;
  expiresAt?: string;
  reason?: string;
}

// ── API helpers ───────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("admin_token"); // host app manages auth
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Sub-components ────────────────────────────────────────────

function StatusBadge({ active }: { active: boolean }) {
  return (
    <Badge variant={active ? "default" : "secondary"}>
      {active ? "Active" : "Inactive"}
    </Badge>
  );
}

function KillSwitchBadge({ killed }: { killed: boolean }) {
  return killed ? (
    <Badge variant="destructive">KILLED</Badge>
  ) : (
    <Badge variant="outline">Nominal</Badge>
  );
}

/** Confirmation dialog for destructive actions */
function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  confirmLabel = "Confirm",
  destructive = false,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  confirmLabel?: string;
  destructive?: boolean;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Audit log viewer dialog */
function AuditLogDialog({
  flag,
  open,
  onOpenChange,
}: {
  flag: FeatureFlag | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!flag || !open) return;
    setLoading(true);
    api<AuditEvent[]>(`/api/v1/admin/feature-flags/${flag.flagKey}/audit?limit=50`)
      .then(setEvents)
      .catch((err) => {
        toast({
          title: "Failed to load audit log",
          description: err.message,
          variant: "destructive",
        });
      })
      .finally(() => setLoading(false));
  }, [flag, open]);

  if (!flag) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Audit Log: {flag.flagKey}</DialogTitle>
          <DialogDescription>
            Recent changes to this feature flag
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <p className="text-muted-foreground">Loading...</p>
        ) : events.length === 0 ? (
          <p className="text-muted-foreground">No audit events found.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[140px]">Timestamp</TableHead>
                <TableHead className="w-[100px]">Action</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-mono text-xs">
                    {new Date(e.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <AuditActionBadge action={e.action} />
                  </TableCell>
                  <TableCell className="text-sm">{e.actor}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[300px] truncate">
                    {e.newValue
                      ? JSON.stringify(e.newValue).slice(0, 100)
                      : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
    </Dialog>
  );
}

function AuditActionBadge({ action }: { action: string }) {
  const variantMap: Record<string, "default" | "destructive" | "secondary" | "outline"> = {
    created: "default",
    updated: "secondary",
    toggled: "secondary",
    deleted: "destructive",
    override_added: "default",
    override_removed: "outline",
    kill_switch_activated: "destructive",
    kill_switch_expired: "outline",
  };
  return (
    <Badge variant={variantMap[action] ?? "outline"} className="text-[10px]">
      {action}
    </Badge>
  );
}

/** Edit flag dialog — rules and metadata */
function EditFlagDialog({
  flag,
  open,
  onOpenChange,
  onSaved,
}: {
  flag: FeatureFlag | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSaved: () => void;
}) {
  const [description, setDescription] = useState("");
  const [defaultValue, setDefaultValue] = useState(false);
  const [rules, setRules] = useState<FlagRule[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (flag) {
      setDescription(flag.description);
      setDefaultValue(flag.defaultValue);
      setRules(flag.rules.length > 0 ? [...flag.rules] : [{ enabled: true as unknown as undefined }]);
    }
  }, [flag]);

  const addRule = () =>
    setRules((prev) => [...prev, {}]);

  const updateRule = (idx: number, patch: Partial<FlagRule>) =>
    setRules((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, ...patch } : r))
    );

  const removeRule = (idx: number) =>
    setRules((prev) => prev.filter((_, i) => i !== idx));

  const handleSave = async () => {
    if (!flag) return;
    setSaving(true);
    try {
      await api(`/api/v1/admin/feature-flags/${flag.flagKey}`, {
        method: "PUT",
        body: JSON.stringify({
          description,
          defaultValue,
          rules: rules.map((r) => ({
            tenantTier: r.tenantTier,
            tenantIds: r.tenantIds?.filter(Boolean),
            percentage: r.percentage,
            userSegments: r.userSegments,
          })),
        }),
      });
      toast({ title: "Flag updated successfully" });
      onSaved();
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast({ title: "Update failed", description: msg, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (!flag) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Flag: {flag.flagKey}</DialogTitle>
          <DialogDescription>
            Modify default value and targeting rules
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="ff-desc">Description</Label>
            <Textarea
              id="ff-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* Default value */}
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <p className="font-medium">Default Value</p>
              <p className="text-sm text-muted-foreground">
                Fail-safe: new flags should default to OFF
              </p>
            </div>
            <Switch
              checked={defaultValue}
              onCheckedChange={setDefaultValue}
            />
          </div>

          {/* Rules */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Targeting Rules</Label>
              <Button size="sm" variant="outline" onClick={addRule}>
                + Add Rule
              </Button>
            </div>

            {rules.map((rule, idx) => (
              <Card key={idx} className="p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">
                    Rule {idx + 1}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-destructive"
                    onClick={() => removeRule(idx)}
                  >
                    Remove
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Tenant Tier</Label>
                    <Select
                      value={rule.tenantTier ?? ""}
                      onValueChange={(v) =>
                        updateRule(idx, {
                          tenantTier: v as FlagRule["tenantTier"],
                        })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Any tier" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Any tier</SelectItem>
                        <SelectItem value="shared">Shared</SelectItem>
                        <SelectItem value="dedicated">Dedicated</SelectItem>
                        <SelectItem value="enterprise">Enterprise</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-xs">Percentage Rollout</Label>
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      value={rule.percentage ?? ""}
                      onChange={(e) =>
                        updateRule(idx, {
                          percentage: e.target.value
                            ? parseInt(e.target.value, 10)
                            : undefined,
                        })
                      }
                      placeholder="0–100"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-xs">Tenant IDs (comma-separated)</Label>
                  <Input
                    value={rule.tenantIds?.join(", ") ?? ""}
                    onChange={(e) =>
                      updateRule(idx, {
                        tenantIds: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="tenant-42, tenant-99"
                  />
                </div>
              </Card>
            ))}

            {rules.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No rules — flag will use the default value for all tenants.
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Kill switch arm dialog */
function KillSwitchDialog({
  flag,
  open,
  onOpenChange,
  onAction,
}: {
  flag: FeatureFlag | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onAction: () => void;
}) {
  const [reason, setReason] = useState("");
  const [duration, setDuration] = useState("14400");
  const [loading, setLoading] = useState(false);

  const handleArm = async () => {
    if (!flag) return;
    if (reason.length < 5) {
      toast({
        title: "Reason too short",
        description: "Must be at least 5 characters",
        variant: "destructive",
      });
      return;
    }
    setLoading(true);
    try {
      await api(`/api/v1/admin/feature-flags/${flag.flagKey}/kill`, {
        method: "POST",
        body: JSON.stringify({
          reason,
          duration_seconds: parseInt(duration, 10),
        }),
      });
      toast({
        title: "Kill switch activated",
        description: `${flag.flagKey} is now disabled globally.`,
        variant: "destructive",
      });
      onAction();
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast({ title: "Failed to arm kill switch", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleDisarm = async () => {
    if (!flag) return;
    setLoading(true);
    try {
      await api(`/api/v1/admin/feature-flags/${flag.flagKey}/kill`, {
        method: "DELETE",
      });
      toast({ title: "Kill switch disarmed" });
      onAction();
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast({ title: "Failed to disarm", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  if (!flag) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-destructive">Kill Switch</DialogTitle>
          <DialogDescription>
            Emergency controls for <code>{flag.flagKey}</code>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-sm font-medium text-destructive">
              Warning: This immediately disables the feature for ALL tenants.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ks-reason">Reason *</Label>
            <Textarea
              id="ks-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Memory leak causing OOMKills in production"
              rows={2}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="ks-duration">Duration (seconds)</Label>
            <Select value={duration} onValueChange={setDuration}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3600">1 hour (3,600s)</SelectItem>
                <SelectItem value="14400">4 hours (14,400s) — default</SelectItem>
                <SelectItem value="28800">8 hours (28,800s)</SelectItem>
                <SelectItem value="86400">24 hours (86,400s) — max</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleArm}
            disabled={loading || reason.length < 5}
          >
            {loading ? "Arming..." : "ARM Kill Switch"}
          </Button>
        </DialogFooter>

        <div className="border-t pt-4 mt-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={handleDisarm}
            disabled={loading}
          >
            Disarm (Reset)
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Main page component ───────────────────────────────────────

export default function FeatureFlagsAdminPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    flag: FeatureFlag | null;
    newValue: boolean;
  }>({ open: false, flag: null, newValue: false });

  const [auditFlag, setAuditFlag] = useState<FeatureFlag | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);

  const [editFlag, setEditFlag] = useState<FeatureFlag | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  const [killFlag, setKillFlag] = useState<FeatureFlag | null>(null);
  const [killOpen, setKillOpen] = useState(false);

  // Kill switch status cache
  const [killStatusMap, setKillStatusMap] = useState<Record<string, KillSwitchStatus>>({});

  const loadFlags = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api<FeatureFlag[]>("/api/v1/admin/feature-flags");
      setFlags(data);

      // Fetch kill switch status for each flag
      const statusEntries = await Promise.all(
        data.map(async (f) => {
          try {
            const status = await api<KillSwitchStatus>(
              `/api/v1/admin/feature-flags/${f.flagKey}/kill`
            );
            return [f.flagKey, status] as const;
          } catch {
            return [f.flagKey, { flagKey: f.flagKey, killed: false }] as const;
          }
        })
      );
      setKillStatusMap(Object.fromEntries(statusEntries));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast({ title: "Failed to load flags", description: msg, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFlags();
    // Refresh every 30 seconds
    const interval = setInterval(loadFlags, 30_000);
    return () => clearInterval(interval);
  }, [loadFlags]);

  const filteredFlags = useMemo(
    () =>
      flags.filter(
        (f) =>
          f.flagKey.toLowerCase().includes(search.toLowerCase()) ||
          f.description.toLowerCase().includes(search.toLowerCase())
      ),
    [flags, search]
  );

  const handleToggleDefault = async (flag: FeatureFlag, newValue: boolean) => {
    try {
      await api(`/api/v1/admin/feature-flags/${flag.flagKey}`, {
        method: "PUT",
        body: JSON.stringify({ defaultValue: newValue }),
      });
      toast({ title: `${flag.flagKey} is now ${newValue ? "ON" : "OFF"}` });
      loadFlags();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast({ title: "Toggle failed", description: msg, variant: "destructive" });
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Feature Flags</h1>
          <p className="text-muted-foreground mt-1">
            Manage feature toggles, rollouts, and kill switches
          </p>
        </div>
        <Button onClick={loadFlags} variant="outline" disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Flags</CardDescription>
            <CardTitle className="text-2xl">{flags.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-2xl">
              {flags.filter((f) => f.defaultValue).length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Overrides</CardDescription>
            <CardTitle className="text-2xl">
              {flags.reduce((sum, f) => sum + f.overrideCount, 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Kill Switches</CardDescription>
            <CardTitle className="text-2xl text-destructive">
              {Object.values(killStatusMap).filter((s) => s.killed).length}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Search */}
      <Input
        placeholder="Search flags by key or description..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md"
      />

      {/* Flags table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">Flag Key</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-[100px]">Default</TableHead>
                <TableHead className="w-[100px]">Overrides</TableHead>
                <TableHead className="w-[110px]">Kill Switch</TableHead>
                <TableHead className="w-[120px]">Status</TableHead>
                <TableHead className="w-[250px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredFlags.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center text-muted-foreground py-8"
                  >
                    {loading ? "Loading..." : "No flags found"}
                  </TableCell>
                </TableRow>
              ) : (
                filteredFlags.map((flag) => {
                  const ks = killStatusMap[flag.flagKey];
                  const isKilled = ks?.killed ?? false;

                  return (
                    <TableRow key={flag.id}>
                      <TableCell className="font-mono text-sm">
                        {flag.flagKey}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-[250px] truncate">
                        {flag.description}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={flag.defaultValue}
                          onCheckedChange={(v) =>
                            setConfirmDialog({
                              open: true,
                              flag,
                              newValue: v,
                            })
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{flag.overrideCount}</Badge>
                      </TableCell>
                      <TableCell>
                        <KillSwitchBadge killed={isKilled} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge active={flag.defaultValue && !isKilled} />
                      </TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setEditFlag(flag);
                            setEditOpen(true);
                          }}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setAuditFlag(flag);
                            setAuditOpen(true);
                          }}
                        >
                          Audit
                        </Button>
                        <Button
                          size="sm"
                          variant={isKilled ? "outline" : "destructive"}
                          onClick={() => {
                            setKillFlag(flag);
                            setKillOpen(true);
                          }}
                        >
                          {isKilled ? "Disarm" : "Kill"}
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Confirmation dialog for toggle */}
      <ConfirmDialog
        open={confirmDialog.open}
        onOpenChange={(v) => setConfirmDialog((p) => ({ ...p, open: v }))}
        title="Toggle Feature Flag"
        description={`Are you sure you want to turn ${
          confirmDialog.flag?.flagKey ?? ""
        } ${confirmDialog.newValue ? "ON" : "OFF"}? This affects all tenants without override rules.`}
        onConfirm={() => {
          if (confirmDialog.flag) {
            handleToggleDefault(confirmDialog.flag, confirmDialog.newValue);
          }
        }}
        confirmLabel="Toggle"
      />

      {/* Audit log dialog */}
      <AuditLogDialog
        flag={auditFlag}
        open={auditOpen}
        onOpenChange={setAuditOpen}
      />

      {/* Edit flag dialog */}
      <EditFlagDialog
        flag={editFlag}
        open={editOpen}
        onOpenChange={setEditOpen}
        onSaved={loadFlags}
      />

      {/* Kill switch dialog */}
      <KillSwitchDialog
        flag={killFlag}
        open={killOpen}
        onOpenChange={setKillOpen}
        onAction={loadFlags}
      />
    </div>
  );
}
