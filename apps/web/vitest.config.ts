import { defineConfig } from "vitest/config";
import path from "node:path";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    env: {
      VITEST: "true",
    },
    typecheck: {
      tsconfig: "./tsconfig.spec.json",
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "node_modules/",
        "test/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/*.test.{ts,tsx}",
        "src/api/generated/**",
        "src/main.tsx",
        "src/App.tsx",
        "src/const.ts",
        "src/api/types.ts",
        "src/shell/**",
      ],
      thresholds: {
        lines: 35,
        functions: 30,
        statements: 35,
        branches: 20,
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
