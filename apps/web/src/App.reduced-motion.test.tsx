import { useContext } from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MotionConfigContext } from "framer-motion";
import App from "./App";

// Keep the test focused on the app-root MotionConfig wiring: replace the
// full static route tree and unrelated providers with lightweight stand-ins,
// matching the provider-mocking pattern in shell/router.behavior.test.tsx.
vi.mock("./shell/router", async () => {
  const { createMemoryRouter } = await vi.importActual<
    typeof import("react-router-dom")
  >("react-router-dom");
  return {
    router: createMemoryRouter(
      [{ path: "*", element: <ReducedMotionProbe /> }],
      { initialEntries: ["/"] }
    ),
  };
});

vi.mock("@/components", () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

vi.mock("@/components/ui/sonner", () => ({
  Toaster: () => null,
}));

vi.mock("@/contexts/ThemeContext", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/auth/ClerkAuthBridge", () => ({
  ClerkAuthBridge: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

function ReducedMotionProbe() {
  const { reducedMotion } = useContext(MotionConfigContext);
  return <div data-testid="reduced-motion-preference">{reducedMotion}</div>;
}

describe("App root reduced-motion accessibility (WCAG 2.3.3)", () => {
  afterEach(() => {
    cleanup();
  });

  it("exposes the user's prefers-reduced-motion setting to every motion component in the app", () => {
    render(<App />);
    // "user" tells framer-motion to disable transform/layout animations
    // whenever the OS-level prefers-reduced-motion setting is enabled.
    expect(screen.getByTestId("reduced-motion-preference")).toHaveTextContent("user");
  });

  it("still renders routed content inside the MotionConfig boundary", () => {
    render(<App />);
    expect(screen.getByTestId("reduced-motion-preference")).toBeInTheDocument();
  });
});
