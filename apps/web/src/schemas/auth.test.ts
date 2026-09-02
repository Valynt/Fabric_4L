import { describe, expect, it } from "vitest";
import {
  validateTokenResponse,
  validateLoginInitiationResponse,
  AuthError,
  AuthErrorCategory,
} from "./auth";

describe("auth schemas validation", () => {
  describe("validateTokenResponse", () => {
    it("returns valid token response data", () => {
      const validData = {
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        expires_in: 3600,
        token_type: "Bearer",
        user_id: "user-123",
        email: "user@example.com",
        role: "standard",
      };

      const result = validateTokenResponse(validData);
      expect(result).toEqual(validData);
    });

    it("returns valid token response data with missing optional fields", () => {
      const validData = {
        user_id: "user-123",
        email: "user@example.com",
        role: "admin",
      };

      const result = validateTokenResponse(validData);

      // Check that defaults are applied
      expect(result).toMatchObject({
        ...validData,
        expires_in: 3600,
        token_type: "Bearer",
      });
    });

    it("throws AuthError for invalid email", () => {
      const invalidData = {
        user_id: "user-123",
        email: "not-an-email",
        role: "standard",
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
      try {
        validateTokenResponse(invalidData);
      } catch (error) {
        expect(error).toBeInstanceOf(AuthError);
        if (error instanceof AuthError) {
          expect(error.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
          expect(error.message).toContain("Invalid token response");
        }
      }
    });

    it("throws AuthError for unsafe email", () => {
      const invalidData = {
        user_id: "user-123",
        email: "<script>alert(1)</script>@example.com",
        role: "standard",
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
    });

    it("throws AuthError for invalid role", () => {
      const invalidData = {
        user_id: "user-123",
        email: "user@example.com",
        role: "invalid-role",
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
    });

    it("throws AuthError for missing required user_id", () => {
      const invalidData = {
        email: "user@example.com",
        role: "standard",
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
    });
  });

  describe("validateLoginInitiationResponse", () => {
    it("returns valid login initiation response data", () => {
      const validData = {
        authorization_url: "https://auth.example.com/login",
        state: "test-state-123",
      };

      const result = validateLoginInitiationResponse(validData);
      expect(result).toEqual(validData);
    });

    it("throws AuthError for invalid URL", () => {
      const invalidData = {
        authorization_url: "not-a-url",
        state: "test-state-123",
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
      try {
        validateLoginInitiationResponse(invalidData);
      } catch (error) {
        expect(error).toBeInstanceOf(AuthError);
        if (error instanceof AuthError) {
          expect(error.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
          expect(error.message).toContain("Invalid login initiation response");
        }
      }
    });

    it("throws AuthError for missing state", () => {
      const invalidData = {
        authorization_url: "https://auth.example.com/login",
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
    });

    it("throws AuthError for empty state", () => {
      const invalidData = {
        authorization_url: "https://auth.example.com/login",
        state: "",
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
    });
  });
});
