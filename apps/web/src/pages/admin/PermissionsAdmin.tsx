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
 * - Destructive actions confirmed with tenant scope
 */

import { useState, useMemo, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  Users, Key, Plus, UserPlus, Shield,
  CheckCircle2, Clock, Eye, EyeOff, Trash2,
} from "lucide-react";
import { formatDate } from "@/lib/formatters";
import ErrorBoundary from "@/components/ErrorBoundary";
import { Btn } from "@/components/ui/fabric";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useUsers,
  useApiKeys,
  useRevokeApiKey,
  useInviteUser,
  type User,
  type ApiKey,
} from "@/hooks/useGovernance";
import {
  AdminShell,
  AdminTabs,
  AdminFilterBar,
  AdminDataTable,
  AdminIconButton,
  AdminIconButtonGroup,
  AdminConfirmDialog,
  type AdminDataTableColumn,
} from "@/components/admin";

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
    <span className={`inline-flex items-center gap-1 vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${ROLE_STYLES[role] || ROLE_STYLES.viewer}`}>
      <Shield size={10} /> {role.replace("_", " ")}
    </span>
  );
}

function StatusChip({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center vf-text-micro font-semibold px-2 py-0.5 rounded-full border ${STATUS_STYLES[status] || STATUS_STYLES.deactivated}`}>
      {status}
    </span>
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

  const [confirmRevoke, setConfirmRevoke] = useState<{ open: boolean; keyId: string; keyName: string }>({
    open: false,
    keyId: "",
    keyName: "",
  });

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

  const handleRevokeConfirm = async () => {
    if (!confirmRevoke.keyId) return;
    await revokeMutation.mutateAsync(confirmRevoke.keyId);
    setConfirmRevoke({ open: false, keyId: "", keyName: "" });
    refetchKeys();
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

  const userColumns: AdminDataTableColumn<User>[] = [
    {
      key: "user",
      header: "User",
      render: (u) => (
        <div>
          <span className="font-medium text-foreground block">{u.display_name || u.email}</span>
          {u.display_name && <span className="vf-text-micro text-muted-foreground">{u.email}</span>}
        </div>
      ),
    },
    { key: "role", header: "Role", render: (u) => <RoleBadge role={u.role} /> },
    { key: "status", header: "Status", render: (u) => <StatusChip status={u.status} /> },
    { key: "created_at", header: "Created", render: (u) => <span className="text-muted-foreground">{formatDate(u.created_at)}</span> },
    { key: "last_login_at", header: "Last Login", render: (u) => <span className="text-muted-foreground">{formatDate(u.last_login_at)}</span> },
    {
      key: "actions",
      header: "",
      className: "w-16",
      render: () => (
        <AdminIconButtonGroup>
          <AdminIconButton icon={Eye} label="View user" />
        </AdminIconButtonGroup>
      ),
    },
  ];

  const keyColumns: AdminDataTableColumn<ApiKey>[] = [
    { key: "name", header: "Key Name", render: (k) => <span className="font-medium text-foreground">{k.name}</span> },
    { key: "prefix", header: "Prefix", render: (k) => <span className="font-mono vf-text-caption text-muted-foreground">{k.prefix}•••</span> },
    {
      key: "enabled",
      header: "Enabled",
      render: (k) =>
        k.is_enabled
          ? <span className="inline-flex items-center gap-1 text-success"><CheckCircle2 size={12} /> Active</span>
          : <span className="inline-flex items-center gap-1 text-muted-foreground"><EyeOff size={12} /> Disabled</span>,
    },
    { key: "created_at", header: "Created", render: (k) => <span className="text-muted-foreground">{formatDate(k.created_at)}</span> },
    { key: "last_used_at", header: "Last Used", render: (k) => <span className="text-muted-foreground">{formatDate(k.last_used_at)}</span> },
    {
      key: "actions",
      header: "",
      className: "w-16",
      render: (k) => (
        <AdminIconButtonGroup>
          <AdminIconButton
            icon={Trash2}
            label="Revoke API key"
            variant="destructive"
            onClick={() => setConfirmRevoke({ open: true, keyId: k.id, keyName: k.name })}
          />
        </AdminIconButtonGroup>
      ),
    },
  ];

  return (
    <AdminShell
      title="Permissions & Access"
      subtitle="Manage users, roles, and API keys for your tenant."
      fullWidth
      actions={
        <Btn variant="primary" onClick={() => activeTab === "users" ? setShowInvite(true) : null}>
          {activeTab === "users"
            ? <><UserPlus size={13} className="mr-1" /> Invite User</>
            : <><Plus size={13} className="mr-1" /> New API Key</>
          }
        </Btn>
      }
      tabs={
        <AdminTabs
          tabs={[
            { id: "users", label: "Users", count: users.length, icon: <Users size={13} /> },
            { id: "api-keys", label: "API Keys", count: apiKeys.length, icon: <Key size={13} /> },
          ]}
          activeTab={activeTab}
          onChange={(tabId) => setActiveTab(tabId as TabType)}
        />
      }
    >
      <AdminFilterBar
        searchPlaceholder={activeTab === "users" ? "Search users..." : "Search API keys..."}
        searchValue={search}
        onSearchChange={setSearch}
      />

      {activeTab === "users" ? (
        <AdminDataTable
          data={filteredUsers}
          columns={userColumns}
          keyExtractor={(u) => u.id}
          isLoading={usersLoading}
          error={usersError}
          onRetry={refetchUsers}
          emptyTitle="No users found"
          emptyDescription={search ? "No users match your search." : "Get started by inviting your first user."}
          emptyIcon={Users}
        />
      ) : (
        <AdminDataTable
          data={filteredKeys}
          columns={keyColumns}
          keyExtractor={(k) => k.id}
          isLoading={keysLoading}
          error={keysError}
          onRetry={refetchKeys}
          emptyTitle="No API keys found"
          emptyDescription={search ? "No API keys match your search." : "Create an API key to integrate with external services."}
          emptyIcon={Key}
        />
      )}

      {/* Invite User Dialog */}
      <Dialog open={showInvite} onOpenChange={setShowInvite}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="vf-heading-l font-semibold">Invite User</DialogTitle>
            <DialogDescription className="vf-text-body-m">
              Send an invitation to join this tenant.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="vf-text-caption font-semibold text-muted-foreground block mb-1">Email</label>
              <Input
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="user@company.com"
              />
            </div>
            <div>
              <label className="vf-text-caption font-semibold text-muted-foreground block mb-1">Role</label>
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
              <p className="vf-text-caption text-destructive">
                {inviteMutation.error instanceof Error ? inviteMutation.error.message : "Invite failed"}
              </p>
            )}
          </div>
          <DialogFooter>
            <Btn variant="ghost" onClick={() => setShowInvite(false)}>Cancel</Btn>
            <Btn variant="primary" onClick={handleInvite} disabled={!inviteEmail || inviteMutation.isPending}>
              {inviteMutation.isPending ? "Sending…" : "Send Invite"}
            </Btn>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Key Confirmation */}
      <AdminConfirmDialog
        open={confirmRevoke.open}
        onOpenChange={(open) => setConfirmRevoke((prev) => ({ ...prev, open }))}
        title="Revoke API Key"
        description="This API key will be permanently revoked. Any integrations using it will stop working immediately."
        itemName={confirmRevoke.keyName}
        tenantName="Current tenant"
        actionLabel="Revoke Key"
        variant="destructive"
        onConfirm={handleRevokeConfirm}
        isPending={revokeMutation.isPending}
      />
    </AdminShell>
  );
}

export default function PermissionsAdmin() {
  return (
    <ErrorBoundary>
      <PermissionsContent />
    </ErrorBoundary>
  );
}
