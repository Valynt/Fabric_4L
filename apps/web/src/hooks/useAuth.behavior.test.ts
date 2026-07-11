import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { buildApiFetchInit } from "@/api/client";
import { SessionService } from "@/services/sessionService";
import { setAuthProvider } from "@/test/utils/withAuthProvider";

function clearCookies() {
  if (typeof document === "undefined") return;
  document.cookie.split(";").forEach((cookie) => {
    const [name] = cookie.split("=");
    document.cookie = `${name.trim()}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  });
}

describe("useAuth behavior invariants", () => {
  beforeEach(() => {
    clearCookies();
  });

  afterEach(() => {
    clearCookies();
    vi.unstubAllGlobals();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("authenticated user with CSRF cookie can obtain CSRF headers", () => {
    document.cookie = "vf_csrf_token=valid-csrf-token; path=/";

    const init = buildApiFetchInit({ method: "POST" });
    const headers = init.headers as Record<string, string>;

    expect(headers["X-CSRF-Token"]).toBe("valid-csrf-token");
  });

  it("preserves an explicit CSRF header when one is already provided", () => {
    document.cookie = "vf_csrf_token=cookie-token; path=/";

    const init = buildApiFetchInit({
      method: "POST",
      headers: { "X-CSRF-Token": "explicit-token" },
    });
    const headers = init.headers as Record<string, string>;

    expect(headers["X-CSRF-Token"]).toBe("explicit-token");
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user without CSRF cookie is denied CSRF headers", () => {
    const init = buildApiFetchInit({ method: "POST" });
    const headers = init.headers as Record<string, string>;

    expect(headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("does not attach CSRF headers to safe read-only requests", () => {
    document.cookie = "vf_csrf_token=valid-csrf-token; path=/";

    const init = buildApiFetchInit({ method: "GET" });
    const headers = init.headers as Record<string, string>;

    expect(headers["X-CSRF-Token"]).toBeUndefined();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode — auth redirects
  // ───────────────────────────────────────────────────────────────────────────
  it("redirects unauthenticated users to login with the original destination preserved", () => {
    setAuthProvider("clerk");
    const replace = vi.fn();
    vi.stubGlobal("window", {
      location: {
        pathname: "/t/acme/value-trees",
        search: "?filter=draft",
        hash: "",
        replace,
      },
    });

    new SessionService().handleUnauthorized();

    expect(replace).toHaveBeenCalledWith(
      "/sign-in?redirect_url=%2Ft%2Facme%2Fvalue-trees%3Ffilter%3Ddraft"
    );
  });

  it("auth redirects are idempotent and do not create self-referential loops", () => {
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

    new SessionService().handleUnauthorized();

    expect(replace).not.toHaveBeenCalled();
  });
});
