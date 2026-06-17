/**
 * Current user profile hooks.
 *
 * Fetches and updates the authenticated user's own profile via
 * `GET /v1/users/me` and `PATCH /v1/users/me`.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPatch } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { withApiError, BaseApiError, STALE_TIME, RETRY_CONFIG } from "./useApiShared";
import { createLogger } from "@/lib/telemetry";

const log = createLogger("useCurrentUser");

// ── Types ───────────────────────────────────────────────────────────────────

export interface CurrentUser {
  id: string;
  email: string;
  display_name?: string;
  role: string;
  status?: string;
  tenant_id: string;
  created_at: string;
  updated_at?: string;
}

export interface UpdateCurrentUserPayload {
  display_name?: string;
}

export class CurrentUserApiError extends BaseApiError {
  constructor(message: string, statusCode?: number, responseData?: unknown) {
    super(message, statusCode, responseData);
    this.name = "CurrentUserApiError";
  }
}

// ── Fetch Functions ─────────────────────────────────────────────────────────

async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await apiGet<CurrentUser>("l4", "/users/me");
  return response.data;
}

async function updateCurrentUser(
  payload: UpdateCurrentUserPayload
): Promise<CurrentUser> {
  const response = await apiPatch<CurrentUser>("l4", "/users/me", payload);
  return response.data;
}

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useCurrentUser() {
  return useQuery<CurrentUser, CurrentUserApiError>({
    queryKey: QK.platform.currentUser,
    queryFn: () => withApiError(fetchCurrentUser(), CurrentUserApiError),
    staleTime: STALE_TIME.reference,
    retry: RETRY_CONFIG.maxRetries,
    retryDelay: RETRY_CONFIG.retryDelay,
  });
}

export function useUpdateCurrentUser() {
  const queryClient = useQueryClient();

  return useMutation<CurrentUser, CurrentUserApiError, UpdateCurrentUserPayload>({
    mutationFn: (payload) =>
      withApiError(updateCurrentUser(payload), CurrentUserApiError),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.platform.currentUser });
    },
    onError: (error) => {
      log.error("UpdateCurrentUser failed", {
        error: error instanceof Error ? error.message : String(error),
      });
    },
  });
}
