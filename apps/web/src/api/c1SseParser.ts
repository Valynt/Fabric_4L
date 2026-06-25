import { createFeatureLogger } from "@/lib/telemetry";
import type { C1StreamChunk } from "./thesysClient";

const log = createFeatureLogger("c1SseParser");

/**
 * Validate if a string is valid JSON without throwing.
 */
function isValidJson(str: string): boolean {
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

/**
 * Parse a single Server-Sent Events `data:` line.
 */
export function parseSseDataLine<T = C1StreamChunk>(line: string): T | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data: ")) return null;

  try {
    return JSON.parse(trimmed.slice(6)) as T;
  } catch (err) {
    log.warn("Malformed SSE chunk", { errorCode: String(err) });
    return null;
  }
}

/**
 * Parse any remaining buffered SSE content after the stream ends.
 */
export function parseFinalBufferedSseChunk<T = C1StreamChunk>(
  buffer: string
): T | null {
  const remaining = buffer.trim();
  if (!remaining.startsWith("data: ")) return null;

  const jsonPart = remaining.slice(6);
  if (
    !(jsonPart.endsWith("}") || jsonPart.endsWith("]")) ||
    !isValidJson(jsonPart)
  ) {
    log.warn("Discarding incomplete final chunk");
    return null;
  }

  try {
    return JSON.parse(jsonPart) as T;
  } catch (err) {
    log.warn("Failed to parse final SSE chunk", {
      errorCode: String(err),
    });
    return null;
  }
}
