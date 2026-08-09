import { jsxLocPlugin } from "@builder.io/vite-plugin-jsx-loc";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  defineConfig,
  loadEnv,
  type Plugin,
  type ProxyOptions,
  type ViteDevServer,
} from "vite";
import { vitePluginManusRuntime } from "vite-plugin-manus-runtime";
import { visualizer } from "rollup-plugin-visualizer";
import { assertFrontendApiEnv } from "./scripts/frontend-api-env.mjs";

// =============================================================================
// Manus Debug Collector - Vite Plugin
// Writes browser logs directly to files, trimmed when exceeding size limit
// =============================================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = __dirname;
const WORKSPACE_ROOT = path.resolve(PROJECT_ROOT, "../..");
const LOG_DIR = path.join(PROJECT_ROOT, ".manus-logs");
const MAX_LOG_SIZE_BYTES = 1 * 1024 * 1024; // 1MB per log file
const TRIM_TARGET_BYTES = Math.floor(MAX_LOG_SIZE_BYTES * 0.6); // Trim to 60% to avoid constant re-trimming
const viteMode =
  process.env.NODE_ENV === "production"
    ? "production"
    : process.env.MODE || "development";
const viteEnv = loadEnv(viteMode, __dirname, "");
const frontendEnv = { ...process.env, ...viteEnv };
const isProductionFrontend =
  process.env.NODE_ENV === "production" ||
  frontendEnv.VITE_APP_ENV === "production";

assertFrontendApiEnv(frontendEnv, {
  production: isProductionFrontend,
  source: "Vite frontend build",
});

const VITE_PROXY_L1_URL =
  frontendEnv.VITE_PROXY_L1_URL || "http://localhost:8001";
const VITE_PROXY_L2_URL =
  frontendEnv.VITE_PROXY_L2_URL || "http://localhost:8002";
const VITE_PROXY_L3_URL =
  frontendEnv.VITE_PROXY_L3_URL || "http://localhost:8003";
const VITE_PROXY_L4_URL =
  frontendEnv.INTERNAL_L4_PROXY_URL ||
  frontendEnv.VITE_PROXY_L4_URL ||
  "http://localhost:8004";
const VITE_PROXY_L5_URL =
  frontendEnv.VITE_PROXY_L5_URL || "http://localhost:8005";
const VITE_PROXY_L6_URL =
  frontendEnv.VITE_PROXY_L6_URL || "http://localhost:8006";
const VITE_PROXY_API_GATEWAY_URL =
  frontendEnv.VITE_PROXY_API_GATEWAY_URL || "http://localhost:8008";

type LogSource = "browserConsole" | "networkRequests" | "sessionReplay";

interface ManusLogPayload {
  consoleLogs?: unknown[];
  networkRequests?: unknown[];
  sessionEvents?: unknown[];
}

interface HmrLikePayload {
  type?: string;
  event?: string;
  [key: string]: unknown;
}

function isManusLogPayload(value: unknown): value is ManusLogPayload {
  if (typeof value !== "object" || value === null) return false;
  const payload = value as Record<string, unknown>;
  const isUnknownArray = (candidate: unknown): candidate is unknown[] =>
    candidate === undefined || Array.isArray(candidate);
  return (
    isUnknownArray(payload.consoleLogs) &&
    isUnknownArray(payload.networkRequests) &&
    isUnknownArray(payload.sessionEvents)
  );
}

function isHmrLikePayload(value: unknown): value is HmrLikePayload {
  return typeof value === "object" && value !== null;
}

function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

function trimLogFile(logPath: string, maxSize: number) {
  try {
    if (!fs.existsSync(logPath) || fs.statSync(logPath).size <= maxSize) {
      return;
    }

    const lines = fs.readFileSync(logPath, "utf-8").split("\n");
    const keptLines: string[] = [];
    let keptBytes = 0;

    // Keep newest lines (from end) that fit within 60% of maxSize
    const targetSize = TRIM_TARGET_BYTES;
    for (let i = lines.length - 1; i >= 0; i--) {
      const lineBytes = Buffer.byteLength(`${lines[i]}\n`, "utf-8");
      if (keptBytes + lineBytes > targetSize) break;
      keptLines.unshift(lines[i]);
      keptBytes += lineBytes;
    }

    fs.writeFileSync(logPath, keptLines.join("\n"), "utf-8");
  } catch {
    /* ignore trim errors */
  }
}

function writeToLogFile(source: LogSource, entries: unknown[]) {
  if (entries.length === 0) return;

  ensureLogDir();
  const logPath = path.join(LOG_DIR, `${source}.log`);

  // Format entries with timestamps
  const lines = entries.map(entry => {
    const ts = new Date().toISOString();
    return `[${ts}] ${JSON.stringify(entry)}`;
  });

  // Append to log file
  fs.appendFileSync(logPath, `${lines.join("\n")}\n`, "utf-8");

  // Trim if exceeds max size
  trimLogFile(logPath, MAX_LOG_SIZE_BYTES);
}

/**
 * Vite plugin to collect browser debug logs
 * - POST /__manus__/logs: Browser sends logs, written directly to files
 * - Files: browserConsole.log, networkRequests.log, sessionReplay.log
 * - Auto-trimmed when exceeding 1MB (keeps newest entries)
 */
function vitePluginManusDebugCollector(): Plugin {
  return {
    name: "manus-debug-collector",

    transformIndexHtml(html) {
      if (process.env.NODE_ENV === "production") {
        return html;
      }
      return {
        html,
        tags: [
          {
            tag: "script",
            attrs: {
              src: "/__manus__/debug-collector.js",
              defer: true,
            },
            injectTo: "head",
          },
        ],
      };
    },

    configureServer(server: ViteDevServer) {
      server.ws.on("connection", () => {
        server.ws.on("manus:hmr", (rawPayload: unknown) => {
          if (!isHmrLikePayload(rawPayload)) {
            return;
          }
          const payloadType =
            typeof rawPayload.type === "string" ? rawPayload.type : "unknown";
          writeToLogFile("sessionReplay", [{ source: "hmr", payloadType }]);
        });
      });
      // POST /__manus__/logs: Browser sends logs (written directly to files)
      server.middlewares.use("/__manus__/logs", (req, res, next) => {
        if (req.method !== "POST") {
          return next();
        }

        const handlePayload = (payload: ManusLogPayload) => {
          // Write logs directly to files
          const consoleLogs = payload.consoleLogs;
          if (consoleLogs && consoleLogs.length > 0) {
            writeToLogFile("browserConsole", consoleLogs);
          }
          const networkRequests = payload.networkRequests;
          if (networkRequests && networkRequests.length > 0) {
            writeToLogFile("networkRequests", networkRequests);
          }
          const sessionEvents = payload.sessionEvents;
          if (sessionEvents && sessionEvents.length > 0) {
            writeToLogFile("sessionReplay", sessionEvents);
          }

          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true }));
        };

        const reqBody = (req as { body?: unknown }).body;
        if (reqBody && typeof reqBody === "object") {
          try {
            if (!isManusLogPayload(reqBody)) {
              throw new Error("Invalid manus log payload shape");
            }
            handlePayload(reqBody);
          } catch (e) {
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ success: false, error: String(e) }));
          }
          return;
        }

        let body = "";
        req.on("data", chunk => {
          body += chunk.toString();
        });

        req.on("end", () => {
          try {
            const payload: unknown = JSON.parse(body);
            if (!isManusLogPayload(payload)) {
              throw new Error("Invalid manus log payload shape");
            }
            handlePayload(payload);
          } catch (e) {
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ success: false, error: String(e) }));
          }
        });
      });
    },
  };
}

const plugins = [
  react(),
  tailwindcss(),
  jsxLocPlugin(),
  vitePluginManusRuntime(),
  vitePluginManusDebugCollector(),
  // Bundle analyzer - only during build when ANALYZE=true
  process.env.ANALYZE === "true"
    ? visualizer({ open: false, gzipSize: true })
    : null,
].filter(Boolean) as Plugin[];

export default defineConfig({
  plugins,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "shared"),
      "@assets": path.resolve(__dirname, "attached_assets"),
      "@fabric/platform-contract/clerk-defaults": path.resolve(__dirname, "../../packages/platform-contract/src/typescript/clerkDefaults.ts"),
    },
  },
  envDir: __dirname,
  root: __dirname,
  build: {
    outDir: path.resolve(__dirname, "dist/public"),
    emptyOutDir: true,
    chunkSizeWarningLimit: 500,
    reportCompressedSize: true,
    rollupOptions: {
      output: {
        manualChunks: id => {
          // TanStack Query
          if (id.includes("@tanstack/react-query")) {
            return "vendor-react-query";
          }
          // Radix UI components — merged into vendor-react to avoid circular chunk deps
          if (id.includes("@radix-ui")) {
            return "vendor-react";
          }
          // Charting libraries
          if (
            id.includes("recharts") ||
            id.includes("chart.js") ||
            id.includes("d3")
          ) {
            return "vendor-charts";
          }
          // HTTP client
          if (id.includes("axios")) {
            return "vendor-axios";
          }
          // Schema validation
          if (id.includes("zod")) {
            return "vendor-zod";
          }
          // React core (exact packages only — avoid @clerk/react, @radix-ui/react-*)
          if (id.includes("/react/") || id.includes("react-dom")) {
            return "vendor-react";
          }
        },
      },
    },
  },
  server: {
    port: 3001,
    strictPort: true, // Fail fast if port busy - ensures Playwright can connect
    host: true,
    watch: {
      ignored: [
        "**/e2e-results/**",
        "**/test-results/**",
        "**/playwright-report/**",
      ],
    },
    allowedHosts: [
      ".manuspre.computer",
      ".manus.computer",
      ".manus-asia.computer",
      ".manuscomputer.ai",
      ".manusvm.computer",
      ".bunnyenv.com",
      "localhost",
      "127.0.0.1",
    ],
    fs: {
      strict: true,
      deny: ["**/.*"],
      allow: [
        __dirname,
        WORKSPACE_ROOT,
        path.resolve(WORKSPACE_ROOT, "app"),
        path.resolve(WORKSPACE_ROOT, "apps/web"),
        "/workspace",
        "/workspace/apps/web",
        path.resolve(WORKSPACE_ROOT, "apps/web"),
        path.join(WORKSPACE_ROOT, "apps/web"),
        path.join(WORKSPACE_ROOT, "packages/platform-contract"),
        "/workspace/packages/platform-contract",
        path.resolve(__dirname, "../../packages/platform-contract/src"),
        path.resolve(__dirname, "../../packages/platform-contract/src/typescript"),
      ],
    },
    // Proxy configuration for multi-layer API routing.
    // Canonical rule: browser calls only /api/v1/*, which terminates at the API
    // gateway. The gateway is mounted at /v1 internally, so /api/v1 is rewritten
    // to /v1. Direct L1-L6 proxies are quarantined behind the explicit
    // VITE_PROXY_DEBUG_DIRECT_LAYERS flag and must not be used in normal app flows.
    // See canonical-paths-policy.md.
    proxy: (() => {
      const debugDirectLayers =
        frontendEnv.VITE_PROXY_DEBUG_DIRECT_LAYERS === "true";
      const rules: Record<string, ProxyOptions> = {};

      if (debugDirectLayers) {
        rules["/api/v1/ingest"] = {
          target: VITE_PROXY_L1_URL,
          changeOrigin: true,
          rewrite: (path: string) =>
            path.replace(/^\/api\/v1\/ingest/, "/api/v1/ingestion"),
        };
        rules["/api/v1/extract"] = {
          target: VITE_PROXY_L2_URL,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api\/v1\/extract/, ""),
        };
        rules["/api/v1/graph"] = {
          target: VITE_PROXY_L3_URL,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api\/v1\/graph/, "/v1"),
        };
        rules["/api/v1/audit"] = {
          target: VITE_PROXY_L4_URL,
          changeOrigin: true,
          rewrite: (path: string) =>
            path.replace(/^\/api\/v1\/audit/, "/v1/audit"),
        };
        rules["/api/v1/agents"] = {
          target: VITE_PROXY_L4_URL,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/api\/v1\/agents/, "/v1"),
        };
        rules["/api/v1/truths"] = {
          target: VITE_PROXY_L5_URL,
          changeOrigin: true,
          rewrite: (path: string) =>
            path.replace(/^\/api\/v1\/truths/, "/api/v1"),
        };
        rules["/api/v1/benchmarks"] = {
          target: VITE_PROXY_L6_URL,
          changeOrigin: true,
          rewrite: (path: string) =>
            path.replace(/^\/api\/v1\/benchmarks/, "/v1/benchmarks"),
        };
      }

      rules["/api/v1"] = {
        target: VITE_PROXY_API_GATEWAY_URL,
        changeOrigin: true,
        rewrite: (path: string) => path.replace(/^\/api\/v1/, "/v1"),
      };

      return rules;
    })(),
  },
  test: {
    environment: "jsdom",
    setupFiles: [path.resolve(__dirname, "test", "setup.ts")],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/api/generated/**",
        "src/main.tsx",
        "src/App.tsx",
        "src/const.ts",
        "src/api/types.ts",
        "src/shell/**",
        "src/pages/**",
        "src/components/**",
        "src/context/**",
        "src/contexts/**",
        "src/hooks/dil/**",
        "src/governance/**",
        "src/hooks/pages/**",
        "src/routes/**",
        "src/app/settings/**",
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        statements: 70,
        branches: 60,
      },
    },
  },
});
