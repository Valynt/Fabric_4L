import { afterEach, describe, expect, it, vi } from "vitest";

import { setAuthProvider } from "@/test/utils/withAuthProvider";
import { SessionService } from "./sessionService";

describe("SessionService", () => {
  afterEach(() => {
    setAuthProvider("legacy");
    vi.unstubAllGlobals();
  });

  it("redirects Clerk unauthorized responses to sign-in with the attempted route", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/t/acme/accounts",
        search: "?view=list",
        hash: "",
        replace,
      },
    });

    new SessionService().redirectToLogin();

    expect(replace).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Ft%2Facme%2Faccounts%3Fview%3Dlist"
    );
    expect(replace).not.toHaveBeenCalledWith("/workspaces");
  });

  it("does not create a self-referential Clerk sign-in redirect", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/sign-in",
        search: "",
        hash: "",
        replace,
      },
    });

    new SessionService().redirectToLogin();

    expect(replace).not.toHaveBeenCalled();
  });
});
