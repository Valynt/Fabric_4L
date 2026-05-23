import { captureException, logError } from './telemetry';

export function reportFireAndForgetError(scope: string, error: unknown): void {
  if (error instanceof Error) {
    captureException(error, { scope });
  } else {
    logError('Unhandled async task failure', {
      scope,
      error: String(error),
    });
  }
}

export function safeAsync(task: Promise<unknown> | unknown, scope: string): void {
  if (task && typeof (task as Promise<unknown>).catch === 'function') {
    (task as Promise<unknown>).catch((error) => reportFireAndForgetError(scope, error));
  }
}
