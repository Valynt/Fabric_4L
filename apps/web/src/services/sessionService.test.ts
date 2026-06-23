import { afterEach, describe, expect, it, vi } from "vitest";

import { setAuthProvider } from "@/test/utils/withAuthProvider";
import { SessionService } from "./sessionService";

describe("SessionService", () => {
  afterEach(() => {
    setAuthProvider("legacy");
    vi.unstubAllGlobals();
  });

  it("redirects Clerk unauthorized responses to sign-in instead of workspace picker", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/home",
        replace,
      },
    });

    new SessionService().redirectToLogin();

    expect(replace).toHaveBeenCalledWith("/sign-in");
    expect(replace).not.toHaveBeenCalledWith("/workspaces");
  });
});
