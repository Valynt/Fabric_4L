/**
 * TypeScript view of the canonical Clerk / Fabric auth defaults.
 *
 * The JSON file in `src/clerk_defaults.json` is the single source of truth.
 * This module re-exports it with a typed shape so frontend and backend
 * TypeScript consumers can import defaults without duplicating them.
 */

import clerkDefaults from "../clerk_defaults.json" with { type: "json" };

export default clerkDefaults;

export type ClerkDefaults = typeof clerkDefaults;
