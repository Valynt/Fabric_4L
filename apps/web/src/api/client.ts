import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";
import axiosRetry from "axios-retry";
import { z } from "zod";
import { createFeatureLogger } from "@/lib/telemetry";
import { sessionService } from "@/services/sessionService";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { getClerkSessionToken } from "@/auth/clerkSession";

/**
 * Validate that a Clerk-issued session token is safe to embed in an HTTP
 * header. Rejects:
 *   - empty / whitespace-only values
 *   - values containing CR (\r), LF (\n), or any ASCII control char (0x00-0x1F, 0x7F)
 *     to defeat header-injection attempts via a compromised/malformed token.
 *
 * Returns the trimmed token when safe, otherwise null.
 *
 * SECURITY: this is defense-in-depth. Clerk should never issue a token with
 * these characters, but a malicious extension, a misconfigured JWT template,
 * or a future runtime regression could. The cost of validating is trivial;
 * the cost of a header-injection bug is not.
 */
function sanitizeBearerToken(raw: string | null | undefined): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;
  // Reject CR, LF, and all C0/C1 control characters (incl. DEL).
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001F\u007F]/.test(trimmed)) return null;
  return trimmed;
}

const log = createFeatureLogger("api-client");
const SKIP_AUTH_REDIRECT_HEADER = "X-Fabric-Skip-Auth-Redirect";

function shouldSkipAuthRedirect(headers: unknown): boolean {
  if (!headers || typeof headers !== "object") {
    return false;
  }

  const maybeAxiosHeaders = headers as {
    get?: (name: string) => unknown;
  };

  if (typeof maybeAxiosHeaders.get === "function") {
    const value =
      maybeAxiosHeaders.get(SKIP_AUTH_REDIRECT_HEADER) ??
      maybeAxiosHeaders.get(SKIP_AUTH_REDIRECT_HEADER.toLowerCase());
    return value === "1" || value === 1 || value === true || value === "true";
  }

  const plainHeaders = headers as Record<string, unknown>;
  for (const [key, value] of Object.entries(plainHeaders)) {
    if (key.toLowerCase() === SKIP_AUTH_REDIRECT_HEADER.toLowerCase()) {
      return value === "1" || value === 1 || value === true || value === "true";
    }
  }

  return false;
}

// ============================================================================
// MANDATE 4: INPUT VALIDATION - Runtime validation schemas
// ============================================================================

/** Valid layer keys - single source of truth */
const VALID_LAYER_KEYS = [
  "api",
  "l1",
  "l2",
  "l2_5",
  "l3",
  "l4",
  "l5",
  "l6",
] as const;

/** Zod schema for layer key validation */
const LayerKeySchema = z.enum(VALID_LAYER_KEYS);
export type LayerKey = z.infer<typeof LayerKeySchema>;

/** API path validation - must start with / */
const ApiPathSchema = z.string().regex(/^\//, "API path must start with /");

/** Backend error response schema - canonical ErrorEnvelope plus legacy FastAPI detail fallback. */
const ErrorResponseSchema = z.object({
  error: z
    .object({
      code: z.string().min(1),
      message: z.string(),
      request_id: z.string().min(1),
      details: z.record(z.string(), z.unknown()).nullable().optional(),
    })
    .optional(),
  // FastAPI validation errors use `detail` when a service has not installed the shared handler.
  detail: z
    .union([
      z.string(),
      z.array(
        z.object({
          loc: z.array(z.unknown()),
          msg: z.string(),
          type: z.string(),
        })
      ),
      z.unknown(),
    ])
    .optional(),
});

type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

/** Extract a human-readable message from a FastAPI detail field */
function extractDetailMessage(detail: ErrorResponse["detail"]): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map(d => {
        if (typeof d === "object" && d !== null && "msg" in d) {
          return String((d as { msg: unknown }).msg);
        }
        return JSON.stringify(d);
      })
      .join("; ");
  }
  return null;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const key = `${name}=`;
  const match = document.cookie.split("; ").find(part => part.startsWith(key));
  return match ? decodeURIComponent(match.slice(key.length)) : null;
}

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

// ============================================================================
// Environment Configuration with Validation
// ============================================================================

function isProductionApiConfig(): boolean {
  return import.meta.env.PROD || import.meta.env.VITE_APP_ENV === "production";
}

const API_ENV_VALUES: Record<string, string | undefined> = {
  VITE_API_VERSION_PREFIX: import.meta.env.VITE_API_VERSION_PREFIX,
  VITE_API_BASE: import.meta.env.VITE_API_BASE,
  VITE_LAYER1_ROUTE_PREFIX: import.meta.env.VITE_LAYER1_ROUTE_PREFIX,
  VITE_L1_PREFIX: import.meta.env.VITE_L1_PREFIX,
  VITE_LAYER2_ROUTE_PREFIX: import.meta.env.VITE_LAYER2_ROUTE_PREFIX,
  VITE_L2_PREFIX: import.meta.env.VITE_L2_PREFIX,
  VITE_LAYER2_5_ROUTE_PREFIX: import.meta.env.VITE_LAYER2_5_ROUTE_PREFIX,
  VITE_L2_5_PREFIX: import.meta.env.VITE_L2_5_PREFIX,
  VITE_LAYER3_ROUTE_PREFIX: import.meta.env.VITE_LAYER3_ROUTE_PREFIX,
  VITE_L3_PREFIX: import.meta.env.VITE_L3_PREFIX,
  VITE_LAYER4_ROUTE_PREFIX: import.meta.env.VITE_LAYER4_ROUTE_PREFIX,
  VITE_L4_PREFIX: import.meta.env.VITE_L4_PREFIX,
  VITE_LAYER5_ROUTE_PREFIX: import.meta.env.VITE_LAYER5_ROUTE_PREFIX,
  VITE_L5_PREFIX: import.meta.env.VITE_L5_PREFIX,
  VITE_LAYER6_ROUTE_PREFIX: import.meta.env.VITE_LAYER6_ROUTE_PREFIX,
  VITE_L6_PREFIX: import.meta.env.VITE_L6_PREFIX,
};

/** Get an API environment variable with development/test fallbacks only. */
function getApiEnvVar(
  names: readonly string[],
  fallback: string,
  label: string
): string {
  for (const name of names) {
    const value = API_ENV_VALUES[name];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }

  if (isProductionApiConfig()) {
    throw new Error(
      `${label} is required in production frontend builds. Set one of: ${names.join(", ")}.`
    );
  }

  log.warn(`API environment variable not set, using non-production fallback`, {
    names,
    fallback,
  });
  return fallback;
}

// Canonical routing/versioning matrix:
// docs/reference/service-routing-and-api-version-matrix.md
// Shared gateway API version prefix.
const API_VERSION_PREFIX = getApiEnvVar(
  ["VITE_API_VERSION_PREFIX", "VITE_API_BASE"],
  "/api/v1",
  "Gateway API version prefix"
);

// Layer route prefixes (aligned with matrix terminology; legacy VITE_L*_PREFIX still supported)
const LAYER_PREFIXES = {
  api: getApiEnvVar(
    ["VITE_API_ROUTE_PREFIX"],
    "",
    "API gateway route prefix"
  ),
  l1: getApiEnvVar(
    ["VITE_LAYER1_ROUTE_PREFIX", "VITE_L1_PREFIX"],
    "/ingest",
    "Layer 1 route prefix"
  ),
  l2: getApiEnvVar(
    ["VITE_LAYER2_ROUTE_PREFIX", "VITE_L2_PREFIX"],
    "/extract",
    "Layer 2 route prefix"
  ),
  l2_5: getApiEnvVar(
    ["VITE_LAYER2_5_ROUTE_PREFIX", "VITE_L2_5_PREFIX"],
    "/signals",
    "Layer 2.5 route prefix"
  ),
  l3: getApiEnvVar(
    ["VITE_LAYER3_ROUTE_PREFIX", "VITE_L3_PREFIX"],
    "/graph",
    "Layer 3 route prefix"
  ),
  l4: getApiEnvVar(
    ["VITE_LAYER4_ROUTE_PREFIX", "VITE_L4_PREFIX"],
    "/agents",
    "Layer 4 route prefix"
  ),
  l5: getApiEnvVar(
    ["VITE_LAYER5_ROUTE_PREFIX", "VITE_L5_PREFIX"],
    "/truths",
    "Layer 5 route prefix"
  ),
  l6: getApiEnvVar(
    ["VITE_LAYER6_ROUTE_PREFIX", "VITE_L6_PREFIX"],
    "/benchmarks",
    "Layer 6 route prefix"
  ),
} as const;

/**
 * Generate a request correlation ID for tracing
 */
function generateRequestId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return `req_${crypto.randomUUID()}`;
  }
  // Fallback for rare legacy runtimes
  return `req_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export interface ApiFetchInitOptions extends Omit<
  RequestInit,
  "headers" | "method"
> {
  headers?: Record<string, string>;
  method?: string;
}

export function buildApiFetchInit({
  headers = {},
  method = "GET",
  credentials = "include",
  ...rest
}: ApiFetchInitOptions = {}): RequestInit {
  const normalizedMethod = method.toUpperCase();
  const mergedHeaders: Record<string, string> = {
    ...headers,
    "X-Request-ID": headers["X-Request-ID"] ?? generateRequestId(),
  };

  if (
    MUTATING_METHODS.has(normalizedMethod) &&
    !mergedHeaders["X-CSRF-Token"]
  ) {
    const csrfToken = getCookie("vf_csrf_token");
    if (csrfToken) {
      mergedHeaders["X-CSRF-Token"] = csrfToken;
    }
  }

  return {
    ...rest,
    method: normalizedMethod,
    credentials,
    headers: mergedHeaders,
  };
}

/**
 * Custom API error class with trace ID support
 */
export class ApiError extends Error {
  public traceId: string | null;
  public statusCode: number;
  public errorCode: string;

  constructor(
    message: string,
    statusCode: number = 500,
    errorCode: string = "INTERNAL_ERROR",
    traceId: string | null = null
  ) {
    super(message);
    this.name = "ApiError";
    this.traceId = traceId;
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}

/**
 * Request deduplication cache entry
 * Stores in-flight promise to be shared by duplicate requests
 */
interface InFlightRequest<T> {
  promise: Promise<T>;
  timestamp: number;
}

class ApiClient {
  private clients: Map<LayerKey, AxiosInstance> = new Map();
  // PERF: Request deduplication - share in-flight promises for identical requests
  private inFlightRequests: Map<string, InFlightRequest<unknown>> = new Map();
  // Maximum age for in-flight request entries (prevents memory leaks)
  private readonly DEDUPE_TTL_MS = 30000;
  private cleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.initializeClients();
    // Cleanup stale entries periodically
    this.cleanupInterval = setInterval(
      () => this.cleanupStaleRequests(),
      this.DEDUPE_TTL_MS
    );
  }

  /**
   * Destroy the ApiClient instance and clean up resources.
   * Call this in tests and during hot-reload to prevent interval leaks.
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.inFlightRequests.clear();
    this.clients.clear();
  }

  /**
   * Cleanup stale in-flight request entries to prevent memory leaks
   */
  private cleanupStaleRequests(): void {
    const now = Date.now();
    const entries = Array.from(this.inFlightRequests.entries());
    for (const [key, entry] of entries) {
      if (now - entry.timestamp > this.DEDUPE_TTL_MS) {
        this.inFlightRequests.delete(key);
      }
    }
  }

  /**
   * Generate unique key for safe request deduplication.
   * GET dedupe intentionally ignores request bodies because GET requests must not rely on one.
   */
  private getRequestKey(layer: LayerKey, method: string, path: string): string {
    return `${layer}:${method}:${path}`;
  }

  private trackInFlight<T>(
    requestKey: string,
    promise: Promise<T>
  ): Promise<T> {
    this.inFlightRequests.set(requestKey, {
      promise,
      timestamp: Date.now(),
    });

    // Cleanup when complete without creating a secondary unhandled rejection.
    void promise
      .finally(() => {
        this.inFlightRequests.delete(requestKey);
      })
      .catch(() => undefined);

    return promise;
  }

  private initializeClients() {
    (Object.keys(LAYER_PREFIXES) as LayerKey[]).forEach(layer => {
      const client = axios.create({
        baseURL: `${API_VERSION_PREFIX}${LAYER_PREFIXES[layer]}`,
        withCredentials: true,
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 30000,
      });

      // Configure retry: 3 attempts with exponential delay for transient errors
      axiosRetry(client, {
        retries: 3,
        retryDelay: axiosRetry.exponentialDelay,
        retryCondition: error => {
          // Retry on network errors, 5xx responses, and rate-limiting (429)
          // so the client can recover from transient infrastructure failures.
          const status = error.response?.status;
          return (
            axiosRetry.isNetworkOrIdempotentRequestError(error) ||
            (status !== undefined && status >= 500) ||
            status === 429
          );
        },
      });

      client.interceptors.request.use(
        async config => {
          // Add correlation ID for request tracing
          config.headers["X-Request-ID"] = generateRequestId();
          // Tenant identity must be resolved server-side from authenticated context.
          // Do not send client-controlled tenant headers from browser code.

          // Phase 2 Clerk integration: when AUTH_PROVIDER=clerk, attach a
          // fresh Clerk session JWT as Bearer. The gateway verifies and
          // re-emits as a Fabric4L envelope; downstream services trust only
          // that envelope, never this header.
          //
          // The legacy path is preserved for AUTH_PROVIDER=legacy: the
          // httpOnly vf_session cookie is sent automatically via
          // withCredentials: true and no Authorization header is set.
          //
          // SECURITY: the browser never asserts tenant identity. We do NOT
          // send X-Tenant-ID or any equivalent hint header from the client.
          // The Fabric4L gateway derives tenant from the verified JWT or
          // session envelope; that is the sole source of tenant authority.
          if (isClerkAuthEnabled()) {
            const rawToken = await getClerkSessionToken();
            const safeToken = sanitizeBearerToken(rawToken);
            if (safeToken) {
              config.headers["Authorization"] = `Bearer ${safeToken}`;
            }
          }

          const method = (config.method ?? "get").toUpperCase();
          if (MUTATING_METHODS.has(method)) {
            const csrfToken = getCookie("vf_csrf_token");
            if (csrfToken) {
              config.headers["X-CSRF-Token"] = csrfToken;
            }
          }

          return config;
        },
        (error: AxiosError) => {
          // MANDATE 3: ERROR HANDLING COMPLETENESS - Log request errors with context
          log.error("Request interceptor error", {
            message: error.message,
            code: error.code,
            stack: error.stack,
          });
          return Promise.reject(error);
        }
      );

      client.interceptors.response.use(
        response => response,
        (error: AxiosError) => {
          // MANDATE 2: TYPE SAFETY - Runtime validation with Zod instead of `as` assertion
          const parseResult = ErrorResponseSchema.safeParse(
            error.response?.data
          );
          const errorData: ErrorResponse = parseResult.success
            ? parseResult.data
            : {};

          // MANDATE 1: NULL/UNDEFINED SAFETY - Optional chaining with nullish coalescing
          const traceId =
            (typeof error.response?.headers["x-request-id"] === "string"
              ? error.response.headers["x-request-id"]
              : null) ??
            errorData.error?.request_id ??
            null;

          const skipAuthRedirect = shouldSkipAuthRedirect(error.config?.headers);

          if (error.response?.status === 401 && !skipAuthRedirect) {
            sessionService.handleUnauthorized({
              route:
                typeof window !== "undefined"
                  ? window.location.pathname
                  : undefined,
              traceId,
            });
          }

          if (error.response?.status === 403 && !skipAuthRedirect) {
            sessionService.handleForbidden({
              route:
                typeof window !== "undefined"
                  ? window.location.pathname
                  : undefined,
              traceId,
            });
          }

          // MANDATE 3: Log error with full context for debugging
          log.error("API request failed", {
            url: error.config?.url,
            method: error.config?.method,
            status: error.response?.status,
            errorCode: errorData.error?.code,
            traceId,
            message: error.message,
          });

          // Transform to ApiError with trace ID for ErrorBoundary.
          // Prefer `detail` (FastAPI format) over generic `message` for richer error messages.
          const detailMessage = extractDetailMessage(errorData.detail);
          const apiError = new ApiError(
            detailMessage ??
              errorData.error?.message ??
              error.message ??
              "API request failed",
            error.response?.status ?? 500,
            errorData.error?.code ?? "INTERNAL_ERROR",
            traceId
          );

          throw apiError;
        }
      );

      this.clients.set(layer, client);
    });
  }

  /**
   * MANDATE 4: INPUT VALIDATION - Get client for layer with fail-fast validation
   * @throws {TypeError} If layer is invalid
   * @throws {Error} If client not initialized for valid layer
   */
  getClient(layer: LayerKey): AxiosInstance {
    // Validate layer key at runtime
    const validation = LayerKeySchema.safeParse(layer);
    if (!validation.success) {
      const error = new TypeError(
        `Invalid layer key: ${String(layer)}. Must be one of: ${VALID_LAYER_KEYS.join(", ")}`
      );
      log.error("Layer validation failed", { layer, error: error.message });
      throw error;
    }

    const client = this.clients.get(layer);
    if (!client) {
      const error = new Error(`API client for layer ${layer} not initialized`);
      log.error("Client lookup failed", { layer, error: error.message });
      throw error;
    }
    return client;
  }

  // MANDATE 4: INPUT VALIDATION - All HTTP methods validate path starts with /
  // PERF: Request deduplication applied to GET requests
  async get<T = unknown>(
    layer: LayerKey,
    path: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const validatedPath = ApiPathSchema.parse(path);
    const requestKey = this.getRequestKey(layer, "GET", validatedPath);

    // Check for existing in-flight request
    const existing = this.inFlightRequests.get(requestKey);
    if (existing) {
      log.warn("Deduplicating identical in-flight GET request", {
        path: validatedPath,
        layer,
      });
      return existing.promise as Promise<AxiosResponse<T>>;
    }

    return this.trackInFlight(
      requestKey,
      this.getClient(layer).get(validatedPath, config)
    );
  }

  async post<T = unknown>(
    layer: LayerKey,
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const validatedPath = ApiPathSchema.parse(path);
    return this.getClient(layer).post(validatedPath, data, config);
  }

  async put<T = unknown>(
    layer: LayerKey,
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const validatedPath = ApiPathSchema.parse(path);
    return this.getClient(layer).put(validatedPath, data, config);
  }

  async patch<T = unknown>(
    layer: LayerKey,
    path: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const validatedPath = ApiPathSchema.parse(path);
    return this.getClient(layer).patch(validatedPath, data, config);
  }

  async delete<T = unknown>(
    layer: LayerKey,
    path: string,
    config?: AxiosRequestConfig
  ): Promise<AxiosResponse<T>> {
    const validatedPath = ApiPathSchema.parse(path);
    return this.getClient(layer).delete(validatedPath, config);
  }
}

export const apiClient = new ApiClient();
export { LAYER_PREFIXES };
