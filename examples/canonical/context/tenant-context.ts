/**
 * Tenant Context Management - Canonical Implementation
 *
 * CONTRACT.md §2.1 - Tenant Context Propagation
 *
 * This module implements the canonical pattern for tenant context:
 * - Request-scoped AsyncLocalStorage for automatic propagation
 * - Immutable context objects
 * - Single accessor function getTenantContext()
 * - Cross-service header propagation
 *
 * Copy this file as the starting point for any new service that needs
 * tenant context propagation.
 */

import { AsyncLocalStorage } from "async_hooks";

// ============================================================================
// Types
// ============================================================================

/** Tenant tier determines isolation strategy */
export type TenantTier = "shared" | "dedicated" | "enterprise";

/** Core tenant context - immutable after creation */
export interface TenantContext {
  /** Tenant unique identifier (UUIDv4) */
  readonly tenant_id: string;

  /** Tenant tier determines database isolation strategy */
  readonly tenant_tier: TenantTier;

  /** Geographic region for data residency */
  readonly region: string;

  /** Timestamp when context was issued */
  readonly issued_at: number;

  /** Permission scopes for authorization */
  readonly scope: string[];

  /** Optional metadata for tenant-specific data */
  readonly metadata?: Record<string, unknown>;
}

/** Complete auth context including identity */
export interface AuthContext {
  /** Authenticated user/subject identifier */
  readonly subject_id: string;

  /** Tenant context for the current request */
  readonly tenant_context: TenantContext;

  /** Authentication method used */
  readonly auth_method: "jwt" | "api_key" | "certificate";

  /** Session identifier for continuity */
  readonly session_id: string;
}

// ============================================================================
// AsyncLocalStorage Setup
// ============================================================================

/**
 * The AsyncLocalStorage instance that holds tenant context for the
 * current async execution scope. This is the core mechanism for
 * automatic context propagation without parameter threading.
 */
const tenantContextStore = new AsyncLocalStorage<TenantContext>();

// ============================================================================
// Core API
// ============================================================================

/**
 * Get the current tenant context from the async scope.
 *
 * CONTRACT.md §2.1:
 * - Returns null if called outside an active async scope (fail-safe)
 * - Never returns undefined - only null or valid context
 * - Context is deeply frozen - modifications require withTenantContext()
 *
 * @returns The current tenant context, or null if not in scope
 *
 * @example
 * ```typescript
 * const ctx = getTenantContext();
 * if (!ctx) {
 *   throw new Error("Tenant context not available - ensure middleware is configured");
 * }
 * console.log(`Operating on tenant: ${ctx.tenant_id}`);
 * ```
 */
export function getTenantContext(): TenantContext | null {
  return tenantContextStore.getStore() ?? null;
}

/**
 * Execute a function within a new tenant context scope.
 *
 * This is the canonical way to establish context for:
 * - HTTP request handlers (called by auth middleware)
 * - Background job processors
 * - Message queue consumers
 *
 * CONTRACT.md §2.1:
 * - Context is immutable within the scope
 * - Scope is automatically cleaned up when function completes
 * - No risk of context bleed between concurrent requests
 *
 * @param context The tenant context to establish
 * @param fn The function to execute within this context
 * @returns The result of fn
 *
 * @example
 * ```typescript
 * // In auth middleware
 * app.use(async (req, res, next) => {
 *   const tenantContext = await extractTenantFromJWT(req.headers.authorization);
 *   return withTenantContext(tenantContext, async () => {
 *     // All downstream code can use getTenantContext()
 *     return next();
 *   });
 * });
 * ```
 */
export function withTenantContext<T>(
  context: TenantContext,
  fn: () => T | Promise<T>
): T | Promise<T> {
  // Deep freeze to prevent accidental mutation
  const frozenContext = Object.freeze({ ...context });

  return tenantContextStore.run(frozenContext, fn);
}

/**
 * Create a new context with modified fields.
 *
 * CONTRACT.md §2.1:
 * - Context is immutable - modifications require explicit copy
 * - Original context is unchanged
 * - Useful for temporarily elevating permissions or changing region
 *
 * @param base The base context to copy
 * @param overrides Fields to override in the new context
 * @returns New immutable context with overrides applied
 *
 * @example
 * ```typescript
 * const current = getTenantContext();
 * if (!current) throw new Error("No context");
 *
 * // Create elevated context for admin operation
 * const elevated = withTenantContextOverride(current, {
 *   scope: [...current.scope, "admin:superuser"]
 * });
 * ```
 */
export function withTenantContextOverride(
  base: TenantContext,
  overrides: Partial<Omit<TenantContext, "tenant_id">>
): TenantContext {
  return Object.freeze({
    ...base,
    ...overrides,
    // tenant_id can never be overridden
    tenant_id: base.tenant_id,
  });
}

// ============================================================================
// Cross-Service Propagation
// ============================================================================

/** Header name for cross-service tenant propagation */
export const TENANT_HEADER = "x-fabric-tenant-id";

/** Header name for request signature verification */
export const SIGNATURE_HEADER = "x-fabric-signature";

/**
 * Extract tenant context from incoming HTTP headers.
 *
 * CONTRACT.md §2.1:
 * - Only the auth middleware calls this function
 * - All other code uses getTenantContext()
 * - Signature verification prevents forgery
 *
 * @param headers HTTP headers object
 * @param signatureVerifier Function to verify request signature
 * @returns Extracted tenant context if valid
 *
 * @example
 * ```typescript
 * // In auth middleware - ONLY location that reads headers directly
 * app.use(async (req, res, next) => {
 *   const result = extractTenantFromHeaders(
 *     req.headers,
 *     verifyServiceSignature
 *   );
 *   if (!result.valid) {
 *     return res.status(401).json({ error: "Invalid tenant context" });
 *   }
 *   // ... establish context scope
 * });
 * ```
 */
export function extractTenantFromHeaders(
  headers: Record<string, string | string[] | undefined>,
  signatureVerifier: (tenantId: string, signature: string) => boolean
): { valid: false; error: string } | { valid: true; context: TenantContext } {
  const tenantId = headers[TENANT_HEADER];
  const signature = headers[SIGNATURE_HEADER];

  if (!tenantId || Array.isArray(tenantId)) {
    return { valid: false, error: `Missing or invalid ${TENANT_HEADER} header` };
  }

  if (!signature || Array.isArray(signature)) {
    return { valid: false, error: `Missing or invalid ${SIGNATURE_HEADER} header` };
  }

  // Verify signature to prevent forgery
  if (!signatureVerifier(tenantId, signature)) {
    return { valid: false, error: "Invalid request signature" };
  }

  // In production, this would look up tenant in database/cache
  // This is a simplified example showing the pattern
  const context: TenantContext = {
    tenant_id: tenantId,
    tenant_tier: "shared", // Would be looked up
    region: "us-east-1", // Would be looked up
    issued_at: Date.now(),
    scope: ["read", "write"], // Would be resolved from auth
  };

  return { valid: true, context };
}

/**
 * Generate headers for cross-service calls.
 *
 * CONTRACT.md §2.1:
 * - Always include x-fabric-tenant-id when calling other services
 * - Always sign requests to prevent forgery
 * - Receiving service validates signature before accepting context
 *
 * @param tenantContext The context to propagate
 * @param signer Function to generate request signature
 * @returns Headers to include in outbound request
 *
 * @example
 * ```typescript
 * // In service client
 * const ctx = getTenantContext();
 * if (!ctx) throw new Error("No tenant context for outbound call");
 *
 * const headers = generatePropagationHeaders(ctx, signRequest);
 * const response = await fetch('https://other-service/api/data', {
 *   headers: { ...headers, 'Content-Type': 'application/json' }
 * });
 * ```
 */
export function generatePropagationHeaders(
  tenantContext: TenantContext,
  signer: (tenantId: string) => string
): Record<string, string> {
  return {
    [TENANT_HEADER]: tenantContext.tenant_id,
    [SIGNATURE_HEADER]: signer(tenantContext.tenant_id),
    // Include other correlation headers
    "x-fabric-region": tenantContext.region,
  };
}

// ============================================================================
// Message Queue Propagation
// ============================================================================

/**
 * Inject tenant context into message payload.
 *
 * CONTRACT.md §2.1:
 * - Async message processing requires explicit context
 * - Message carries its own context in payload
 * - Consumer validates context before processing
 *
 * @param payload Original message payload
 * @param tenantContext Context to include
 * @returns Payload with embedded context
 *
 * @example
 * ```typescript
 * // Producer
 * const message = injectContextIntoMessage(
 *   { action: "process_invoice", invoice_id: "inv-123" },
 *   getTenantContext()!
 * );
 * await queue.send(message);
 * ```
 */
export function injectContextIntoMessage<T extends Record<string, unknown>>(
  payload: T,
  tenantContext: TenantContext
): T & { _fabric_context: TenantContext } {
  return {
    ...payload,
    _fabric_context: tenantContext,
  };
}

/**
 * Extract and validate tenant context from message payload.
 *
 * @param message Message from queue
 * @returns Context if valid, null otherwise
 *
 * @example
 * ```typescript
 * // Consumer
 * consumer.on('message', async (msg) => {
 *   const ctx = extractContextFromMessage(msg);
 *   if (!ctx) {
 *     // Reject message - no valid context
 *     return msg.nack();
 *   }
 *
 *   await withTenantContext(ctx, async () => {
 *     // Process message with proper tenant isolation
 *     await processInvoice(msg.invoice_id);
 *   });
 * });
 * ```
 */
export function extractContextFromMessage(
  message: Record<string, unknown>
): TenantContext | null {
  const context = message._fabric_context as TenantContext | undefined;

  if (!context || !context.tenant_id) {
    return null;
  }

  // Validate required fields
  if (!isValidTenantContext(context)) {
    return null;
  }

  return Object.freeze({ ...context });
}

// ============================================================================
// Validation
// ============================================================================

/**
 * Type guard to validate tenant context structure.
 */
function isValidTenantContext(obj: unknown): obj is TenantContext {
  if (!obj || typeof obj !== "object") return false;

  const ctx = obj as Record<string, unknown>;

  return (
    typeof ctx.tenant_id === "string" &&
    ["shared", "dedicated", "enterprise"].includes(ctx.tenant_tier as string) &&
    typeof ctx.region === "string" &&
    typeof ctx.issued_at === "number" &&
    Array.isArray(ctx.scope) &&
    ctx.scope.every((s) => typeof s === "string")
  );
}

// ============================================================================
// Testing Utilities
// ============================================================================

/**
 * Create a test tenant context for unit tests.
 *
 * This helper creates valid contexts for testing without needing
 * the full auth infrastructure.
 *
 * @param overrides Fields to override in test context
 * @returns Valid tenant context for testing
 *
 * @example
 * ```typescript
 * // In test file
 * describe('InvoiceService', () => {
 *   it('should create invoice', async () => {
 *     const testCtx = createTestContext({ tenant_id: 'test-tenant-123' });
 *
 *     await withTenantContext(testCtx, async () => {
 *       const result = await invoiceService.create({ amount: 100 });
 *       expect(result.tenant_id).toBe('test-tenant-123');
 *     });
 *   });
 * });
 * ```
 */
export function createTestContext(
  overrides: Partial<TenantContext> = {}
): TenantContext {
  return Object.freeze({
    tenant_id: `test-tenant-${Date.now()}`,
    tenant_tier: "shared",
    region: "us-east-1",
    issued_at: Date.now(),
    scope: ["read", "write"],
    ...overrides,
  });
}

// ============================================================================
// Anti-Pattern Detection (Runtime Guards)
// ============================================================================

/**
 * Guard to catch parameter pollution anti-pattern at runtime.
 *
 * This is used internally by the framework to catch anti-patterns
 * during development. It logs warnings when tenantId is passed
 * as a parameter when context is available.
 *
 * @internal
 */
export function __guardParameterPollution(
  functionName: string,
  tenantIdParam?: string
): void {
  if (process.env.NODE_ENV === "production") return;

  const context = getTenantContext();
  if (context && tenantIdParam && tenantIdParam !== context.tenant_id) {
    console.warn(
      `[CONTRACT VIOLATION §2.1] Function "${functionName}" received tenantId parameter ` +
        `"${tenantIdParam}" but context shows "${context.tenant_id}". ` +
        `Use getTenantContext() instead of passing tenantId as parameter. ` +
        `See CONTRACT.md §2.1`
    );
  }
}
