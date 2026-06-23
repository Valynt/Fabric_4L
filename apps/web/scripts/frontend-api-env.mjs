#!/usr/bin/env node
/**
 * Frontend API environment validation.
 *
 * Production builds must not silently fall back to local API routing defaults.
 * The values validated here are public VITE_* configuration only; they must not
 * contain secrets because Vite embeds them in the browser bundle.
 */

export const API_ENV_GROUPS = [
  {
    label: "gateway API version prefix",
    names: ["VITE_API_VERSION_PREFIX", "VITE_API_BASE"],
  },
  {
    label: "Layer 1 route prefix",
    names: ["VITE_LAYER1_ROUTE_PREFIX", "VITE_L1_PREFIX"],
  },
  {
    label: "Layer 2 route prefix",
    names: ["VITE_LAYER2_ROUTE_PREFIX", "VITE_L2_PREFIX"],
  },
  {
    label: "Layer 2.5 route prefix",
    names: ["VITE_LAYER2_5_ROUTE_PREFIX", "VITE_L2_5_PREFIX"],
  },
  {
    label: "Layer 3 route prefix",
    names: ["VITE_LAYER3_ROUTE_PREFIX", "VITE_L3_PREFIX"],
  },
  {
    label: "Layer 4 route prefix",
    names: ["VITE_LAYER4_ROUTE_PREFIX", "VITE_L4_PREFIX"],
  },
  {
    label: "Layer 5 route prefix",
    names: ["VITE_LAYER5_ROUTE_PREFIX", "VITE_L5_PREFIX"],
  },
  {
    label: "Layer 6 route prefix",
    names: ["VITE_LAYER6_ROUTE_PREFIX", "VITE_L6_PREFIX"],
  },
  {
    label: "Layer 7 route prefix",
    names: ["VITE_LAYER7_ROUTE_PREFIX", "VITE_L7_PREFIX"],
  },
];

export function validateFrontendApiEnv(
  env,
  { production = false, source = "frontend API configuration" } = {}
) {
  const errors = [];

  if (!production) {
    return { ok: true, errors };
  }

  for (const group of API_ENV_GROUPS) {
    const value = firstPresentValue(env, group.names);
    if (!value) {
      errors.push(`${group.label} requires one of: ${group.names.join(", ")}`);
      continue;
    }

    if (!value.startsWith("/")) {
      errors.push(
        `${group.label} must start with /; received ${JSON.stringify(value)}`
      );
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    message: formatValidationMessage(source, errors),
  };
}

export function assertFrontendApiEnv(env, options = {}) {
  const result = validateFrontendApiEnv(env, options);
  if (!result.ok) {
    throw new Error(result.message);
  }
  return result;
}

function firstPresentValue(env, names) {
  for (const name of names) {
    const value = env?.[name];
    if (typeof value === "string" && value.trim() !== "") {
      return value.trim();
    }
  }
  return null;
}

function formatValidationMessage(source, errors) {
  if (errors.length === 0) {
    return `${source} accepted.`;
  }

  return `${source} is missing required production API environment variables.\n- ${errors.join("\n- ")}`;
}
