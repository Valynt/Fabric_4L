import { describe, it, expect } from 'vitest';
import {
  validateTokenResponse,
  validateLoginInitiationResponse,
  AuthError,
  AuthErrorCategory
} from './auth';

describe('auth schemas', () => {
  describe('validateTokenResponse', () => {
    it('should return valid token response for correct data', () => {
      const validData = {
        access_token: 'token123',
        refresh_token: 'refresh123',
        expires_in: 3600,
        token_type: 'Bearer',
        user_id: 'user123',
        email: 'test@example.com',
        role: 'admin',
      };

      const result = validateTokenResponse(validData);
      expect(result).toEqual(validData);
    });

    it('should use defaults for optional fields', () => {
      const minimalData = {
        user_id: 'user123',
        email: 'test@example.com',
      };

      const result = validateTokenResponse(minimalData);
      expect(result).toMatchObject({
        user_id: 'user123',
        email: 'test@example.com',
        expires_in: 3600,
        token_type: 'Bearer',
        role: 'standard',
      });
    });

    it('should format token_type properly', () => {
      const validData = {
        user_id: 'user123',
        email: 'test@example.com',
        token_type: 'bearer',
      };

      const result = validateTokenResponse(validData);
      expect(result.token_type).toBe('Bearer');
    });

    it('should throw AuthError for invalid email', () => {
      const invalidData = {
        user_id: 'user123',
        email: 'invalid-email',
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
      try {
        validateTokenResponse(invalidData);
      } catch (err) {
        if (err instanceof AuthError) {
          expect(err.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
        }
      }
    });

    it('should throw AuthError for unsafe email', () => {
      const invalidData = {
        user_id: 'user123',
        email: '<script>alert(1)</script>@example.com',
        role: 'standard',
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
      try {
        validateTokenResponse(invalidData);
      } catch (err) {
        if (err instanceof AuthError) {
          expect(err.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
        }
      }
    });

    it('should throw AuthError for invalid role', () => {
      const invalidData = {
        user_id: 'user123',
        email: 'user@example.com',
        role: 'invalid-role',
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
      try {
        validateTokenResponse(invalidData);
      } catch (err) {
        if (err instanceof AuthError) {
          expect(err.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
        }
      }
    });

    it('should throw AuthError if missing user_id', () => {
      const invalidData = {
        email: 'test@example.com',
      };

      expect(() => validateTokenResponse(invalidData)).toThrowError(AuthError);
    });
  });

  describe('validateLoginInitiationResponse', () => {
    it('should return valid response for correct data', () => {
      const validData = {
        authorization_url: 'https://example.com/auth',
        state: 'random-state',
      };

      const result = validateLoginInitiationResponse(validData);
      expect(result).toEqual(validData);
    });

    it('should throw AuthError for invalid URL', () => {
      const invalidData = {
        authorization_url: 'not-a-url',
        state: 'random-state',
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
      try {
        validateLoginInitiationResponse(invalidData);
      } catch (err) {
        if (err instanceof AuthError) {
          expect(err.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
        }
      }
    });

    it('should throw AuthError if missing state', () => {
      const invalidData = {
        authorization_url: 'https://example.com/auth',
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
    });

    it('should throw AuthError for empty state', () => {
      const invalidData = {
        authorization_url: 'https://example.com/auth',
        state: '',
      };

      expect(() => validateLoginInitiationResponse(invalidData)).toThrowError(AuthError);
      try {
        validateLoginInitiationResponse(invalidData);
      } catch (err) {
        if (err instanceof AuthError) {
          expect(err.category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
        }
      }
    });
  });
});
