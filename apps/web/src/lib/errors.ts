export interface NormalizedError {
  message: string;
  code?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function normalizeError(error: unknown, fallbackMessage = 'An unexpected error occurred'): NormalizedError {
  if (error instanceof Error) {
    return { message: error.message || fallbackMessage };
  }

  if (typeof error === 'string') {
    return { message: error };
  }

  if (isRecord(error)) {
    const message = typeof error.message === 'string' && error.message ? error.message : fallbackMessage;
    const code = typeof error.code === 'string' ? error.code : typeof error.statusCode === 'string' ? error.statusCode : undefined;

    return { message, code };
  }

  return { message: fallbackMessage };
}
