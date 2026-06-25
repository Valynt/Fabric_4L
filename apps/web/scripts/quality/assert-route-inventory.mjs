#!/usr/bin/env node
/**
 * Static route inventory guard.
 *
 * Browser route tests prove runtime rendering. This guard catches earlier drift:
 * TieredNav links must resolve to canonical router entries, protected routes
 * must carry access-policy metadata directly or through the known Settings
 * layout branches, admin route families must be admin-gated, and legacy flat
 * redirects must target real tenant-scoped routes.
 */
import { readFileSync } from "node:fs";
import { dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..", "..");
const routerPath = resolve(webRoot, "src", "shell", "router.tsx");
const navPath = resolve(webRoot, "src", "components", "navigation", "TieredNav.tsx");
const routerText = readFileSync(routerPath, "utf8");
const navText = readFileSync(navPath, "utf8");
const failures = [];

const routerPaths = extractStringValues(routerText, "path");
const navPaths = extractStringValues(navText, "path").filter((path) => path.startsWith("/"));
const legacyRedirects = extractLegacyFlatRouteMap(routerText);

validateTieredNavDestinations();
validateRouteAccessPolicyMetadata();
validateAdminRoutePolicyMetadata();
validateLegacyRedirectTargets();
validateNavigationDoesNotTargetLegacyRedirects();

if (failures.length > 0) {
  console.error("Frontend route inventory guard failed.");
  for (const failure of failures) {
    console.error(` - ${failure}`);
  }
  process.exit(1);
}

console.log(
  `Frontend route inventory passed: ${navPaths.length} TieredNav paths, ${routerPaths.length} router paths, and ${legacyRedirects.length} legacy redirects validated.`,
);

function validateTieredNavDestinations() {
  for (const navPathValue of navPaths) {
    if (!routerPaths.some((routePath) => routePatternMatches(routePath, navPathValue))) {
      failures.push(
        `${relative(webRoot, navPath)} TieredNav path ${navPathValue} has no canonical router match`,
      );
    }
  }
}

function validateRouteAccessPolicyMetadata() {
  for (const route of extractRouteObjects(routerText)) {
    const path = route.path;
    if (isPublicOrRedirectOnlyRoute(route) || inheritsKnownParentPolicy(path)) {
      continue;
    }
    if (!/handle\s*:\s*\{[\s\S]*accessPolicy\s*:/.test(route.objectText)) {
      failures.push(`${relative(webRoot, routerPath)} route ${path} is missing handle.accessPolicy`);
    }
  }
}

function validateAdminRoutePolicyMetadata() {
  for (const route of extractRouteObjects(routerText)) {
    const path = route.path;
    if (!isAdminRoute(path) || isPublicOrRedirectOnlyRoute(route)) {
      continue;
    }
    if (inheritsTenantSettingsAdminPolicy(path)) {
      continue;
    }
    if (!/tenantAdminPolicy\(/.test(route.objectText)) {
      failures.push(`${relative(webRoot, routerPath)} admin route ${path} must use tenantAdminPolicy`);
    }
  }
}

function validateLegacyRedirectTargets() {
  for (const [legacyPath, targetTemplate] of legacyRedirects) {
    const canonicalTarget = targetTemplate.replace("{tenantSlug}", ":tenantSlug");
    if (!canonicalTarget.startsWith("/t/:tenantSlug/")) {
      failures.push(`legacy redirect ${legacyPath} must target a tenant-scoped canonical route`);
      continue;
    }
    if (!routerPaths.some((routePath) => routePatternMatches(routePath, canonicalTarget))) {
      failures.push(`legacy redirect ${legacyPath} targets missing route ${targetTemplate}`);
    }
  }
}

function validateNavigationDoesNotTargetLegacyRedirects() {
  const legacySources = new Set(legacyRedirects.map(([legacyPath]) => legacyPath));
  for (const navPathValue of navPaths) {
    if (legacySources.has(navPathValue)) {
      failures.push(`TieredNav must not target legacy redirect source ${navPathValue}`);
    }
  }
}

function extractStringValues(text, key) {
  const pattern = new RegExp(`${key}\\s*:\\s*["']([^"']+)["']`, "g");
  return [...text.matchAll(pattern)].map((match) => match[1]);
}

function extractLegacyFlatRouteMap(text) {
  const mapMatch = text.match(/LEGACY_FLAT_ROUTE_MAP[\s\S]*?=\s*\{([\s\S]*?)\};/);
  if (!mapMatch) {
    failures.push("LEGACY_FLAT_ROUTE_MAP could not be found");
    return [];
  }
  return [...mapMatch[1].matchAll(/["']([^"']+)["']\s*:\s*["']([^"']+)["']/g)].map((match) => [
    match[1],
    match[2],
  ]);
}

function extractRouteObjects(text) {
  const routeObjects = [];
  const pathPattern = /path\s*:\s*["']([^"']+)["']/g;
  let match;
  while ((match = pathPattern.exec(text)) !== null) {
    const objectStart = text.lastIndexOf("{", match.index);
    if (objectStart < 0) {
      continue;
    }
    const objectEnd = findMatchingBrace(text, objectStart);
    if (objectEnd < 0) {
      failures.push(`could not find route object end for path ${match[1]}`);
      continue;
    }
    routeObjects.push({
      path: match[1],
      objectText: text.slice(objectStart, objectEnd + 1),
    });
  }
  return routeObjects;
}

function findMatchingBrace(text, startIndex) {
  let depth = 0;
  let quote = "";
  let escaped = false;
  for (let index = startIndex; index < text.length; index += 1) {
    const char = text[index];
    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = "";
      }
      continue;
    }
    if (char === '"' || char === "'" || char === "`") {
      quote = char;
      continue;
    }
    if (char === "{") {
      depth += 1;
    } else if (char === "}") {
      depth -= 1;
      if (depth === 0) {
        return index;
      }
    }
  }
  return -1;
}

function routePatternMatches(routePath, candidatePath) {
  const routeSegments = routePath.split("/").filter(Boolean);
  const candidateSegments = candidatePath.split("/").filter(Boolean);
  if (routeSegments.length !== candidateSegments.length) {
    return false;
  }
  return routeSegments.every((segment, index) => {
    const candidate = candidateSegments[index];
    return segment === candidate || segment.startsWith(":") || candidate.startsWith(":");
  });
}

function isPublicOrRedirectOnlyRoute(route) {
  return (
    route.path === "*" ||
    route.path === "/" ||
    /authPolicy|homePolicy|<Navigate\s/.test(route.objectText) ||
    /LegacyFlatRedirect|LegacyIntelligenceRedirect|RootRedirect|ExternalRootRedirect/.test(route.objectText)
  );
}

function inheritsKnownParentPolicy(path) {
  return path.startsWith("/personal") || path.startsWith("/settings") || path.startsWith("/t/:tenantSlug/settings");
}

function inheritsTenantSettingsAdminPolicy(path) {
  return path.startsWith("/t/:tenantSlug/settings");
}

function isAdminRoute(path) {
  return (
    path.startsWith("/t/:tenantSlug/settings") ||
    path === "/dev/integration" ||
    /\/(integrations|sources|targets|benchmarks|policies|audit-log|health|billing)(\/|$)/.test(path)
  );
}
