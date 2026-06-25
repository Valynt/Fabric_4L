import { describe, it, expect, vi } from "vitest";
import {
  parseSseDataLine,
  parseFinalBufferedSseChunk,
} from "./c1SseParser";
import type { C1StreamChunk } from "./thesysClient";

vi.mock("@/lib/telemetry", () => ({
  createFeatureLogger: () => ({
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  }),
}));

describe("c1SseParser", () => {
  describe("parseSseDataLine", () => {
    it("parses a valid SSE data line into a chunk", () => {
      const chunk = parseSseDataLine<C1StreamChunk>(
        'data: {"type":"content","data":{"text":"hello"}}'
      );
      expect(chunk).toEqual({ type: "content", data: { text: "hello" } });
    });

    it("returns null for comment lines", () => {
      expect(parseSseDataLine(": keep-alive")).toBeNull();
    });

    it("returns null for blank lines", () => {
      expect(parseSseDataLine("")).toBeNull();
      expect(parseSseDataLine("   ")).toBeNull();
    });

    it("returns null for malformed JSON", () => {
      expect(parseSseDataLine("data: {not-json}")).toBeNull();
    });

    it("returns null for lines missing the data: prefix", () => {
      expect(parseSseDataLine('{"type":"done"}')).toBeNull();
    });
  });

  describe("parseFinalBufferedSseChunk", () => {
    it("parses a complete final object chunk", () => {
      const chunk = parseFinalBufferedSseChunk<C1StreamChunk>(
        'data: {"type":"done"}'
      );
      expect(chunk).toEqual({ type: "done" });
    });

    it("parses a complete final array chunk", () => {
      const chunk = parseFinalBufferedSseChunk("data: [1,2,3]");
      expect(chunk).toEqual([1, 2, 3]);
    });

    it("returns null when the buffer is not a data line", () => {
      expect(parseFinalBufferedSseChunk('{"type":"done"}')).toBeNull();
    });

    it("returns null for incomplete JSON objects", () => {
      expect(parseFinalBufferedSseChunk('data: {"type":"done"')).toBeNull();
    });

    it("returns null for incomplete JSON arrays", () => {
      expect(parseFinalBufferedSseChunk("data: [1,2,")).toBeNull();
    });

    it("returns null for malformed final JSON", () => {
      expect(parseFinalBufferedSseChunk("data: not-json")).toBeNull();
    });
  });
});
