import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useBilling, useFeatureCheck } from "./useBilling";
import { apiClient } from "@/api/client";
import { createWrapper, createMockResponse } from "@/test-utils";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = apiClient.get as Mock;
const mockPost = apiClient.post as Mock;
const originalLocation = window.location;

describe("useBilling behavior invariants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: originalLocation,
    });
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with active subscription can view billing details", async () => {
    const mockSubscription = {
      id: "sub_123",
      plan_id: "pro",
      status: "active",
      current_period_start: "2024-01-01T00:00:00Z",
      current_period_end: "2024-02-01T00:00:00Z",
      cancel_at_period_end: false,
    };
    mockGet.mockResolvedValue(createMockResponse(mockSubscription));

    const { result } = renderHook(() => useBilling("user_123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.subscription).toEqual(mockSubscription));
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("user can open customer portal when subscribed", async () => {
    const mockPortalResponse = { url: "https://billing.stripe.com/portal" };
    mockGet.mockResolvedValue(createMockResponse({ plan_id: "pro" }));
    mockPost.mockResolvedValue(createMockResponse(mockPortalResponse));

    Object.defineProperty(window, "location", {
      writable: true,
      value: { href: "http://localhost:5173" },
    });

    const { result } = renderHook(() => useBilling("user_123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.subscription).toBeTruthy());
    await act(async () => {
      await result.current.openCustomerPortal("http://localhost:5173/settings");
    });

    expect(window.location.href).toBe("https://billing.stripe.com/portal");
  });

  it("user can initiate checkout for plan upgrade", async () => {
    const mockCheckoutResponse = { session_id: "sess_123", url: "https://checkout.stripe.com/pay" };
    mockGet.mockResolvedValue(createMockResponse({ plan_id: "free" }));
    mockPost.mockResolvedValue(createMockResponse(mockCheckoutResponse));

    Object.defineProperty(window, "location", {
      writable: true,
      value: { href: "http://localhost:5173" },
    });

    const { result } = renderHook(() => useBilling("user_123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.subscription).toBeTruthy());
    await act(async () => {
      await result.current.subscribe("pro", "http://localhost:5173/success", "http://localhost:5173/cancel");
    });

    expect(window.location.href).toBe("https://checkout.stripe.com/pay");
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user without subscription sees undefined subscription state", async () => {
    mockGet.mockRejectedValue(new Error("Failed to fetch"));

    const { result } = renderHook(() => useBilling("user_123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.subscription).toBeUndefined();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("loading state is surfaced while subscription is resolving", async () => {
    mockGet.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useBilling("user_123"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.subscription).toBeUndefined();
    expect(result.current.error).toBeNull();
  });
});

describe("useFeatureCheck behavior invariants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Allowed behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user with feature access is allowed", async () => {
    mockGet.mockResolvedValue(createMockResponse({ feature_id: "advanced_models", has_access: true }));

    const { result } = renderHook(() => useFeatureCheck("user_123", "advanced_models"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data?.has_access).toBe(true));
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Denied behavior
  // ───────────────────────────────────────────────────────────────────────────
  it("user without feature access is denied", async () => {
    mockGet.mockResolvedValue(createMockResponse({ feature_id: "advanced_models", has_access: false }));

    const { result } = renderHook(() => useFeatureCheck("user_123", "advanced_models"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data?.has_access).toBe(false));
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Failure mode
  // ───────────────────────────────────────────────────────────────────────────
  it("empty customerId fails closed with idle state and no API call", async () => {
    const { result } = renderHook(() => useFeatureCheck("", "feature_1"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("empty featureId fails closed with idle state and no API call", async () => {
    const { result } = renderHook(() => useFeatureCheck("user_123", ""), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockGet).not.toHaveBeenCalled();
  });
});
