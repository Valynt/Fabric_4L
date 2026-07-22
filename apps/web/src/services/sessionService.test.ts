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

  it("redirects Clerk SSO callback routes to plain sign-in without a redirect_url loop", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/sso-callback",
        search: "?state=abc",
        hash: "",
        replace,
      },
    });

    new SessionService().redirectToLogin();

    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("swallows Clerk redirect failures from loc.replace", () => {
    setAuthProvider("clerk");
    const replace = vi.fn(() => {
      throw new Error("navigation blocked");
    });
    vi.stubGlobal("window", {
      location: {
        pathname: "/t/acme/accounts",
        search: "",
        hash: "",
        replace,
      },
    });

    expect(() => new SessionService().redirectToLogin()).not.toThrow();
    expect(replace).toHaveBeenCalled();
  });

  it("is a no-op when window is unavailable", () => {
    setAuthProvider("clerk");
    vi.stubGlobal("window", undefined);

    expect(() => new SessionService().redirectToLogin()).not.toThrow();
    expect(() => new SessionService().handleForbidden()).not.toThrow();
  });

  it("redirects legacy sessions to /sign-in", () => {
    setAuthProvider("legacy");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/workspaces", search: "", hash: "", replace },
    });

    new SessionService().redirectToLogin();

    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("does not redirect legacy sessions already on /sign-in", () => {
    setAuthProvider("legacy");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/sign-in", search: "", hash: "", replace },
    });

    new SessionService().redirectToLogin();

    expect(replace).not.toHaveBeenCalled();
  });

  it("swallows legacy redirect failures from loc.replace", () => {
    setAuthProvider("legacy");
    const replace = vi.fn(() => {
      throw new Error("navigation blocked");
    });
    vi.stubGlobal("window", {
      location: { pathname: "/workspaces", search: "", hash: "", replace },
    });

    expect(() => new SessionService().redirectToLogin()).not.toThrow();
    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("handleUnauthorized logs and redirects to login", () => {
    setAuthProvider("legacy");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/workspaces", search: "", hash: "", replace },
    });

    new SessionService().handleUnauthorized({ traceId: "t-1", route: "/x" });

    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("handleForbidden redirects to /forbidden", () => {
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/workspaces", search: "", hash: "", replace },
    });

    new SessionService().handleForbidden({ traceId: "t-2" });

    expect(replace).toHaveBeenCalledWith("/forbidden");
  });

  it("handleForbidden does not redirect when already on /forbidden", () => {
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: { pathname: "/forbidden", search: "", hash: "", replace },
    });

    new SessionService().handleForbidden();

    expect(replace).not.toHaveBeenCalled();
  });

  it("handleForbidden swallows replace failures", () => {
    const replace = vi.fn(() => {
      throw new Error("navigation blocked");
    });
    vi.stubGlobal("window", {
      location: { pathname: "/workspaces", search: "", hash: "", replace },
    });

    expect(() => new SessionService().handleForbidden()).not.toThrow();
    expect(replace).toHaveBeenCalledWith("/forbidden");
  });

  it("builds the Clerk redirect path when search and hash are absent", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/t/acme/accounts",
        search: undefined,
        hash: undefined,
        replace,
      },
    });

    new SessionService().redirectToLogin();

    expect(replace).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Ft%2Facme%2Faccounts"
    );
  });

  it("redirectTo assigns window.location.href", () => {
    const location = { href: "" };
    vi.stubGlobal("window", { location });

    new SessionService().redirectTo("https://accounts.example.com/sign-in");

    expect(location.href).toBe("https://accounts.example.com/sign-in");
  });
});
