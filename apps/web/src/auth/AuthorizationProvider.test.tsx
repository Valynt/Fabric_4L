import { describe, expect, it } from "vitest";
import { authorizationSnapshotQueryKey } from "./AuthorizationProvider";

describe("authorizationSnapshotQueryKey", () => {
  it("binds tenant authorization to the exact Clerk session and organization", () => {
    expect(authorizationSnapshotQueryKey("sess_1", "org_1", null)).toEqual([
      "authorization-snapshot",
      "1",
      "sess_1",
      "org_1",
      "tenant",
    ]);
  });

  it("includes the normalized exact account scope", () => {
    expect(authorizationSnapshotQueryKey("sess_1", "org_1", " acc_1 ")).toEqual(
      ["authorization-snapshot", "1", "sess_1", "org_1", "account:acc_1"]
    );
  });
});
