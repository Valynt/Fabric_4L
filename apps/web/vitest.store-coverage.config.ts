import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
    include: [
      "src/stores/**/*.test.ts",
      "src/hooks/useExtractionConfig.test.ts",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text"],
      all: true,
      include: [
        "src/stores/**/*.ts",
        "src/hooks/useExtractionConfig.ts",
      ],
      exclude: ["**/*.test.*", "**/*.spec.*", "**/index.ts"],
      thresholds: {
        lines: 80,
        functions: 70,
        branches: 70,
        statements: 80,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "shared"),
    },
  },
});
