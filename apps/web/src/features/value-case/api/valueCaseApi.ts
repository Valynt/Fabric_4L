/**
 * Value Case Typed API Client
 *
 * Performs validated network calls to backend value-case endpoints.
 */
import { apiGet, apiPost, apiPatch } from "@/api/typedClient";
import {
  parseApiBusinessCase,
  parseApiValueCaseList,
  parseApiAccount,
  ValueCaseBoundaryError,
  type ApiBusinessCase,
  type ApiValueCaseContent,
  type ApiAccount,
} from "./valueCaseSchemas";

export async function fetchValueCasesApi(
  accountId: string,
  options?: { headers?: Record<string, string> }
): Promise<ApiBusinessCase[]> {
  try {
    const response = await apiGet<unknown>(
      "api",
      `/accounts/${encodeURIComponent(accountId)}/value-cases`,
      options
    );
    return parseApiValueCaseList(response.data);
  } catch (err: unknown) {
    if (err instanceof ValueCaseBoundaryError) throw err;
    const message = err instanceof Error ? err.message : "Failed to load value cases";
    throw new ValueCaseBoundaryError(message, "NETWORK_ERROR", err);
  }
}

export async function createValueCaseApi(
  accountId: string,
  payload: { title: string; value_case: ApiValueCaseContent },
  options?: { headers?: Record<string, string> }
): Promise<ApiBusinessCase> {
  try {
    const response = await apiPost<unknown>(
      "api",
      `/accounts/${encodeURIComponent(accountId)}/value-case`,
      payload,
      options
    );
    return parseApiBusinessCase(response.data);
  } catch (err: unknown) {
    if (err instanceof ValueCaseBoundaryError) throw err;
    const message = err instanceof Error ? err.message : "Failed to create value case";
    throw new ValueCaseBoundaryError(message, "NETWORK_ERROR", err);
  }
}

export async function updateValueCaseApi(
  accountId: string,
  caseId: string,
  payload: { value_case: Partial<ApiValueCaseContent> },
  options?: { headers?: Record<string, string> }
): Promise<ApiBusinessCase> {
  try {
    const response = await apiPatch<unknown>(
      "api",
      `/accounts/${encodeURIComponent(accountId)}/value-cases/${encodeURIComponent(caseId)}`,
      payload,
      options
    );
    return parseApiBusinessCase(response.data);
  } catch (err: unknown) {
    if (err instanceof ValueCaseBoundaryError) throw err;
    const message = err instanceof Error ? err.message : "Failed to update value case";
    throw new ValueCaseBoundaryError(message, "NETWORK_ERROR", err);
  }
}

export async function publishValueCaseApi(
  accountId: string,
  caseId: string,
  options?: { headers?: Record<string, string> }
): Promise<ApiBusinessCase> {
  try {
    const response = await apiPost<unknown>(
      "api",
      `/accounts/${encodeURIComponent(accountId)}/value-cases/${encodeURIComponent(caseId)}/publish`,
      {},
      options
    );
    return parseApiBusinessCase(response.data);
  } catch (err: unknown) {
    if (err instanceof ValueCaseBoundaryError) throw err;
    const message = err instanceof Error ? err.message : "Failed to publish value case";
    throw new ValueCaseBoundaryError(message, "NETWORK_ERROR", err);
  }
}

export async function fetchAccountApi(
  accountId: string,
  options?: { headers?: Record<string, string> }
): Promise<ApiAccount> {
  try {
    const response = await apiGet<unknown>(
      "api",
      `/accounts/${encodeURIComponent(accountId)}`,
      options
    );
    return parseApiAccount(response.data);
  } catch (err: unknown) {
    if (err instanceof ValueCaseBoundaryError) throw err;
    const message = err instanceof Error ? err.message : "Failed to load account";
    throw new ValueCaseBoundaryError(message, "NETWORK_ERROR", err);
  }
}
