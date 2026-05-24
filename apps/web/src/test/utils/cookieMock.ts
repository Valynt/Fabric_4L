/**
 * Cookie mocking utility for reliable cookie handling in tests.
 *
 * This utility provides a clean, reusable way to mock document.cookie in tests,
 * avoiding brittle Object.defineProperty patterns and ensuring proper cleanup.
 * It uses a Map-based storage to simulate browser cookie behavior.
 */

/**
 * Cookie storage implementation using a Map for test isolation.
 */
class CookieStorage {
  private cookies = new Map<string, string>();

  /**
   * Get a cookie value by name.
   * @param name - Cookie name
   * @returns Cookie value or undefined if not found
   */
  get(name: string): string | undefined {
    return this.cookies.get(name);
  }

  /**
   * Set a cookie value.
   * @param name - Cookie name
   * @param value - Cookie value
   */
  set(name: string, value: string): void {
    this.cookies.set(name, value);
  }

  /**
   * Remove a cookie by name.
   * @param name - Cookie name
   */
  remove(name: string): void {
    this.cookies.delete(name);
  }

  /**
   * Clear all cookies.
   */
  clear(): void {
    this.cookies.clear();
  }

  /**
   * Get all cookies as a semicolon-separated string (browser format).
   * @returns Cookie string in "name1=value1; name2=value2" format
   */
  toString(): string {
    return Array.from(this.cookies.entries())
      .map(([name, value]) => `${name}=${value}`)
      .join('; ');
  }

  /**
   * Get all cookie entries as an array of [name, value] tuples.
   * @returns Array of cookie entries
   */
  entries(): [string, string][] {
    return Array.from(this.cookies.entries());
  }

  /**
   * Parse a cookie string and populate storage.
   * @param cookieString - Cookie string in "name1=value1; name2=value2" format
   */
  fromString(cookieString: string): void {
    this.clear();
    if (!cookieString) return;

    cookieString.split(';').forEach((cookie) => {
      const [name, ...valueParts] = cookie.trim().split('=');
      const value = valueParts.join('=');
      if (name) {
        this.cookies.set(name, value);
      }
    });
  }
}

/**
 * Cookie mock manager for test setup and teardown.
 * Provides a clean API for mocking document.cookie in tests.
 */
export class CookieMock {
  private storage = new CookieStorage();
  private originalCookieDescriptor?: PropertyDescriptor;

  /**
   * Initialize the cookie mock by replacing document.cookie.
   * Call this in beforeEach or test setup.
   */
  install(): void {
    // Store original descriptor for restoration
    this.originalCookieDescriptor = Object.getOwnPropertyDescriptor(
      Document.prototype,
      'cookie'
    );

    // Replace document.cookie with our mock
    Object.defineProperty(document, 'cookie', {
      configurable: true,
      get: () => this.storage.toString(),
      set: (value: string) => this.storage.fromString(value),
    });
  }

  /**
   * Restore the original document.cookie implementation.
   * Call this in afterEach or test teardown.
   */
  uninstall(): void {
    if (this.originalCookieDescriptor) {
      Object.defineProperty(document, 'cookie', this.originalCookieDescriptor);
    }
    this.storage.clear();
  }

  /**
   * Set a specific cookie value.
   * @param name - Cookie name
   * @param value - Cookie value
   */
  setCookie(name: string, value: string): void {
    this.storage.set(name, value);
  }

  /**
   * Get a specific cookie value.
   * @param name - Cookie name
   * @returns Cookie value or undefined if not found
   */
  getCookie(name: string): string | undefined {
    return this.storage.get(name);
  }

  /**
   * Remove a specific cookie.
   * @param name - Cookie name
   */
  removeCookie(name: string): void {
    this.storage.remove(name);
  }

  /**
   * Clear all cookies.
   */
  clear(): void {
    this.storage.clear();
  }

  /**
   * Get all current cookies as an object.
   * @returns Object with cookie name-value pairs
   */
  getAll(): Record<string, string> {
    return Object.fromEntries(this.storage.entries());
  }
}

/**
 * Convenience function to create and install a cookie mock.
 * Returns the mock instance for use in tests.
 *
 * @example
 * ```ts
 * const cookieMock = setupCookieMock();
 * cookieMock.setCookie('vf_csrf_token', 'test-token');
 * // ... run tests
 * cookieMock.uninstall();
 * ```
 */
export function setupCookieMock(): CookieMock {
  const mock = new CookieMock();
  mock.install();
  return mock;
}

/**
 * CSRF token-specific cookie helpers.
 * These are commonly used in auth tests.
 */
export const csrfCookieHelpers = {
  /**
   * Set the CSRF token cookie.
   * @param token - CSRF token value
   * @param cookieMock - Optional CookieMock instance (uses global if not provided)
   */
  setCsrfToken(token: string, cookieMock?: CookieMock): void {
    if (cookieMock) {
      cookieMock.setCookie('vf_csrf_token', token);
    } else {
      document.cookie = `vf_csrf_token=${token}`;
    }
  },

  /**
   * Get the CSRF token from cookies.
   * @param cookieMock - Optional CookieMock instance (uses global if not provided)
   * @returns CSRF token value or undefined
   */
  getCsrfToken(cookieMock?: CookieMock): string | undefined {
    if (cookieMock) {
      return cookieMock.getCookie('vf_csrf_token');
    }
    // Parse from document.cookie string
    const match = document.cookie.match(/vf_csrf_token=([^;]+)/);
    return match?.[1];
  },

  /**
   * Clear the CSRF token cookie.
   * @param cookieMock - Optional CookieMock instance (uses global if not provided)
   */
  clearCsrfToken(cookieMock?: CookieMock): void {
    if (cookieMock) {
      cookieMock.removeCookie('vf_csrf_token');
    } else {
      document.cookie = 'vf_csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    }
  },
};
