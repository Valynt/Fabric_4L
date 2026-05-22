import { logError } from './telemetry';

export function reportFireAndForgetError(scope: string, error: unknown): void {
  logError('Unhandled async task failure', {
    scope,
    error: error instanceof Error ? error.message : String(error),
  });
}

export function safeAsync(task: Promise<unknown>, scope: string): void {
  task.catch((error) => reportFireAndForgetError(scope, error));
}
