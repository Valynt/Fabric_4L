import { jsxLocPlugin } from "@builder.io/vite-plugin-jsx-loc";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin, type ViteDevServer } from "vite";
import { vitePluginManusRuntime } from "vite-plugin-manus-runtime";
import { visualizer } from "rollup-plugin-visualizer";

// =============================================================================
// Manus Debug Collector - Vite Plugin
// Writes browser logs directly to files, trimmed when exceeding size limit
// =============================================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = __dirname;
const LOG_DIR = path.join(PROJECT_ROOT, ".manus-logs");
const MAX_LOG_SIZE_BYTES = 1 * 1024 * 1024; // 1MB per log file
const TRIM_TARGET_BYTES = Math.floor(MAX_LOG_SIZE_BYTES * 0.6); // Trim to 60% to avoid constant re-trimming
const VITE_PROXY_L1_URL = process.env.VITE_PROXY_L1_URL || "http://localhost:8001";
const VITE_PROXY_L2_URL = process.env.VITE_PROXY_L2_URL || "http://localhost:8002";
const VITE_PROXY_L3_URL = process.env.VITE_PROXY_L3_URL || "http://localhost:8003";
const VITE_PROXY_L4_URL =
  process.env.INTERNAL_L4_PROXY_URL ||
  process.env.VITE_PROXY_L4_URL ||
  "http://localhost:8004";
const VITE_PROXY_L5_URL = process.env.VITE_PROXY_L5_URL || "http://localhost:8005";
const VITE_PROXY_L6_URL = process.env.VITE_PROXY_L6_URL || "http://localhost:8006";

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
  const isUnknownArray = (candidate: unknown): candidate is unknown[] => candidate === undefined || Array.isArray(candidate);
  return isUnknownArray(payload.consoleLogs)
    && isUnknownArray(payload.networkRequests)
    && isUnknownArray(payload.sessionEvents);
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
  const lines = entries.map((entry) => {
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
          const payloadType = typeof rawPayload.type === "string" ? rawPayload.type : "unknown";
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
          if (payload.consoleLogs?.length > 0) {
            writeToLogFile("browserConsole", payload.consoleLogs);
          }
          if (payload.networkRequests?.length > 0) {
            writeToLogFile("networkRequests", payload.networkRequests);
          }
          if (payload.sessionEvents?.length > 0) {
            writeToLogFile("sessionReplay", payload.sessionEvents);
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
        req.on("data", (chunk) => {
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
  process.env.ANALYZE === "true" ? visualizer({ open: false, gzipSize: true }) : null,
].filter(Boolean) as Plugin[];

export default defineConfig({
  plugins,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "shared"),
      "@assets": path.resolve(__dirname, "attached_assets"),
    },
  },
  envDir: __dirname,
  root: __dirname,
  build: {
    outDir: path.resolve(__dirname, "dist/public"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // TanStack Query
          if (id.includes('@tanstack/react-query')) {
            return 'vendor-react-query';
          }
          // Radix UI components — merged into vendor-react to avoid circular chunk deps
          if (id.includes('@radix-ui')) {
            return 'vendor-react';
          }
          // Charting libraries
          if (id.includes('recharts') || id.includes('chart.js') || id.includes('d3')) {
            return 'vendor-charts';
          }
          // HTTP client
          if (id.includes('axios')) {
            return 'vendor-axios';
          }
          // Schema validation
          if (id.includes('zod')) {
            return 'vendor-zod';
          }
          // React core (exact packages only — avoid @clerk/react, @radix-ui/react-*)
          if (id.includes('/react/') || id.includes('react-dom')) {
            return 'vendor-react';
          }
        },
      },
    },
  },
  server: {
    port: 3001,
    strictPort: true, // Fail fast if port busy - ensures Playwright can connect
    host: true,
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
    },
    // Proxy configuration for multi-layer API routing
    // Each layer runs on a different port; unified under /api/v1 for future gateway compatibility
    proxy: {
      '/api/v1/ingest': {
        target: VITE_PROXY_L1_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/ingest/, '/api/v1/ingestion'),
      },
      '/api/v1/extract': {
        target: VITE_PROXY_L2_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/extract/, ''),
      },
      '/api/v1/graph': {
        target: VITE_PROXY_L3_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/graph/, '/v1'),
      },
      '/api/v1/audit': {
        target: VITE_PROXY_L4_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/audit/, '/v1/audit'),
      },
      '/api/v1/agents': {
        target: VITE_PROXY_L4_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/agents/, '/v1'),
      },
      '/api/v1/truths': {
        target: VITE_PROXY_L5_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/truths/, '/api/v1'),
      },
      '/api/v1/benchmarks': {
        target: VITE_PROXY_L6_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1\/benchmarks/, '/v1/benchmarks'),
      },
    },
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

