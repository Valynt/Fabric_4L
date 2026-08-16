import { describe, expect, it } from "vitest";
import {
  accountScopeFromPath,
  authorizationSnapshotQueryKey,
} from "./AuthorizationProvider";

describe("authorizationSnapshotQueryKey", () => {
  it("binds tenant authorization to the exact session and Fabric tenant", () => {
    expect(authorizationSnapshotQueryKey("sess_1", "ten_1", null)).toEqual([
      "authorization-snapshot",
      "1",
      "sess_1",
      "ten_1",
      "tenant",
    ]);
  });

  it("includes the normalized exact account scope", () => {
    expect(
      authorizationSnapshotQueryKey("sess_1", "ten_1", " acc_1 ")
    ).toEqual([
      "authorization-snapshot",
      "1",
      "sess_1",
      "ten_1",
      "account:acc_1",
    ]);
  });

  it("does not reuse a previous account when the scope changes", () => {
    const previous = authorizationSnapshotQueryKey("sess_1", "ten_1", "acc_1");
    const next = authorizationSnapshotQueryKey("sess_1", "ten_1", "acc_2");
    expect(previous).not.toEqual(next);
    expect(next[4]).toBe("account:acc_2");
  });
});

describe("accountScopeFromPath", () => {
  it("binds a direct account URL to the route account id", () => {
    expect(
      accountScopeFromPath("/t/acme/accounts/acc_99/studio")
    ).toBe("acc_99");
  });

  it("stays tenant-scoped when no account segment is present", () => {
    expect(accountScopeFromPath("/t/acme/home")).toBeNull();
  });
});
