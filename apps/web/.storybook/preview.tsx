/**
 * Storybook Preview Configuration
 * ================================
 *
 * Wraps all stories with the same providers used in production:
 *   - React Query (TanStack Query) with test-safe defaults
 *   - Theme provider (light/dark toggle)
 * - Tailwind CSS base styles
 * - DESIGN.md typography (Inter, JetBrains Mono)
 *
 * @see https://storybook.js.org/docs/configure#configure-story-rendering
 */

import type { Preview } from "@storybook/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

// ---------------------------------------------------------------------------
// Global styles — same entry point as production
// ---------------------------------------------------------------------------

import "../src/index.css";

// ---------------------------------------------------------------------------
// Query Client factory for Storybook
// ---------------------------------------------------------------------------

function createStorybookQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Stories are static — don't retry or refetch
        retry: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: false,
        staleTime: Infinity,
        // Show initial data immediately for deterministic screenshots
        placeholderData: (previousData: unknown) => previousData,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Story wrapper component
// ---------------------------------------------------------------------------

function StorybookProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(() => createStorybookQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <div className="min-h-screen bg-background text-foreground antialiased">
          {children}
        </div>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Preview configuration
// ---------------------------------------------------------------------------

const preview: Preview = {
  // Decorator applied to every story
  decorators: [
    (Story) => (
      <StorybookProviders>
        <Story />
      </StorybookProviders>
    ),
  ],

  // Global parameters
  parameters: {
    // Background presets matching Tailwind themes
    backgrounds: {
      default: "light",
      values: [
        { name: "light", value: "#ffffff" },
        { name: "dark", value: "#0a0a0a" },
        { name: "slate-50", value: "#f8fafc" },
        { name: "slate-100", value: "#f1f5f9" },
      ],
    },

    // Viewport presets for responsive testing
    viewport: {
      viewports: {
        mobile: {
          name: "Mobile (375×667)",
          styles: { width: "375px", height: "667px" },
          type: "mobile",
        },
        tablet: {
          name: "Tablet (768×1024)",
          styles: { width: "768px", height: "1024px" },
          type: "tablet",
        },
        desktop: {
          name: "Desktop (1280×720)",
          styles: { width: "1280px", height: "720px" },
          type: "desktop",
        },
        wide: {
          name: "Wide (1440×900)",
          styles: { width: "1440px", height: "900px" },
          type: "desktop",
        },
      },
      defaultViewport: "desktop",
    },

    // A11y addon — axe-core rules
    a11y: {
      config: {
        rules: [
          // Color contrast can be stricter than default
          { id: "color-contrast", enabled: true },
          // Ensure all images have alt text
          { id: "image-alt", enabled: true },
          // Enforce valid ARIA usage
          { id: "aria-valid-attr-value", enabled: true },
        ],
      },
      // Run a11y checks on every story by default
      test: "todo",
    },

    // Controls panel — expanded by default for discoverability
    controls: {
      expanded: true,
      hideNoControlsWarning: true,
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },

    // Actions panel — log all function arguments
    actions: { argTypesRegex: "^on[A-Z].*" },

    // Docs — auto-generate docs page for every story
    docs: {
      toc: true,
      source: { type: "dynamic" },
    },

    // Interactions — run play functions automatically in docs
    interactions: {
      disable: false,
    },

    // Options panel
    options: {
      storySort: {
        order: [
          "UI",
          ["Button", "Card", "Badge", "Dialog", "Form"],
          "Domain",
          ["WorkflowCard", "TenantSelector", "*"],
          "Pages",
          ["DashboardLayout", "*"],
        ],
      },
    },
  },

  // Global tags applied to all stories
  tags: ["autodocs"],
};

export default preview;
