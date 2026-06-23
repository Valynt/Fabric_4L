import { describe, expect, it } from "vitest";
import { createNextAction } from "./nextAction";

describe("createNextAction", () => {
  it("generates a default id from target when id is omitted", () => {
    const action = createNextAction({
      label: "Open account",
      target: "/accounts/123" as any,
      params: { accountId: "123" },
    });

    expect(action.id).toBe("/accounts/123-next-action");
    expect(action.label).toBe("Open account");
    expect(action.params).toEqual({ accountId: "123" });
  });

  it("preserves the provided id when present", () => {
    const action = createNextAction({
      id: "custom-action-id",
      label: "Review signal",
      target: "/signals/456" as any,
      params: { accountId: "456" },
    });

    expect(action.id).toBe("custom-action-id");
  });

  it("includes optional query and disabled fields", () => {
    const action = createNextAction({
      label: "Disabled action",
      target: "/home" as any,
      params: { accountId: "abc" },
      query: { tab: "settings" },
      disabled: true,
      reason: "No permission",
    });

    expect(action.query).toEqual({ tab: "settings" });
    expect(action.disabled).toBe(true);
    expect(action.reason).toBe("No permission");
  });
});
