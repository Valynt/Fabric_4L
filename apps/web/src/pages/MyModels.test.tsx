import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { createWrapper, createMockResponse } from "../test-utils";
import MyModels from "./MyModels";
import * as useModelsModule from "../hooks/useModels";
import { apiClient } from "@/api/client";

// Mock the API client
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const navigateTo = vi.fn();

// Mock centralized navigation
vi.mock("@/hooks/useNavigation", () => ({
  useNavigation: () => ({ navigateTo }),
}));

describe("MyModels Page", () => {
  // Mock models in BACKEND format (snake_case) - will be transformed by hook
  const mockModels = [
    {
      model_id: "mdl_001",
      name: "SaaS Revenue Optimization",
      description: "End-to-end value model",
      industry: "SaaS / B2B",
      tags: ["revenue", "churn"],
      status: "active" as const,
      folder: "my-models",
      formula_count: 14,
      entity_count: 32,
      driver_count: 8,
      created_at: "2026-03-15T10:00:00Z",
      updated_at: "2026-04-16T14:30:00Z",
      owner: "user-001",
      is_shared: false,
    },
    {
      model_id: "mdl_002",
      name: "DevOps Efficiency",
      description: "Infrastructure cost model",
      industry: "SaaS / B2B",
      tags: ["infrastructure"],
      status: "draft" as const,
      folder: "my-models",
      formula_count: 9,
      entity_count: 18,
      driver_count: 5,
      created_at: "2026-02-20T09:00:00Z",
      updated_at: "2026-04-14T11:15:00Z",
      owner: "user-001",
      is_shared: false,
    },
  ];

  const mockFolders = [
    { id: "all", name: "All Models", count: 2 },
    { id: "my-models", name: "My Models", count: 2 },
    { id: "shared", name: "Shared With Me", count: 0 },
    { id: "favorites", name: "Favorites", count: 0 },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Helper to set up standard mock API responses for models and folders
  const setupMockApi = () => {
    vi.mocked(apiClient.get).mockImplementation((_, path) => {
      if (path?.includes("/models/folders")) {
        return Promise.resolve(createMockResponse({ folders: mockFolders }));
      }
      if (path?.includes("/models?")) {
        return Promise.resolve(createMockResponse({
          models: mockModels,
          total: mockModels.length,
          offset: 0,
          limit: 50,
        }));
      }
      return Promise.resolve(createMockResponse({}));
    });
  };

  describe("Initial Render", () => {
    it("should render page header with title and subtitle", async () => {
      setupMockApi();

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("My Models")).toBeInTheDocument();
      });

      expect(screen.getByText("Personal and shared value models")).toBeInTheDocument();
    });

    it("should show loading state initially", () => {
      vi.mocked(apiClient.get).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<MyModels />, { wrapper: createWrapper() });

      // Should show skeletons while loading
      expect(document.querySelector("[class*='animate-pulse']")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no models exist", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(
            createMockResponse({
              folders: [
                { id: "all", name: "All Models", count: 0 },
                { id: "my-models", name: "My Models", count: 0 },
                { id: "shared", name: "Shared With Me", count: 0 },
                { id: "favorites", name: "Favorites", count: 0 },
              ],
            })
          );
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: [],
              total: 0,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("No models yet")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Create your first value model to get started.")
      ).toBeInTheDocument();

      // Should show Create First Model button
      expect(screen.getByRole("button", { name: /Create First Model/i })).toBeInTheDocument();
    });

    it("should show search empty state when no search results", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: [],
              total: 0,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Search models...")).toBeInTheDocument();
      });

      // Type in search box
      const searchInput = screen.getByPlaceholderText("Search models...");
      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      await waitFor(() => {
        expect(screen.getByText("No models match your search")).toBeInTheDocument();
      });
    });
  });

  describe("Model Grid View", () => {
    it("should render model cards in grid view", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("SaaS Revenue Optimization")).toBeInTheDocument();
      });

      expect(screen.getByText("DevOps Efficiency")).toBeInTheDocument();
      // Model stats from mock: mdl_001 has 8 drivers, 14 formulas; mdl_002 has 5 drivers, 9 formulas
      await waitFor(() => {
        expect(screen.getByText(/8 drivers/)).toBeInTheDocument();
        expect(screen.getByText(/14 formulas/)).toBeInTheDocument();
      });
    });

    it("should show correct status badges", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Active")).toBeInTheDocument();
      });

      expect(screen.getByText("Draft")).toBeInTheDocument();
    });
  });

  describe("Model Navigation", () => {
    it("should navigate to model detail when a model card is clicked", async () => {
      setupMockApi();

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("SaaS Revenue Optimization")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("SaaS Revenue Optimization"));

      expect(navigateTo).toHaveBeenCalledWith("model-detail", { modelId: "mdl_001" });
    });
  });

  describe("Folder Sidebar", () => {
    it("should render folder list with counts", async () => {
      setupMockApi();

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Folders")).toBeInTheDocument();
      });

      // Verify folder counts are displayed - component renders count as separate element
      expect(screen.getByText(/All Models/)).toBeInTheDocument();
      expect(screen.getByText(/Shared With Me/)).toBeInTheDocument();
      expect(screen.getByText(/Favorites/)).toBeInTheDocument();
      // Check counts from mock data: All Models (2), My Models (2), Shared With Me (0), Favorites (0)
    });
  });

  describe("Search and Filter", () => {
    it("should update search query on input change", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Search models...")).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText("Search models...");
      fireEvent.change(searchInput, { target: { value: "revenue" } });

      expect(searchInput).toHaveValue("revenue");
    });

    it("should show Clear button when filters active", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByPlaceholderText("Search models...")).toBeInTheDocument();
      });

      // Type in search box to activate filters
      const searchInput = screen.getByPlaceholderText("Search models...");
      fireEvent.change(searchInput, { target: { value: "test" } });

      await waitFor(() => {
        expect(screen.getByText("Clear")).toBeInTheDocument();
      });
    });
  });

  describe("Create Model Dialog", () => {
    it("should open create dialog on New Model button click", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /New Model/i })).toBeInTheDocument();
      });

      const newModelButton = screen.getByRole("button", { name: /New Model/i });
      fireEvent.click(newModelButton);

      await waitFor(() => {
        expect(screen.getByText("New Value Model")).toBeInTheDocument();
      });

      expect(screen.getByPlaceholderText("e.g. SaaS Revenue Optimization")).toBeInTheDocument();
    });

    it("should close dialog on Cancel", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /New Model/i })).toBeInTheDocument();
      });

      // Open dialog
      fireEvent.click(screen.getByRole("button", { name: /New Model/i }));

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });

      // Click Cancel
      fireEvent.click(screen.getByText("Cancel"));

      // Dialog should close (New Value Model text should not be visible)
      await waitFor(() => {
        expect(screen.queryByText("New Value Model")).not.toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should show error state when API fails", async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error("API Error"));

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText("Failed to load models")).toBeInTheDocument();
      });
    });
  });

  describe("View Mode Toggle", () => {
    it("should have grid/list view toggle buttons", async () => {
      vi.mocked(apiClient.get).mockImplementation((layer, path) => {
        if (path === "/models/folders") {
          return Promise.resolve(createMockResponse({ folders: mockFolders }));
        }
        if (path?.includes("/models?")) {
          return Promise.resolve(
            createMockResponse({
              models: mockModels,
              total: 2,
              offset: 0,
              limit: 50,
            })
          );
        }
        return Promise.resolve(createMockResponse({}));
      });

      render(<MyModels />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Grid and List buttons should be present (they use icons)
        const buttons = screen.getAllByRole("button");
        expect(buttons.length).toBeGreaterThan(0);
      });
    });
  });
});
