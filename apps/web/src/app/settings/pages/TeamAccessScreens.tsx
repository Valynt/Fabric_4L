import { useMemo, useState } from "react";
import { Shield, UserPlus } from "lucide-react";
import { Btn, PageHeader } from "@/components/ui/fabric";
import { formatDate } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import {
  useApiKeys,
  useInviteUser,
  useRevokeApiKey,
  useUsers,
  type User,
} from "@/hooks/useGovernance";
import { useSettingsAccess } from "../access";

const ROLE_STYLES: Record<string, string> = {
  super_admin: "bg-red-50 text-red-700 border-red-200",
  tenant_admin: "bg-amber-50 text-amber-700 border-amber-200",
  member: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-muted text-muted-foreground border-border",
};

function RoleBadge({ role }: { role: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${ROLE_STYLES[role] || ROLE_STYLES.viewer}`}>
      <Shield size={10} /> {role.replace("_", " ")}
    </span>
  );
}

function getTeamActionAccess(role: string) {
  const canMutateTeam = role === "super_admin" || role === "tenant_admin" || role === "admin";
  const canAssignRoles = canMutateTeam;
  const canAssignPolicies = canMutateTeam;
  return { canMutateTeam, canAssignRoles, canAssignPolicies };
}

function TeamUsersTable({ users, showRoleActions }: { users: User[]; showRoleActions: boolean }) {
  return (
    <table className="w-full text-xs">
      <thead className="bg-muted border-b border-border text-muted-foreground uppercase tracking-wide text-xs">
        <tr>
          <th className="text-left px-4 py-2">User</th><th className="text-left px-4 py-2">Role</th><th className="text-left px-4 py-2">Status</th><th className="text-right px-4 py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map((u) => (
          <tr key={u.id} className="border-b border-border">
            <td className="px-4 py-3">
              <div className="font-medium text-foreground">{u.display_name || u.email}</div>
              <div className="text-muted-foreground">{u.email}</div>
            </td>
            <td className="px-4 py-3"><RoleBadge role={u.role} /></td>
            <td className="px-4 py-3">{u.status}</td>
            <td className="px-4 py-3 text-right">
              {showRoleActions ? (
                <div className="inline-flex gap-2">
                  <Btn variant="ghost" size="sm">Assign role</Btn>
                  {u.status === "active" ? <Btn variant="ghost" size="sm">Deactivate</Btn> : <Btn variant="ghost" size="sm">Reactivate</Btn>}
                </div>
              ) : (
                <span className="text-neutral-400">Read only</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function TeamMembersScreen() {
  const { role } = useSettingsAccess();
  const { canMutateTeam } = getTeamActionAccess(role);
  const { data: users = [] } = useUsers();
  const inviteMutation = useInviteUser();
  const [inviteEmail, setInviteEmail] = useState("");

  return (
    <div className="p-6 max-w-6xl space-y-4">
      <PageHeader title="Team Members" subtitle="Invite and manage workspace member lifecycle." />
      <div className="flex justify-end">
        {canMutateTeam && (
          <div className="flex items-center gap-2">
            <input className="border border-neutral-200 rounded px-2 py-1 text-xs" placeholder="user@company.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
            <Btn variant="primary" onClick={() => inviteEmail && inviteMutation.mutate({ email: inviteEmail, role: "member" })}>
              <UserPlus size={13} className="mr-1" />Invite member
            </Btn>
          </div>
        )}
      </div>
      <div className="rounded-xl border border-neutral-200 overflow-hidden bg-white">
        <TeamUsersTable users={users} showRoleActions={canMutateTeam} />
      </div>
    </div>
  );
}

export function TeamRolesScreen() {
  const { role } = useSettingsAccess();
  const { canAssignRoles } = getTeamActionAccess(role);
  const { data: users = [] } = useUsers();
  const roleCounts = useMemo(() => users.reduce<Record<string, number>>((acc, user) => {
    acc[user.role] = (acc[user.role] || 0) + 1;
    return acc;
  }, {}), [users]);

  return (
    <div className="p-6 max-w-6xl space-y-4">
      <PageHeader title="Team Roles" subtitle="Define roles and assign role-based access to members." />
      <div className="grid gap-3 md:grid-cols-3">
        {Object.entries(roleCounts).map(([r, count]) => (
          <div key={r} className="rounded-lg border border-neutral-200 bg-white p-4">
            <div className="text-xs text-neutral-500 uppercase">{r.replace("_", " ")}</div>
            <div className="text-xl font-semibold">{count}</div>
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-neutral-200 overflow-hidden bg-white">
        <TeamUsersTable users={users} showRoleActions={canAssignRoles} />
      </div>
    </div>
  );
}

export function TeamPermissionsScreen() {
  const { role } = useSettingsAccess();
  const { canAssignPolicies } = getTeamActionAccess(role);
  const { data: apiKeys = [] } = useApiKeys();
  const revokeMutation = useRevokeApiKey();

  return (
    <div className="p-6 max-w-6xl space-y-4">
      <PageHeader title="Team Permissions" subtitle="Review permission matrix and assign policy controls." />
      <div className="rounded-xl border border-border bg-white overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-muted border-b border-border text-muted-foreground uppercase tracking-wide text-xs">
            <tr><th className="px-4 py-2 text-left">Policy surface</th><th className="px-4 py-2 text-left">Capability</th><th className="px-4 py-2 text-right">Action</th></tr>
          </thead>
          <tbody>
            <tr className="border-b border-border"><td className="px-4 py-3">Members</td><td className="px-4 py-3">members:view/manage</td><td className="px-4 py-3 text-right">{canAssignPolicies ? <Btn variant="ghost" size="sm">Assign policy</Btn> : <span className="text-muted-foreground">Read only</span>}</td></tr>
            <tr className="border-b border-border"><td className="px-4 py-3">Roles</td><td className="px-4 py-3">roles:view/manage</td><td className="px-4 py-3 text-right">{canAssignPolicies ? <Btn variant="ghost" size="sm">Assign policy</Btn> : <span className="text-muted-foreground">Read only</span>}</td></tr>
            <tr><td className="px-4 py-3">API Keys</td><td className="px-4 py-3">keys:view/revoke</td><td className="px-4 py-3 text-right">{canAssignPolicies ? <Btn variant="ghost" size="sm">Assign policy</Btn> : <span className="text-muted-foreground">Read only</span>}</td></tr>
          </tbody>
        </table>
      </div>
      <div className="rounded-xl border border-border bg-white overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-muted border-b border-border"><tr><th className="px-4 py-2 text-left">API Key</th><th className="px-4 py-2 text-left">Last used</th><th className="px-4 py-2 text-right">Mutation</th></tr></thead>
          <tbody>
            {apiKeys.map((key) => (
              <tr key={key.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium">{key.name}</td>
                <td className="px-4 py-3">{key.last_used_at ? formatDate(key.last_used_at) : "Never"}</td>
                <td className="px-4 py-3 text-right">
                  {canAssignPolicies ? (
                    <Btn variant="ghost" size="sm" className={cn(revokeMutation.isPending && "opacity-50")} onClick={() => revokeMutation.mutate(key.id)}>Revoke</Btn>
                  ) : <span className="text-muted-foreground">Read only</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
