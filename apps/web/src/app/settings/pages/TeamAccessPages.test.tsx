import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TeamMembers } from "./TeamMembers";
import { TeamRoles } from "./TeamRoles";
import { TeamPermissions } from "./TeamPermissions";

const roleState = { role: "tenant_admin" };

vi.mock("../access", () => ({
  useSettingsAccess: () => ({
    role: roleState.role,
    capabilities: new Set(["team"]),
    hasCapability: () => true,
    getCapabilityDecision: () => ({ allowed: true, reasons: [], source: "fallback" }),
  }),
}));

vi.mock("@/hooks/useGovernance", () => ({
  useUsers: () => ({
    data: [
      { id: "u1", email: "admin@example.com", display_name: "Admin", role: "tenant_admin", status: "active", tenant_id: "t1", created_at: "2026-01-01T00:00:00Z" },
    ],
  }),
  useApiKeys: () => ({
    data: [{ id: "k1", name: "Primary Key", prefix: "pk_", tenant_id: "t1", is_enabled: true, created_at: "2026-01-01T00:00:00Z" }],
  }),
  useInviteUser: () => ({ mutate: vi.fn(), isPending: false }),
  useRevokeApiKey: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("Team access settings pages", () => {
  it("renders separated route screens", () => {
    render(<TeamMembers />);
    expect(screen.getByText("Team Members")).toBeInTheDocument();

    render(<TeamRoles />);
    expect(screen.getByText("Team Roles")).toBeInTheDocument();

    render(<TeamPermissions />);
    expect(screen.getByText("Team Permissions")).toBeInTheDocument();
  });

  it("hides mutation controls for read-only roles while keeping inspection views", () => {
    roleState.role = "viewer";
    render(<TeamMembers />);
    expect(screen.getByText("Team Members")).toBeInTheDocument();
    expect(screen.queryByText("Invite member")).not.toBeInTheDocument();
    expect(screen.getByText("Read only")).toBeInTheDocument();
  });
});
