import { describe, it, expect } from 'vitest';
import { SafeEmailSchema, isSafeEmail } from './auth';

describe('SafeEmailSchema', () => {
  it('should validate standard email formats', () => {
    expect(SafeEmailSchema.safeParse('test@example.com').success).toBe(true);
    expect(SafeEmailSchema.safeParse('user.name+tag@example.co.uk').success).toBe(true);
  });

  it('should reject emails with single quotes because of strict unsafe pattern', () => {
    // Single quotes are technically valid in email local parts, but our current
    // strict unsafeEmailInputPattern regex explicitly rejects them for safety.
    expect(SafeEmailSchema.safeParse('o\'connor@example.com').success).toBe(false);
  });

  it('should allow whitespace trimming', () => {
    // Current codebase uses .trim() which trims before standard validation in Zod v3.
    const result = SafeEmailSchema.safeParse('  test@example.com  ');
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data).toBe('test@example.com');
    }
  });

  it('should reject emails without @ symbol', () => {
    expect(SafeEmailSchema.safeParse('testexample.com').success).toBe(false);
  });

  it('should reject emails that are too long', () => {
    const longLocalPart = 'a'.repeat(250);
    const longEmail = `${longLocalPart}@example.com`;
    expect(SafeEmailSchema.safeParse(longEmail).success).toBe(false);
  });

  describe('Unsafe character rejection', () => {
    it('should reject emails with HTML/script tags', () => {
      expect(SafeEmailSchema.safeParse('<script>@example.com').success).toBe(false);
      expect(SafeEmailSchema.safeParse('test@<script>example.com').success).toBe(false);
    });

    it('should reject emails with double quotes', () => {
      expect(SafeEmailSchema.safeParse('"test"@example.com').success).toBe(false);
    });

    it('should reject emails with backticks', () => {
      expect(SafeEmailSchema.safeParse('test`@example.com').success).toBe(false);
    });

    it('should reject emails with backslashes', () => {
      expect(SafeEmailSchema.safeParse('test\\@example.com').success).toBe(false);
    });

    it('should reject emails with control characters', () => {
      expect(SafeEmailSchema.safeParse('test\u0000@example.com').success).toBe(false);
      expect(SafeEmailSchema.safeParse('test\u001f@example.com').success).toBe(false);
    });

    it('should reject javascript: and data: URIs', () => {
      expect(SafeEmailSchema.safeParse('javascript:alert(1)@example.com').success).toBe(false);
      expect(SafeEmailSchema.safeParse('data:text/html@example.com').success).toBe(false);
    });
  });
});

describe('isSafeEmail', () => {
  it('should return true for safe emails', () => {
    expect(isSafeEmail('test@example.com')).toBe(true);
    expect(isSafeEmail('  test@example.com  ')).toBe(true); // Trims and passes
  });

  it('should return false for unsafe or invalid emails', () => {
    expect(isSafeEmail('invalid-email')).toBe(false);
    expect(isSafeEmail('<script>alert("xss")</script>@example.com')).toBe(false);
    expect(isSafeEmail('data:text/html@example.com')).toBe(false);
  });
});
