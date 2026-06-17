import { z } from "zod";

// Keep Zod CSP-safe in browsers by avoiding Function/eval probing.
z.config({ jitless: true });
