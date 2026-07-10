/**
 * Storybook Configuration — Fabric_4L
 * =====================================
 *
 * - Uses Vite builder for fast HMR and production builds
 * - Loads all stories from src/ and stories/ directories
 * - Includes essential addons: docs, interactions, a11y, backgrounds
 * - Respects DESIGN.md typography rules (Inter, JetBrains Mono)
 *
 * @see https://storybook.js.org/docs/configure
 */

import type { StorybookConfig } from "@storybook/react-vite";
import { resolve } from "node:path";

const config: StorybookConfig = {
  stories: [
    // UI primitives (shadcn/ui wrappers)
    "../stories/ui/**/*.stories.@(ts|tsx)",
    // Domain-specific components
    "../stories/domain/**/*.stories.@(ts|tsx)",
    // Page-level compositions
    "../stories/pages/**/*.stories.@(ts|tsx)",
    // Co-located stories within src (optional convention)
    "../src/**/*.stories.@(ts|tsx)",
  ],

  addons: [
    // Core documentation and controls
    "@storybook/addon-essentials",
    // Interaction testing (play functions)
    "@storybook/addon-interactions",
    // Accessibility auditing via axe-core
    "@storybook/addon-a11y",
    // Background grid / theme toggle
    "@storybook/addon-backgrounds",
    // Viewport presets for responsive testing
    "@storybook/addon-viewport",
    // Measure / outline overlay
    "@storybook/addon-measure",
    // Story source code viewer
    "@storybook/addon-storysource",
  ],

  framework: {
    name: "@storybook/react-vite",
    options: {
      // Strict mode helps catch side-effects in stories
      strictMode: true,
      builder: {
        viteConfigPath: resolve(__dirname, "../vite.config.ts"),
      },
    },
  },

  typescript: {
    // Use react-docgen-typescript for accurate prop tables
    reactDocgen: "react-docgen-typescript",
    reactDocgenTypescriptOptions: {
      // Speed up docgen by excluding large generated files
      exclude: ["**/node_modules/**", "**/generated/**"],
      // Include JSDoc descriptions in prop tables
      shouldExtractLiteralValuesFromEnum: true,
      // Include @default tags as default values
      shouldRemoveUndefinedFromOptional: true,
    },
  },

  core: {
    // Disable telemetry for privacy
    disableTelemetry: true,
    // Enable crash reporter for better error messages
    enableCrashReports: false,
  },

  // Static build output directory
  outputDir: "../storybook-static",

  // Serve static assets from the public directory
  staticDirs: ["../public"],

  // Vite configuration overrides
  async viteFinal(config) {
    // Ensure aliases match the main vite.config.ts
    config.resolve = config.resolve ?? {};
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": resolve(__dirname, "../src"),
      "@/components": resolve(__dirname, "../src/components"),
      "@/lib": resolve(__dirname, "../src/lib"),
      "@/hooks": resolve(__dirname, "../src/hooks"),
      "@/api": resolve(__dirname, "../src/api"),
      "@/stores": resolve(__dirname, "../src/stores"),
    };

    // Ensure CSS is processed through Tailwind
    config.css = config.css ?? {};
    config.css.postcss = config.css.postcss ?? "../postcss.config.js";

    return config;
  },
};

export default config;
