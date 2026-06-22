import React, { ReactElement, ReactNode, useState } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { QueryCache, QueryClient, QueryClientProvider, MutationCache } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
// Re-export for AuthContext tests (avoids circular dependency)
export type { UserInfo } from "./contexts/AuthContext";
import { logError } from "./lib/telemetry";

// P2 Improvement: Shared mock response factory for API tests
export function createMockResponse<T>(data: T, status = 200): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: status === 200 ? "OK" : "Error",
    headers: {},
    config: { headers: {} } as InternalAxiosRequestConfig,
  } as AxiosResponse<T>;
}

export const createTestQueryClient = () =>
  new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        logError('Test query failed', {
          queryKey: JSON.stringify(query.queryKey),
          error: error instanceof Error ? error.message : String(error),
        });
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        logError('Test mutation failed', {
          mutationKey: mutation.options.mutationKey?.toString(),
          error: error instanceof Error ? error.message : String(error),
        });
      },
    }),
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

export function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    const [queryClient] = useState(() => createTestQueryClient());
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

export function createWrapperWithRouterPath(path: string) {
  return function Wrapper({ children }: { children: ReactNode }) {
    const [queryClient] = useState(() => createTestQueryClient());
    if (typeof window !== "undefined") {
      const url = new URL(path, "http://localhost:3000");
      Object.defineProperty(window, "location", {
        configurable: true,
        writable: true,
        value: {
          ...window.location,
          href: url.toString(),
          pathname: url.pathname,
          search: url.search,
          hash: url.hash,
        },
      });
      window.history.replaceState({}, "", path);
    }
    return (
      <MemoryRouter initialEntries={[path]}>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

type RenderWithRouterOptions = Omit<RenderOptions, "wrapper"> & {
  path?: string;
};

export function renderWithRouter(
  ui: ReactElement,
  { path = "/", ...renderOptions }: RenderWithRouterOptions = {}
) {
  const wrapper = createWrapperWithRouterPath(path);
  return render(ui, { wrapper, ...renderOptions });
}

/** Create a wrapper with configurable retry behavior for error state testing */
export function createWrapperWithRetry(enableRetry: boolean) {
  return function Wrapper({ children }: { children: ReactNode }) {
    const [queryClient] = useState(() =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: enableRetry,
            staleTime: 0,
            gcTime: 0,
          },
        },
      })
    );
    return (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}


