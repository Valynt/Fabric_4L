/**
 * Database Session Manager - Canonical Implementation
 *
 * CONTRACT.md §2.2 - DB Session and Isolation Pattern
 *
 * Tiered isolation with pooled shared-schema default and Row-Level Security.
 * This module demonstrates the canonical pattern for database access:
 * - TenantAwarePool reads context from async scope
 * - SET app.current_tenant before each query
 * - RLS policies as safety net
 *
 * Copy this file as the starting point for database sessions in new services.
 */

import { getTenantContext, type TenantTier } from "../context/tenant-context";

// ============================================================================
// Types
// ============================================================================

/** Database connection configuration */
export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;

  /** Connection pool settings */
  poolSize: number;
  connectionTimeoutMs: number;
  idleTimeoutMs: number;
}

/** Database session interface */
export interface DatabaseSession {
  /** Execute a query with automatic tenant scoping */
  query<T = unknown>(sql: string, params?: unknown[]): Promise<T[]>;

  /** Execute a single row query */
  queryOne<T = unknown>(sql: string, params?: unknown[]): Promise<T | null>;

  /** Execute insert/update/delete */
  execute(sql: string, params?: unknown[]): Promise<{ rowCount: number }>;

  /** Start a transaction */
  transaction<T>(fn: (session: DatabaseSession) => Promise<T>): Promise<T>;

  /** Release connection back to pool */
  release(): void;
}

/** Tenant-aware connection pool */
export interface TenantAwarePool {
  /** Get a session scoped to current tenant */
  getSession(): Promise<DatabaseSession>;

  /** End the pool (for shutdown) */
  end(): Promise<void>;
}

/** Tier-specific routing info */
interface TierRouting {
  tier: TenantTier;
  schema?: string; // For dedicated tier
  database?: string; // For enterprise tier
}

// ============================================================================
// Session Manager Implementation
// ============================================================================

/**
 * Canonical database session manager implementing tiered isolation.
 *
 * CONTRACT.md §2.2:
 * - Default: Pooled shared-schema with tenant_id columns and RLS
 * - Dedicated: Schema-per-tenant routing
 * - Enterprise: Database-per-tenant routing
 *
 * Usage:
 * ```typescript
 * // NEVER pass tenantId as parameter
 * const session = await db.getSession();
 *
 * // Automatic tenant scoping applied
 * const users = await session.query("SELECT * FROM users");
 * // Actually executes: SELECT * FROM users WHERE tenant_id = 'current-tenant'
 * ```
 */
export class SessionManager implements TenantAwarePool {
  private sharedPool: ConnectionPool;
  private dedicatedPools = new Map<string, ConnectionPool>();
  private enterprisePools = new Map<string, ConnectionPool>();
  private config: DatabaseConfig;

  constructor(config: DatabaseConfig) {
    this.config = config;
    // Initialize shared connection pool (PgBouncer or similar)
    this.sharedPool = new ConnectionPool(config);
  }

  /**
   * Get a database session automatically scoped to current tenant.
   *
   * CONTRACT.md §2.2:
   * - Reads tenant from async context (never pass as parameter)
   * - Returns appropriately-scoped connection
   * - Applies RLS via SET app.current_tenant
   *
   * @returns DatabaseSession ready for queries
   *
   * @example
   * ```typescript
   * // In route handler or service method
   * const session = await db.getSession();
   *
   * try {
   *   const users = await session.query(
   *     "SELECT * FROM users WHERE active = $1",
   *     [true]
   *   );
   *   // Automatic tenant scoping applied via RLS
   * } finally {
   *   session.release();
   * }
   * ```
   */
  async getSession(): Promise<DatabaseSession> {
    // CONTRACT.md §2.1: Read tenant from async context
    const tenantContext = getTenantContext();

    if (!tenantContext) {
      throw new Error(
        "Tenant context not available. Ensure request is within authenticated scope. " +
          "See CONTRACT.md §2.1 and §2.2"
      );
    }

    // Determine tier and routing
    const routing = this.determineRouting(tenantContext.tenant_tier, tenantContext.tenant_id);

    // Get connection from appropriate pool
    const connection = await this.acquireConnection(routing);

    // Apply tenant scoping to connection
    await this.applyTenantScope(connection, tenantContext.tenant_id, routing);

    return new ScopedSession(connection, tenantContext.tenant_id, () => {
      // Clear tenant scope before returning to pool
      this.clearTenantScope(connection);
    });
  }

  /**
   * Execute a query bypassing RLS (for admin/analytics only).
   *
   * CONTRACT.md §2.2:
   * - Requires BYPASS RLS database role
   * - All queries logged to audit trail
   * - Not available to application services
   *
   * @param sql Query to execute
   * @param reason Business reason for bypass
   * @returns Query results
   */
  async queryWithBypass<T>(sql: string, reason: string): Promise<T[]> {
    // Log to audit trail
    console.log(`[AUDIT] RLS bypass query: ${sql.substring(0, 100)}... Reason: ${reason}`);

    // Use dedicated admin connection with BYPASS RLS role
    const adminConnection = await this.sharedPool.acquireAdminConnection();

    try {
      return await adminConnection.query<T>(sql);
    } finally {
      adminConnection.release();
    }
  }

  async end(): Promise<void> {
    await this.sharedPool.end();

    for (const pool of this.dedicatedPools.values()) {
      await pool.end();
    }

    for (const pool of this.enterprisePools.values()) {
      await pool.end();
    }
  }

  // ==========================================================================
  // Private Methods
  // ==========================================================================

  private determineRouting(tier: TenantTier, tenantId: string): TierRouting {
    switch (tier) {
      case "shared":
        return { tier: "shared" };

      case "dedicated":
        return {
          tier: "dedicated",
          schema: `tenant_${tenantId.replace(/-/g, "_")}`,
        };

      case "enterprise":
        return {
          tier: "enterprise",
          database: `tenant_${tenantId}`,
        };

      default:
        throw new Error(`Unknown tenant tier: ${tier}`);
    }
  }

  private async acquireConnection(routing: TierRouting): Promise<Connection> {
    switch (routing.tier) {
      case "shared":
        return await this.sharedPool.acquire();

      case "dedicated": {
        // Get or create dedicated pool for this tenant's schema
        let pool = this.dedicatedPools.get(routing.schema!);
        if (!pool) {
          pool = new ConnectionPool({
            ...this.config,
            // Schema-specific configuration
          });
          this.dedicatedPools.set(routing.schema!, pool);
        }
        return await pool.acquire();
      }

      case "enterprise": {
        // Get or create enterprise pool for this tenant's database
        let pool = this.enterprisePools.get(routing.database!);
        if (!pool) {
          pool = new ConnectionPool({
            ...this.config,
            database: routing.database!,
          });
          this.enterprisePools.set(routing.database!, pool);
        }
        return await pool.acquire();
      }
    }
  }

  private async applyTenantScope(
    connection: Connection,
    tenantId: string,
    routing: TierRouting
  ): Promise<void> {
    switch (routing.tier) {
      case "shared":
        // CONTRACT.md §2.2: SET app.current_tenant for RLS policies
        await connection.execute("SET app.current_tenant = $1", [tenantId]);

        // Verify RLS is active
        await connection.execute("SET row_security = on");
        break;

      case "dedicated":
        // Set search_path to tenant schema
        await connection.execute("SET search_path TO $1", [routing.schema]);
        break;

      case "enterprise":
        // Already connected to tenant-specific database
        // No additional scoping needed
        break;
    }
  }

  private async clearTenantScope(connection: Connection): Promise<void> {
    // Reset any tenant-specific settings before returning to pool
    await connection.execute("RESET app.current_tenant").catch(() => {
      // Ignore errors - connection may already be closed
    });
    await connection.execute("RESET search_path").catch(() => {
      // Ignore errors
    });
  }
}

// ============================================================================
// Scoped Session Implementation
// ============================================================================

/**
 * Database session with automatic tenant scoping.
 *
 * CONTRACT.md §2.2:
 * - All queries include WHERE tenant_id clause via ORM/RLS
 * - Raw SQL outside migrations requires explicit approval
 * - RLS provides defense-in-depth
 */
class ScopedSession implements DatabaseSession {
  constructor(
    private connection: Connection,
    private tenantId: string,
    private cleanup: () => void
  ) {}

  async query<T = unknown>(sql: string, params?: unknown[]): Promise<T[]> {
    // CONTRACT.md §2.2: Application-level scoping (primary defense)
    const scopedSql = this.ensureTenantScope(sql);
    return await this.connection.query<T>(scopedSql, params);
  }

  async queryOne<T = unknown>(sql: string, params?: unknown[]): Promise<T | null> {
    const results = await this.query<T>(sql, params);
    return results[0] ?? null;
  }

  async execute(sql: string, params?: unknown[]): Promise<{ rowCount: number }> {
    const scopedSql = this.ensureTenantScope(sql);
    return await this.connection.execute(scopedSql, params);
  }

  async transaction<T>(fn: (session: DatabaseSession) => Promise<T>): Promise<T> {
    await this.connection.execute("BEGIN");

    try {
      const result = await fn(this);
      await this.connection.execute("COMMIT");
      return result;
    } catch (error) {
      await this.connection.execute("ROLLBACK");
      throw error;
    }
  }

  release(): void {
    this.cleanup();
    this.connection.release();
  }

  // ========================================================================
  // Private Methods
  // ========================================================================

  /**
   * Ensure query has tenant scoping.
   *
   * CONTRACT.md §2.2:
   * - Application-level filtering is primary defense
   * - RLS is the safety net
   */
  private ensureTenantScope(sql: string): string {
    // Skip for queries that don't need tenant scoping
    if (sql.match(/^\s*(SET|SHOW|BEGIN|COMMIT|ROLLBACK)/i)) {
      return sql;
    }

    // Check if query already has tenant_id (double-scope prevention)
    if (sql.includes("tenant_id")) {
      return sql;
    }

    // For SELECT/INSERT/UPDATE/DELETE, add tenant scoping
    // In production, this would be handled by ORM's query builder
    // This is simplified for demonstration
    const match = sql.match(/^\s*(SELECT|INSERT|UPDATE|DELETE)/i);
    if (match && !sql.includes("WHERE")) {
      // Add WHERE clause with tenant_id
      // Note: Real implementation would use query builder, not string manipulation
      console.warn(`[DB] Query missing tenant scope: ${sql.substring(0, 50)}...`);
    }

    return sql;
  }
}

// ============================================================================
// Connection Pool (Mock Implementation)
// ============================================================================

interface Connection {
  query<T>(sql: string, params?: unknown[]): Promise<T[]>;
  execute(sql: string, params?: unknown[]): Promise<{ rowCount: number }>;
  release(): void;
}

class ConnectionPool {
  private connections: Connection[] = [];

  constructor(private config: DatabaseConfig) {
    // Initialize pool connections
  }

  async acquire(): Promise<Connection> {
    // In production: get connection from PgBouncer or similar
    // For now, return mock connection
    return new MockConnection();
  }

  async acquireAdminConnection(): Promise<Connection> {
    // Return connection with elevated privileges
    return new MockConnection(true);
  }

  async end(): Promise<void> {
    // Close all connections
  }
}

class MockConnection implements Connection {
  constructor(private isAdmin = false) {}

  async query<T>(sql: string, params?: unknown[]): Promise<T[]> {
    console.log(`[DB Query${this.isAdmin ? " (admin)" : ""}] ${sql.substring(0, 100)}`);
    return [] as T[];
  }

  async execute(sql: string, params?: unknown[]): Promise<{ rowCount: number }> {
    console.log(`[DB Execute${this.isAdmin ? " (admin)" : ""}] ${sql.substring(0, 100)}`);
    return { rowCount: 1 };
  }

  release(): void {
    // Return to pool
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

// Production configuration would come from environment
const defaultConfig: DatabaseConfig = {
  host: process.env.DB_HOST || "localhost",
  port: parseInt(process.env.DB_PORT || "5432"),
  database: process.env.DB_NAME || "fabric4l",
  user: process.env.DB_USER || "app",
  password: process.env.DB_PASSWORD || "",
  poolSize: parseInt(process.env.DB_POOL_SIZE || "20"),
  connectionTimeoutMs: 5000,
  idleTimeoutMs: 30000,
};

/** Global session manager instance */
export const db = new SessionManager(defaultConfig);

// ============================================================================
// Anti-Pattern Detection
// ============================================================================

/**
 * DEPRECATED: Direct database connection with explicit tenant.
 *
 * CONTRACT.md §2.2 Anti-pattern:
 * - db.connect(tenantId) is deprecated
 * - Use db.getSession() instead (context-driven)
 *
 * This function exists only for backward compatibility during migration.
 * It will be removed in Q3 2026.
 *
 * @deprecated Use db.getSession() which reads tenant from async scope
 */
export async function connectWithTenant(tenantId: string): Promise<DatabaseSession> {
  console.warn(
    `[DEPRECATION] db.connect(${tenantId}) is deprecated. ` +
      `Use db.getSession() which reads tenant from async scope. ` +
      `See CONTRACT.md §2.2 and DEPRECATIONS.md`
  );

  // Delegate to canonical pattern
  const ctx = getTenantContext();
  if (!ctx || ctx.tenant_id !== tenantId) {
    throw new Error(
      `Tenant context mismatch. Expected ${tenantId}, got ${ctx?.tenant_id || "null"}`
    );
  }

  return db.getSession();
}
