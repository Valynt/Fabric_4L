/**
 * Behavior tests for app bootstrap factories extracted from main.tsx.
 *
 * Covers:
 *   - createQueryClient: default query options (retry/staleTime/focus) and
 *     error handlers wired to the telemetry logger.
 *   - initSentry: guarded by DSN presence; swallows init failures.
 *   - registerServiceWorker: prod-only, fires after the `load` event, and
 *     logs registration failures without rethrowing.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const sentryMock = vi.hoisted(() => ({ init: vi.fn() }));

vi.mock("@sentry/react", () => sentryMock);

vi.mock("@/lib/telemetry", () => ({
  logError: vi.fn(),
  createFeatureLogger: () => ({
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  }),
}));

// Import after vi.mock.
import { MutationObserver } from "@tanstack/react-query";
import { logError } from "@/lib/telemetry";
import {
  createQueryClient,
  initSentry,
  registerServiceWorker,
} from "./bootstrapFactory";
import { STALE_TIME } from "@/hooks/useApiShared";

describe("bootstrapFactory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("createQueryClient", () => {
    it("applies the shared default query options", () => {
      const client = createQueryClient();
      const defaults = client.getDefaultOptions().queries;

      expect(defaults).toMatchObject({
        staleTime: STALE_TIME.activity,
        retry: 2,
        refetchOnWindowFocus: false,
      });
    });

    it("wires query errors to the telemetry logger", async () => {
      const client = createQueryClient();

      await expect(
        client.fetchQuery({
          queryKey: ["accounts"],
          queryFn: () => {
            throw new Error("boom");
          },
          retry: false,
        })
      ).rejects.toThrow("boom");

      expect(logError).toHaveBeenCalledWith(
        "Query failed",
        expect.objectContaining({ queryKey: '["accounts"]' })
      );
    });

    it("wires mutation errors to the telemetry logger", async () => {
          const client = createQueryClient();
          const observer = new MutationObserver(client, {
            mutationKey: ["save"],
            mutationFn: () => {
              throw new Error("kaboom");
            },
          });

          await expect(observer.mutate()).rejects.toThrow("kaboom");

          expect(logError).toHaveBeenCalledWith(
            "Mutation failed",
            expect.objectContaining({ mutationKey: "save" })
          );
        });
  });

  describe("initSentry", () => {
      it("is a no-op when the DSN is falsy", () => {
        initSentry({ dsn: "" });
        initSentry({ dsn: undefined });
        expect(sentryMock.init).not.toHaveBeenCalled();
      });

      it("initializes Sentry with the DSN and environment", () => {
        initSentry({ dsn: "abc-dsn", mode: "production" });

        expect(sentryMock.init).toHaveBeenCalledWith(
          expect.objectContaining({
            dsn: "abc-dsn",
            environment: "production",
          })
        );
      });

      it("swallows Sentry init failures and logs them", () => {
        sentryMock.init.mockImplementationOnce(() => {
          throw new Error("sentry boomed");
        });

      initSentry({ dsn: "abc-dsn" });

      expect(logError).toHaveBeenCalledWith(
        "Failed to initialize Sentry",
        expect.objectContaining({ error: "sentry boomed" })
      );
    });
  });

  describe("registerServiceWorker", () => {
    let loadHandlers: Array<EventListener>;

    beforeEach(() => {
      loadHandlers = [];
      vi.spyOn(window, "addEventListener").mockImplementation(
        (name, handler) => {
          if (name === "load") {
            loadHandlers.push(handler);
          }
        }
      );
    });

    function installNavigatorServiceWorker() {
      const mockRegister = vi.fn();
      Object.defineProperty(navigator, "serviceWorker", {
        configurable: true,
        value: { register: mockRegister },
      });
      return mockRegister;
    }

    function deleteNavigatorServiceWorker() {
      delete (navigator as typeof navigator & { serviceWorker?: unknown })
        .serviceWorker;
    }

    it("does not register when not in production", () => {
      installNavigatorServiceWorker();
      registerServiceWorker(false);

      expect(loadHandlers).toHaveLength(0);
      deleteNavigatorServiceWorker();
    });

    it("does not register when navigator.serviceWorker is unavailable", () => {
      deleteNavigatorServiceWorker();

      registerServiceWorker(true);

      expect(loadHandlers).toHaveLength(0);
    });

    it("registers the service worker after the load event in production", () => {
      const mockRegister = installNavigatorServiceWorker();

      registerServiceWorker(true);

      expect(loadHandlers).toHaveLength(1);
      mockRegister.mockResolvedValue({});
      loadHandlers[0]();
      expect(mockRegister).toHaveBeenCalledWith("/sw.js");

      deleteNavigatorServiceWorker();
    });

    it("swallows and logs a service worker registration failure", async () => {
      const mockRegister = installNavigatorServiceWorker();

      registerServiceWorker(true);

      mockRegister.mockRejectedValue(new Error("reg failed"));
      loadHandlers[0]();
          await vi.waitFor(() =>
            expect(logError).toHaveBeenCalledWith(
              "Service worker registration failed",
              expect.objectContaining({ error: "reg failed" })
            )
          );
          deleteNavigatorServiceWorker();
        });
  });
});