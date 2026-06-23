/**
 * Thesys C1 API Client
 * OpenAI-compatible API for Generative UI streaming
 */

import { apiClient, buildApiFetchInit } from "./client";
import { createFeatureLogger } from "@/lib/telemetry";
import { API_BASE, L4_PREFIX } from "@/lib/apiConfig";

const log = createFeatureLogger("thesysClient");

/**
 * Validate if a string is valid JSON without throwing
 */
function isValidJson(str: string): boolean {
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

const ENABLE_C1 = import.meta.env.VITE_ENABLE_C1_REPORTS === "true";

export interface C1Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface C1StreamChunk {
  type: "content" | "component" | "error" | "done";
  data?: unknown;
  error?: string;
}

export interface C1Component {
  type: string;
  props: Record<string, unknown>;
}

interface WhatIfResult {
  original_value: number;
  adjusted_value: number;
  delta_percentage: number;
  new_roi: number;
  new_payback_months: number;
  formula_used: string;
}

/**
 * Check if C1 integration is enabled.
 * The API key lives server-side, so the frontend only checks the feature flag.
 */
export function isC1Enabled(): boolean {
  return ENABLE_C1;
}

function parseSseDataLine(line: string): C1StreamChunk | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data: ")) return null;

  try {
    return JSON.parse(trimmed.slice(6)) as C1StreamChunk;
  } catch (err) {
    log.warn("Malformed SSE chunk", { errorCode: String(err) });
    return null;
  }
}

function parseFinalBufferedSseChunk(buffer: string): C1StreamChunk | null {
  const remaining = buffer.trim();
  if (!remaining.startsWith("data: ")) return null;

  const jsonPart = remaining.slice(6);
  if (!(jsonPart.endsWith("}") || jsonPart.endsWith("]")) || !isValidJson(jsonPart)) {
    log.warn("Discarding incomplete final chunk");
    return null;
  }

  try {
    return JSON.parse(jsonPart) as C1StreamChunk;
  } catch (err) {
    log.warn("Failed to parse final SSE chunk", {
      errorCode: String(err),
    });
    return null;
  }
}

/**
 * Stream C1 response for interactive UI generation.
 * Uses the L4 server-side proxy (`POST /v1/c1/stream`) so the Thesys API
 * key is never exposed to the browser.  The response is consumed via the
 * native `fetch()` + `ReadableStream` API which works in all modern browsers.
 */
export async function* streamC1Response(
  messages: C1Message[],
  businessCaseId: string,
  businessCaseData?: Record<string, unknown>,
  signal?: AbortSignal
): AsyncGenerator<C1StreamChunk, void, unknown> {
  if (!isC1Enabled()) {
    yield {
      type: "error",
      error: "C1 is not enabled. Set VITE_ENABLE_C1_REPORTS=true.",
    };
    return;
  }

  const url = `${API_BASE}${L4_PREFIX}/c1/stream`;

  try {
    const response = await fetch(
      url,
      buildApiFetchInit({
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages,
          business_case_id: businessCaseId,
          business_case_data: businessCaseData,
        }),
        signal,
      })
    );

    if (!response.ok) {
      const text = await response.text();
      yield {
        type: "error",
        error: `Server error (${response.status}): ${text}`,
      };
      return;
    }

    if (!response.body) {
      yield {
        type: "error",
        error: "Streaming not supported by this browser.",
      };
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last (possibly incomplete) line in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        const chunk = parseSseDataLine(line);
        if (chunk) yield chunk;
      }
    }

    const finalChunk = parseFinalBufferedSseChunk(buffer);
    if (finalChunk) yield finalChunk;

    yield { type: "done" };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      // Stream was intentionally aborted — not an error
      return;
    }
    yield {
      type: "error",
      error:
        error instanceof Error ? error.message : "Failed to stream C1 response",
    };
  }
}

/**
 * Evaluate formula via Value Fabric API and return formatted result
 * Called by C1-generated components when sliders change
 */
export async function evaluateWhatIf(
  baseCaseId: string,
  adjustments: Array<{ name: string; value: number; original_value: number }>,
  baseCaseData?: Record<string, unknown>
): Promise<WhatIfResult> {
  const response = await apiClient.post<WhatIfResult>(
    "l3",
    "/formulas/scenario",
    {
      base_case_id: baseCaseId,
      adjustments,
      base_case_data: baseCaseData,
    }
  );

  return response.data;
}

/**
 * Save scenario to localStorage (MVP implementation)
 * Can be upgraded to backend persistence later
 */
export function saveScenario(
  caseId: string,
  scenarioName: string,
  adjustments: Array<{ name: string; value: number }>
): string {
  const scenarioId = `scenario_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  const scenarios = getScenarios(caseId);

  scenarios.push({
    id: scenarioId,
    name: scenarioName,
    adjustments,
    created_at: new Date().toISOString(),
  });

  localStorage.setItem(`vf_scenarios_${caseId}`, JSON.stringify(scenarios));
  return scenarioId;
}

/**
 * Get saved scenarios for a business case
 */
export interface SavedScenario {
  id: string;
  name: string;
  adjustments: Array<{ name: string; value: number }>;
  created_at: string;
}

export function getScenarios(caseId: string): SavedScenario[] {
  try {
    const stored = localStorage.getItem(`vf_scenarios_${caseId}`);
    if (!stored) return [];
    const parsed = JSON.parse(stored) as SavedScenario[];
    // Validate structure to prevent crashes from corrupt data
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // Clear corrupt data
    localStorage.removeItem(`vf_scenarios_${caseId}`);
    return [];
  }
}

/**
 * Compare multiple scenarios
 */
export interface ScenarioComparison {
  id: string;
  name: string;
  adjustments: Array<{ name: string; value: number }>;
  created_at: string;
}

export function compareScenarios(
  caseId: string,
  scenarioIds: string[]
): ScenarioComparison[] {
  const allScenarios = getScenarios(caseId);
  return allScenarios.filter(s => scenarioIds.includes(s.id));
}

export { ENABLE_C1 };
