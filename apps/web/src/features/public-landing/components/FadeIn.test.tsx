import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MotionConfig } from "framer-motion";
import { FadeIn } from "./FadeIn";

// jsdom does not implement matchMedia; stub it so useReducedMotion can read
// the prefers-reduced-motion media query.
function stubMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("FadeIn", () => {
  beforeEach(() => {
    stubMatchMedia(false);
  });

  afterEach(() => {
    cleanup();
  });

  it("renders children through the lazy motion path when motion is allowed", () => {
    render(
      <FadeIn>
        <span>animated content</span>
      </FadeIn>
    );
    expect(screen.getByText("animated content")).toBeInTheDocument();
  });

  it("composes with an ancestor MotionConfig reducedMotion boundary", () => {
    render(
      <MotionConfig reducedMotion="user">
        <FadeIn delay={0.2}>
          <span>configured content</span>
        </FadeIn>
      </MotionConfig>
    );
    expect(screen.getByText("configured content")).toBeInTheDocument();
  });

  it("renders a plain div without motion props when reduced motion is preferred", async () => {
    stubMatchMedia(true);
    render(
      <FadeIn className="fade-in-static">
        <span>static content</span>
      </FadeIn>
    );
    const content = await screen.findByText("static content");
    const wrapper = content.parentElement;
    expect(wrapper).not.toBeNull();
    expect(wrapper!.tagName).toBe("DIV");
    expect(wrapper!.className).toContain("fade-in-static");
  });
});
