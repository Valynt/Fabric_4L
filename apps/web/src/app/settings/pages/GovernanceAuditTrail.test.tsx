import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { buildOperationalAuditParams } from "@/hooks/useOperationalAudit";
import { GovernanceAuditTrail } from "./GovernanceAuditTrail";
import { useOperationalAudit } from "@/hooks/useOperationalAudit";

vi.mock("@/hooks/useOperationalAudit", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useOperationalAudit")>("@/hooks/useOperationalAudit");
  return {
    ...actual,
    useOperationalAudit: vi.fn(() => ({ data: { entries: [], total: 0, page: 1, per_page: 25 }, isLoading: false, error: null })),
  };
});

vi.mock("../access", () => ({
  useSettingsAccess: vi.fn(() => ({ role: "analyst", hasCapability: () => true, getCapabilityDecision: () => ({ allowed: true, reasons: [], source: "fallback" }) })),
}));

describe("GovernanceAuditTrail", () => {
  it("serializes filter state to API query params", () => {
    const params = buildOperationalAuditParams({ actor: "alice", action: "login", entityType: "session", entityId: "sess-1", startDate: "2026-05-01", endDate: "2026-05-20", page: 2, perPage: 50 });
    expect(params.get("actor")).toBe("alice");
    expect(params.get("action")).toBe("login");
    expect(params.get("entity_type")).toBe("session");
    expect(params.get("entity_id")).toBe("sess-1");
    expect(params.get("start_date")).toBe("2026-05-01");
    expect(params.get("end_date")).toBe("2026-05-20");
    expect(params.get("page")).toBe("2");
    expect(params.get("per_page")).toBe("50");
  });

  it("hides export controls for unauthorized roles", () => {
    render(<MemoryRouter><GovernanceAuditTrail /></MemoryRouter>);
    expect(screen.queryByText("Export CSV")).not.toBeInTheDocument();
    expect(screen.queryByText("Export JSON")).not.toBeInTheDocument();
  });

  it("shows error state", () => {
    vi.mocked(useOperationalAudit).mockReturnValueOnce({ data: undefined, isLoading: false, error: { message: "boom" } } as never);
    render(<MemoryRouter><GovernanceAuditTrail /></MemoryRouter>);
    expect(screen.getByText("Failed to load audit events")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<MemoryRouter><GovernanceAuditTrail /></MemoryRouter>);
    expect(screen.getByText("No operational audit events found for this tenant.")).toBeInTheDocument();
  });
});
