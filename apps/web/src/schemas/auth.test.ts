import { describe, it, expect } from 'vitest';
import {
  validateTokenResponse,
  validateLoginInitiationResponse,
  AuthError,
  AuthErrorCategory,
} from './auth';

describe('auth schemas', () => {
  describe('validateTokenResponse', () => {
    it('returns valid token response for correct data', () => {
      const validData = {
        access_token: 'token123',
        refresh_token: 'refresh123',
        expires_in: 3600,
        token_type: 'Bearer',
        user_id: 'user123',
        email: 'test@example.com',
        role: 'admin',
      };

      expect(validateTokenResponse(validData)).toEqual(validData);
    });

    it('applies defaults for optional fields', () => {
      const result = validateTokenResponse({
        user_id: 'user123',
        email: 'test@example.com',
      });

      expect(result).toMatchObject({
        user_id: 'user123',
        email: 'test@example.com',
        expires_in: 3600,
        token_type: 'Bearer',
        role: 'standard',
      });
    });

    it('normalizes token_type casing', () => {
      const result = validateTokenResponse({
        user_id: 'user123',
        email: 'test@example.com',
        token_type: 'bearer',
      });

      expect(result.token_type).toBe('Bearer');
    });

    it('throws AuthError for invalid email', () => {
      expect.assertions(2);
      try {
        validateTokenResponse({
          user_id: 'user123',
          email: 'invalid-email',
        });
        throw new Error('Expected validateTokenResponse to throw');
      } catch (err) {
        expect(err).toBeInstanceOf(AuthError);
        expect((err as AuthError).category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
      }
    });

    it('throws AuthError for unsafe email', () => {
      expect.assertions(2);
      try {
        validateTokenResponse({
          user_id: 'user123',
          email: '<script>alert(1)</script>@example.com',
          role: 'standard',
        });
        throw new Error('Expected validateTokenResponse to throw');
      } catch (err) {
        expect(err).toBeInstanceOf(AuthError);
        expect((err as AuthError).category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
      }
    });

    it('throws AuthError for invalid role', () => {
      expect.assertions(2);
      try {
        validateTokenResponse({
          user_id: 'user123',
          email: 'user@example.com',
          role: 'invalid-role',
        });
        throw new Error('Expected validateTokenResponse to throw');
      } catch (err) {
        expect(err).toBeInstanceOf(AuthError);
        expect((err as AuthError).category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
      }
    });

    it('throws AuthError when user_id is missing', () => {
      expect(() =>
        validateTokenResponse({
          email: 'test@example.com',
        }),
      ).toThrowError(AuthError);
    });

    it('throws AuthError when email is missing', () => {
      expect(() =>
        validateTokenResponse({
          user_id: 'user123',
        }),
      ).toThrowError(AuthError);
    });
  });

  describe('validateLoginInitiationResponse', () => {
    it('returns valid login initiation response', () => {
      const validData = {
        authorization_url: 'https://example.com/auth',
        state: 'random-state',
      };

      expect(validateLoginInitiationResponse(validData)).toEqual(validData);
    });

    it('throws AuthError for invalid authorization URL', () => {
      expect.assertions(2);
      try {
        validateLoginInitiationResponse({
          authorization_url: 'not-a-url',
          state: 'random-state',
        });
        throw new Error('Expected validateLoginInitiationResponse to throw');
      } catch (err) {
        expect(err).toBeInstanceOf(AuthError);
        expect((err as AuthError).category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
      }
    });

    it('throws AuthError when state is missing', () => {
      expect(() =>
        validateLoginInitiationResponse({
          authorization_url: 'https://example.com/auth',
        }),
      ).toThrowError(AuthError);
    });

    it('throws AuthError for empty state', () => {
      expect.assertions(2);
      try {
        validateLoginInitiationResponse({
          authorization_url: 'https://example.com/auth',
          state: '',
        });
        throw new Error('Expected validateLoginInitiationResponse to throw');
      } catch (err) {
        expect(err).toBeInstanceOf(AuthError);
        expect((err as AuthError).category).toBe(AuthErrorCategory.MALFORMED_RESPONSE);
      }
    });

    it('throws AuthError when authorization_url is missing', () => {
      expect(() =>
        validateLoginInitiationResponse({
          state: 'random-state',
        }),
      ).toThrowError(AuthError);
    });
  });
});
