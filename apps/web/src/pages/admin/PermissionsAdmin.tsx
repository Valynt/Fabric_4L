/**
 * PermissionsAdmin — Admin Tier 3 Page
 *
 * Tenant governance and RBAC management:
 * - Users (invite, role, deactivate)
 * - API Keys (create, revoke)
 *
 * Features:
 * - User listing with role badges
 * - API key listing with enable/revoke
 * - Connected to L4 governance endpoints
 */

import { useState, useMemo, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  Users, Key, Plus, Search, Shield, UserPlus,
  CheckCircle2, Clock, AlertCircle, RefreshCw,
  Trash2, Eye, EyeOff,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/formatters";
import ErrorBoundary from "@/components/ErrorBoundary";
import { cn } from "@/lib/utils";
import {
  useUsers,
  useApiKeys,
  useRevokeApiKey,
  useInviteUser,
  type User,
  type ApiKey,
} from "@/hooks/useGovernance";
import { PageHeader, Btn } from "@/components/ui/fabric";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ── Styling Constants ───────────────────────────────────────────────────────────

const ROLE_STYLES: Record<string, string> = {
  super_admin:  "bg-destructive/10 text-destructive border-destructive/20",
  tenant_admin: "bg-warning/10 text-warning border-warning/20",
  member:       "bg-primary/10 text-primary border-primary/20",
  viewer:       "bg-muted text-muted-foreground border-border",
};

const STATUS_STYLES: Record<string, string> = {
  active:      "bg-success/10 text-success border-success/20",
  invited:     "bg-warning/10 text-warning border-warning/20",
  deactivated: "bg-destructive/10 text-destructive border-destructive/20",
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${ROLE_STYLES[role] || ROLE_STYLES.viewer}`}>
      <Shield size={10} /> {role.replace("_", " ")}
    </span>
  );
}

function StatusChip({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[status] || STATUS_STYLES.deactivated}`}>
      {status}
    </span>
  );
}


function PermissionsSkeleton() {
  return (
    <PageShell fullWidth>
      <div className="max-w-6xl">
        <div className="flex items-start justify-between mb-6">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-9 w-32" />
        </div>
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="px-4 py-4 border-b border-border flex gap-4">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      </div>
    </PageShell>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

type TabType = "users" | "api-keys";

function getTabFromPath(path: string): TabType {
  if (path.startsWith("/settings/access/keys") || path.startsWith("/settings/team/api-keys")) {
    return "api-keys";
  }

  if (
    path.startsWith("/settings/access/roles") ||
    path.startsWith("/settings/access/teams") ||
    path.startsWith("/settings/team")
  ) {
    return "users";
  }

  return "users";
}

function PermissionsContent() {
  const { pathname: location } = useLocation();
  const [activeTab, setActiveTab] = useState<TabType>(() => getTabFromPath(location));
  const [search, setSearch] = useState("");

  useEffect(() => {
    setActiveTab(getTabFromPath(location));
  }, [location]);

  const {
    data: users = [],
    isLoading: usersLoading,
    error: usersError,
    refetch: refetchUsers,
  } = useUsers();

  const {
    data: apiKeys = [],
    isLoading: keysLoading,
    error: keysError,
    refetch: refetchKeys,
  } = useApiKeys();

  const revokeMutation = useRevokeApiKey();
  const inviteMutation = useInviteUser();
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const handleInvite = async () => {
    if (!inviteEmail) return;
    try {
      await inviteMutation.mutateAsync({ email: inviteEmail, role: inviteRole });
      setShowInvite(false);
      setInviteEmail("");
      setInviteRole("member");
      refetchUsers();
    } catch (e) { /* error shown via mutation state */ }
  };

  const isLoading = usersLoading || keysLoading;
  const error = usersError || keysError;

  const filteredUsers = useMemo(() =>
    search
      ? users.filter(u =>
          u.email.toLowerCase().includes(search.toLowerCase()) ||
          (u.display_name || "").toLowerCase().includes(search.toLowerCase())
        )
      : users,
    [users, search]
  );

  const filteredKeys = useMemo(() =>
    search
      ? apiKeys.filter(k => k.name.toLowerCase().includes(search.toLowerCase()))
      : apiKeys,
    [apiKeys, search]
  );

  if (isLoading) return <PermissionsSkeleton />;

  if (error) {
    return (
      <PageShell fullWidth>
      <div className="max-w-6xl">
        <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-8 h-8 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-[14px] font-semibold text-destructive-foreground mb-1">Failed to load permissions data</h3>
              <p className="text-[12px] text-destructive/80">
                {error instanceof Error ? error.message : "An unexpected error occurred"}
              </p>
              <button
                onClick={() => { refetchUsers(); refetchKeys(); }}
                className="mt-4 flex items-center gap-1.5 px-3 py-1.5 bg-destructive/20 text-destructive text-[12px] font-medium rounded-lg hover:bg-destructive/30 transition-colors"
              >
                <RefreshCw size={14} /> Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
    );
  }

  return (
    <PageShell fullWidth>
      <div className="max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <PageHeader
          title="Permissions & Access"
          subtitle="Manage users, roles, and API keys for your tenant."
        />
        <Btn variant="primary" onClick={() => activeTab === "users" ? setShowInvite(true) : null}>
          {activeTab === "users"
            ? <><UserPlus size={13} className="mr-1" /> Invite User</>
            : <><Plus size={13} className="mr-1" /> New API Key</>
          }
        </Btn>
      </div>

      {/* Invite User Dialog */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
          <div className="bg-card rounded-xl shadow-xl p-6 w-[400px]">
            <h3 className="text-[15px] font-bold text-foreground mb-4">Invite User</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">Email</label>
                <input value={inviteEmail} onChange={e => setInviteEmail(e.target.value)}
                  placeholder="user@company.com" className="w-full text-[12px] border border-border rounded-lg px-3 py-2 outline-none focus:border-primary" />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">Role</label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger className="w-full vf-text-body-s">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {inviteMutation.error && (
                <p className="text-[11px] text-destructive">{inviteMutation.error instanceof Error ? inviteMutation.error.message : "Invite failed"}</p>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <Btn variant="ghost" onClick={() => setShowInvite(false)}>Cancel</Btn>
              <Btn variant="primary" onClick={handleInvite} disabled={!inviteEmail || inviteMutation.isPending}>
                {inviteMutation.isPending ? "Sending…" : "Send Invite"}
              </Btn>
            </div>
          </div>
        </div>
      )}
      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border mb-4">
        {[
          { id: "users" as const, label: "Users", count: users.length, icon: <Users size={13} /> },
          { id: "api-keys" as const, label: "API Keys", count: apiKeys.length, icon: <Key size={13} /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2.5 text-[12px] font-medium transition-colors relative",
              activeTab === tab.id
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <span className="flex items-center gap-2">
              {tab.icon} {tab.label}
              <span className={cn(
                "px-1.5 py-0.5 rounded text-[10px]",
                activeTab === tab.id ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
              )}>
                {tab.count}
              </span>
            </span>
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full" />
            )}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 max-w-sm mb-4">
        <Search size={12} className="text-muted-foreground shrink-0" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={activeTab === "users" ? "Search users..." : "Search API keys..."}
          className="flex-1 text-[12px] bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
        />
      </div>

      {activeTab === "users" ? (
        /* Users Table */
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border bg-muted">
                {["User", "Role", "Status", "Created", "Last Login", ""].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredUsers.map(u => (
                <tr key={u.id} className="hover:bg-muted transition-colors group">
                  <td className="px-4 py-3">
                    <div>
                      <span className="font-medium text-foreground block">{u.display_name || u.email}</span>
                      {u.display_name && <span className="text-[10px] text-muted-foreground">{u.email}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
                  <td className="px-4 py-3"><StatusChip status={u.status} /></td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(u.last_login_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground" title="View">
                        <Eye size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredUsers.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-[12px]">
              <Users size={32} className="mx-auto mb-3 text-muted-foreground/50" />
              No users match your search.
            </div>
          )}
        </div>
      ) : (
        /* API Keys Table */
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border bg-muted">
                {["Key Name", "Prefix", "Enabled", "Created", "Last Used", ""].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredKeys.map(k => (
                <tr key={k.id} className="hover:bg-muted transition-colors group">
                  <td className="px-4 py-3 font-medium text-foreground">{k.name}</td>
                  <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">{k.prefix}•••</td>
                  <td className="px-4 py-3">
                    {k.is_enabled
                      ? <span className="inline-flex items-center gap-1 text-success"><CheckCircle2 size={12} /> Active</span>
                      : <span className="inline-flex items-center gap-1 text-muted-foreground"><EyeOff size={12} /> Disabled</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(k.created_at)}</td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(k.last_used_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                        title="Revoke"
                        onClick={() => revokeMutation.mutate(k.id)}
                        disabled={revokeMutation.isPending}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredKeys.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-[12px]">
              <Key size={32} className="mx-auto mb-3 text-muted-foreground/50" />
              No API keys found.
            </div>
          )}
        </div>
      )}
    </div>
    </PageShell>
  );
}

export default function PermissionsAdmin() {
  return (
    <ErrorBoundary>
      <PermissionsContent />
    </ErrorBoundary>
  );
}
