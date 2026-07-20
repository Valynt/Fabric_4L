/**
 * Centralized Telemetry & Error Logging Service
 *
 * Single source of truth for all frontend observability:
 * - Environment-guarded console logging (dev only by default)
 * - Structured error capture with trace IDs
 * - Pluggable backend ready for Sentry/DataDog/etc.
 *
 * Usage:
 *   import { logError, captureException } from '@/lib/telemetry';
 *   logError('Failed to load value packs', { packId, statusCode });
 *   captureException(error, { traceId });
 */

type LogLevel = 'error' | 'warn' | 'info' | 'debug';
type TelemetryImportMetaEnv = {
  DEV?: boolean;
  PROD?: boolean;
  VITE_API_BASE?: string;
};
type ConsoleLike = Pick<typeof globalThis.console, LogLevel>;

export interface LogContext extends Record<string, unknown> {
  feature?: string;
  route?: string;
  accountId?: string | null;
  tenantId?: string | null;
  userId?: string | null;
  authPhase?: string;
  traceId?: string | null;
  statusCode?: number;
  errorCode?: string;
}

export type TelemetryContextDefaults = Omit<LogContext, 'feature'>;

function getImportMetaEnv(): TelemetryImportMetaEnv {
  return (import.meta as ImportMeta & { env?: TelemetryImportMetaEnv }).env ?? {};
}

/** Determine whether console logging should be emitted */
function isLoggingEnabled(): boolean {
  const env = getImportMetaEnv();
  return (
    env.DEV === true ||
    (typeof process !== 'undefined' && process.env?.NODE_ENV === 'development')
  );
}

/** Core logger — emits to console in dev, swallows in prod */
function log(level: LogLevel, message: string, context?: LogContext): void {
  if (!isLoggingEnabled()) return;

  const prefix = '[Fabric]';
  const args = context ? [prefix, message, context] : [prefix, message];
  const sink = globalThis['console'] as ConsoleLike | undefined;
  sink?.[level]?.(...args);
}

/** Log an error with optional structured context */
export function logError(message: string, context?: LogContext): void {
  log('error', message, context);
}

/** Log a warning with optional structured context */
export function logWarn(message: string, context?: LogContext): void {
  log('warn', message, context);
}

/** Log an info message with optional structured context */
export function logInfo(message: string, context?: LogContext): void {
  log('info', message, context);
}

/** Log a debug message with optional structured context */
export function logDebug(message: string, context?: LogContext): void {
  log('debug', message, context);
}

/**
 * Send error report to backend telemetry endpoint.
 * Uses navigator.sendBeacon for reliable delivery during page unload.
 * Exported for direct transport testing (same pattern as web-vitals sendToAnalytics).
 */
export function sendToTelemetryBackend(
  type: 'exception' | 'message',
  payload: { message: string; stack?: string; name?: string; level?: LogLevel; context?: LogContext }
): void {
  try {
    const API_BASE = getImportMetaEnv().VITE_API_BASE || '/api/v1';
    const data = JSON.stringify({
      type,
      timestamp: new Date().toISOString(),
      url: typeof window !== 'undefined' ? window.location.href : undefined, // navigation-guardrail: ignore - telemetry URL tracking, not navigation
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      ...payload,
    });

    // Use sendBeacon for reliable delivery even during page unload
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon(`${API_BASE}/telemetry/error`, new Blob([data], { type: 'application/json' }));
    } else if (typeof fetch !== 'undefined') {
      // Fallback: keepalive fetch stays unload-safe without blocking the main thread
      void fetch(`${API_BASE}/telemetry/error`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data,
        keepalive: true,
      }).catch(() => {
        // Silently fail - don't cause errors while reporting errors
      });
    }
  } catch {
    // Silently fail - don't cause errors while reporting errors
  }
}

/**
 * Capture an exception for telemetry.
 * In development: logs to console with stack trace.
 * In production: sends to backend telemetry endpoint via sendBeacon.
 */
export function captureException(error: Error, context?: LogContext): void {
  // Validate error is an actual Error instance
  if (!(error instanceof Error)) {
    logError('captureException called with non-Error value', { type: typeof error });
    return;
  }

  logError(error.message, {
    stack: error.stack,
    name: error.name,
    ...context,
  });

  if (getImportMetaEnv().PROD) {
    sendToTelemetryBackend('exception', {
      message: error.message,
      stack: error.stack,
      name: error.name,
      context,
    });
  }
}

/**
 * Capture a structured message for telemetry.
 * In development: logs to console.
 * In production: sends to backend telemetry endpoint via sendBeacon.
 */
export function captureMessage(
  message: string,
  level: LogLevel = 'info',
  context?: LogContext
): void {
  log(level, message, context);

  if (getImportMetaEnv().PROD) {
    sendToTelemetryBackend('message', {
      message,
      level,
      context,
    });
  }
}

/**
 * Create a namespaced logger for a module.
 * Produces messages like `[Fabric][useValuePacks] Deployment failed`.
 */
export function createLogger(module: string) {
  const prefix = `[Fabric][${module}]`;

  return {
    error: (message: string, context?: LogContext) =>
      log('error', `${prefix} ${message}`, context),
    warn: (message: string, context?: LogContext) =>
      log('warn', `${prefix} ${message}`, context),
    info: (message: string, context?: LogContext) =>
      log('info', `${prefix} ${message}`, context),
    debug: (message: string, context?: LogContext) =>
      log('debug', `${prefix} ${message}`, context),
  };
}

/**
 * Create a feature-scoped logger that automatically enriches telemetry context.
 */
export function createFeatureLogger(
  feature: string,
  defaults: TelemetryContextDefaults = {}
) {
  const logger = createLogger(feature);

  const withDefaults = (context?: LogContext): LogContext => ({
    feature,
    ...defaults,
    ...context,
  });

  return {
    error: (message: string, context?: LogContext) =>
      logger.error(message, withDefaults(context)),
    warn: (message: string, context?: LogContext) =>
      logger.warn(message, withDefaults(context)),
    info: (message: string, context?: LogContext) =>
      logger.info(message, withDefaults(context)),
    debug: (message: string, context?: LogContext) =>
      logger.debug(message, withDefaults(context)),
    child: (context: TelemetryContextDefaults) =>
      createFeatureLogger(feature, { ...defaults, ...context }),
  };
}
