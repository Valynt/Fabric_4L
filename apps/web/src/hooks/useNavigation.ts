/**
 * useNavigation — Wrapper hook for centralized navigation service
 * Replaces direct useNavigate() with state-based navigation per CONTRACT.md §2.6
 */
import { useNavigate, useLocation, type NavigateOptions, type To } from "react-router-dom";
import { getStatePath, type RouteState, type NavigationParams } from "@/navigation/navigationService";
import { serializeQueryString } from "@/navigation/queryParams";
import { useWorkflowContext } from "@/hooks/useWorkflowContext";
import { serializeWorkflowContextToQuery } from "@/workflow/context";

interface NavigationOptions extends Omit<NavigateOptions, "state"> {
  replace?: boolean;
  state?: Record<string, unknown>;
}

interface StateNavigationOptions extends NavigationOptions {
  query?: Record<string, string | number | boolean | undefined | string[]>;
}

interface NavigateToFunction {
  (state: RouteState, params?: NavigationParams, options?: StateNavigationOptions): void;
  (path: string, options?: NavigationOptions): void;
}

export function useNavigation() {
  const navigate = useNavigate();
  const location = useLocation();
  const workflowContext = useWorkflowContext();

  const navigateTo: NavigateToFunction = (
    stateOrPath: RouteState | string,
    paramsOrOptions?: NavigationParams | NavigationOptions,
    options?: StateNavigationOptions
  ) => {
    if (typeof stateOrPath === "string" && stateOrPath.startsWith("/")) {
      // Direct path navigation (backward compat)
      const opts = paramsOrOptions as NavigationOptions | undefined;
      navigate(stateOrPath, opts);
    } else {
      // State-based navigation
      const state = stateOrPath as RouteState;
      const params = paramsOrOptions as NavigationParams | undefined;
      const opts = options;
      let path = getStatePath(state, params);
      const contextQuery = serializeWorkflowContextToQuery(workflowContext);
      const mergedQuery = { ...contextQuery, ...(opts?.query ?? {}) };
      path += serializeQueryString(mergedQuery);
      const { query: _query, ...navigateOpts } = opts ?? {};
      navigate(path, navigateOpts);
    }
  };

  const goBack = () => navigate(-1);
  const goForward = () => navigate(1);

  const navigateToLogin = (redirect?: string) => {
    navigateTo("login", undefined, redirect ? { query: { redirect } } : undefined);
  };

  const navigateToHome = () => navigateTo("home");

  const navigateToAccount = (tenantSlug: string, accountId: string) =>
    navigateTo("account-detail", { tenantSlug, accountId });

  const navigateToIntelligence = (tenantSlug: string, accountId: string, tab?: string) => {
    const state = tab ? (`intelligence-${tab}` as RouteState) : "intelligence-signals";
    navigateTo(state, { tenantSlug, accountId });
  };

  return {
    navigate,
    navigateTo,
    goBack,
    goForward,
    navigateToLogin,
    navigateToHome,
    navigateToAccount,
    navigateToIntelligence,
    location,
  };
}
