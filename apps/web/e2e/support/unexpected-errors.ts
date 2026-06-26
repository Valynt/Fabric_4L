import type { ConsoleMessage, Page, Request, Response } from '@playwright/test';

type UnexpectedErrorAuditOptions = {
  allowConsoleErrorPatterns?: RegExp[];
  allowHttp5xxPatterns?: RegExp[];
  allowUnhandledApiRequests?: boolean;
};

type UnexpectedErrorAudit = {
  recordExpectedHttp5xxPattern: (pattern: string | RegExp) => void;
  recordUnhandledApiRequest: (request: { method: string; url: string }) => void;
  assertClean: () => Promise<void>;
  teardown: () => void;
};

const IGNORED_CONSOLE_ERRORS = [
  /favicon\.ico/i,
  /ResizeObserver loop/i,
  /Failed to load resource: the server responded with a status of 40[14] /i,
];

const FAILED_JOB_STATUS_PATTERN = /\b(failed|error|cancelled)\b/i;
const JOB_URL_PATTERN = /\/api\/v1\/(?:ingest\/jobs|agents\/workflows|agents\/harness\/runs)/i;
const FAILING_RESOURCE_ERROR_PATTERN = /ERR_NAME_NOT_RESOLVED/i;

export function attachUnexpectedErrorAudit(
  page: Page,
  options: UnexpectedErrorAuditOptions = {},
): UnexpectedErrorAudit {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const http5xx: string[] = [];
  const failedJobs: string[] = [];
  const failedResourceRequests: string[] = [];
  const unhandledApiRequests: string[] = [];
  const expectedHttp5xxPatterns = [...(options.allowHttp5xxPatterns ?? [])];

  const onPageError = (error: Error) => {
    pageErrors.push(error.stack || error.message);
  };

  const onConsole = (message: ConsoleMessage) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (IGNORED_CONSOLE_ERRORS.some((pattern) => pattern.test(text))) return;
    if ((options.allowConsoleErrorPatterns ?? []).some((pattern) => pattern.test(text))) return;
    consoleErrors.push(text);
  };

  const onResponse = async (response: Response) => {
    const url = response.url();
    const status = response.status();
    if (status >= 500 && !matchesAny(url, expectedHttp5xxPatterns)) {
      http5xx.push(`${status} ${url}`);
    }

    if (JOB_URL_PATTERN.test(url) && status < 500) {
      await recordFailedJobIfPresent(response, failedJobs);
    }
  };

  const onRequestFailed = (request: Request) => {
    const failure = request.failure();
    const errorText = failure?.errorText ?? '';
    if (!FAILING_RESOURCE_ERROR_PATTERN.test(errorText)) return;
    const url = request.url();
    if (IGNORED_CONSOLE_ERRORS.some((pattern) => pattern.test(url))) return;
    failedResourceRequests.push(`${request.method()} ${url} ${errorText}`);
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);
  page.on('response', onResponse);
  page.on('requestfailed', onRequestFailed);

  return {
    recordExpectedHttp5xxPattern: (pattern: string | RegExp) => {
      expectedHttp5xxPatterns.push(toRegExp(pattern));
    },
    recordUnhandledApiRequest: ({ method, url }) => {
      if (!options.allowUnhandledApiRequests) {
        unhandledApiRequests.push(`${method} ${url}`);
      }
    },
    assertClean: async () => {
      const failures = [
        ...pageErrors.map((error) => `unexpected page error: ${error}`),
        ...consoleErrors.map((error) => `unexpected console error: ${error}`),
        ...failedResourceRequests.map((error) => `unexpected failed resource request: ${error}`),
        ...http5xx.map((error) => `unexpected HTTP 5xx response: ${error}`),
        ...failedJobs.map((error) => `unexpected failed background job: ${error}`),
        ...unhandledApiRequests.map((error) => `unhandled mocked API request: ${error}`),
      ];
      if (failures.length > 0) {
        throw new Error(`Unexpected browser/test errors detected:\n- ${failures.join('\n- ')}`);
      }
    },
    teardown: () => {
      page.off('pageerror', onPageError);
      page.off('console', onConsole);
      page.off('response', onResponse);
      page.off('requestfailed', onRequestFailed);
    },
  };
}

function matchesAny(value: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(value));
}

function toRegExp(pattern: string | RegExp): RegExp {
  if (pattern instanceof RegExp) return pattern;
  return globToRegExp(pattern);
}

function globToRegExp(glob: string): RegExp {
  const escaped = glob
    .replace(/[.+^${}()|[\]\\]/g, '\\$&')
    .replace(/\*\*/g, '.*')
    .replace(/\*/g, '[^/]*');
  return new RegExp(escaped);
}

async function recordFailedJobIfPresent(response: Response, failedJobs: string[]): Promise<void> {
  const contentType = response.headers()['content-type'] ?? '';
  if (!contentType.includes('application/json')) return;

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return;
  }

  for (const item of collectRecords(payload)) {
    const status = readStatus(item);
    if (status && FAILED_JOB_STATUS_PATTERN.test(status)) {
      failedJobs.push(`${response.status()} ${response.url()} status=${status}`);
    }
  }
}

function collectRecords(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return [payload];

  const record = payload as Record<string, unknown>;
  for (const key of ['items', 'data', 'jobs', 'runs']) {
    if (Array.isArray(record[key])) return record[key] as unknown[];
  }
  return [payload];
}

function readStatus(value: unknown): string | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const record = value as Record<string, unknown>;
  const status = record.status ?? record.state ?? record.outcome;
  return typeof status === 'string' ? status : undefined;
}
