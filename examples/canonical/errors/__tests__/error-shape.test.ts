import { describe, it, expect } from "vitest";
import { createErrorResponse, CanonicalError, ErrorCode, ErrorResponse } from "../error-shape";

describe("createErrorResponse", () => {
  describe("Legacy Signature", () => {
    it("should create a properly formatted error response with valid metadata", () => {
      const error: CanonicalError = {
        code: "VALIDATION_FAILED",
        message: "Missing field name",
        recoverable: true,
      };
      const requestId = "req-123";
      const traceId = "trace-456";

      const result = createErrorResponse(error, requestId, traceId);

      expect(result.response.success).toBe(false);
      expect(result.response.error).toEqual(error);
      expect(result.response.meta.request_id).toBe(requestId);
      expect(result.response.meta.trace_id).toBe(traceId);

      // Check if timestamp is a valid ISO 8601 string
      expect(Date.parse(result.response.meta.timestamp)).not.toBeNaN();
      expect(result.statusCode).toBe(400);
    });

    it("should map NOT_FOUND error code to 404 status code", () => {
      const error: CanonicalError = {
        code: "NOT_FOUND",
        message: "Resource not found",
        recoverable: false,
      };

      const result = createErrorResponse(error, "req-1", "trace-1");

      expect(result.statusCode).toBe(404);
    });

    it("should fallback to 500 status code for unknown error codes", () => {
      const error: CanonicalError = {
        code: "UNKNOWN_CODE_XYZ" as ErrorCode,
        message: "Something mysterious happened",
        recoverable: false,
      };

      const result = createErrorResponse(error, "req-2", "trace-2");

      expect(result.statusCode).toBe(500);
    });
  });

  describe("New Signature", () => {
    it("should return the error directly if it is a CanonicalError", () => {
      const error: CanonicalError = {
        code: "VALIDATION_FAILED",
        message: "Missing field name",
        recoverable: true,
      };

      const result = createErrorResponse(error);
      expect(result).toBe(error);
    });

    it("should map a standard Error to an INTERNAL_ERROR ErrorResponse", () => {
      const standardError = new Error("Something went wrong");
      const context = { requestId: "req-1", traceId: "trace-1" };

      const result = createErrorResponse(standardError, context);

      // Type assertion needed since the return type is a union ErrorResponse | CanonicalError
      const response = result as ErrorResponse;
      expect(response.success).toBe(false);
      expect(response.error.code).toBe("INTERNAL_ERROR");
      expect(response.error.message).toBe("Something went wrong");
      expect(response.error.recoverable).toBe(false);
      expect(response.error.details).toBe(context);
      expect(response.meta.request_id).toBe("req-1");
      expect(response.meta.trace_id).toBe("trace-1");
      expect(Date.parse(response.meta.timestamp)).not.toBeNaN();
    });

    it("should map an unknown string error to an INTERNAL_ERROR ErrorResponse", () => {
      const stringError = "String failure";

      const result = createErrorResponse(stringError);

      const response = result as ErrorResponse;
      expect(response.success).toBe(false);
      expect(response.error.code).toBe("INTERNAL_ERROR");
      expect(response.error.message).toBe("String failure");
      expect(response.error.recoverable).toBe(false);
      expect(response.error.details).toBeUndefined();
      expect(response.meta.request_id).toBe("unknown");
      expect(response.meta.trace_id).toBe("unknown");
      expect(Date.parse(response.meta.timestamp)).not.toBeNaN();
    });
  });
});
