import { useEffect } from "react";
import { useLocation, useMatches } from "react-router-dom";
import { getTracer } from "./opentelemetry";

/**
 * RouteTelemetry — creates an OpenTelemetry span on every route change.
 *
 * Mount once inside the Router tree (e.g. GlobalLayout). Uses useLocation
 * and useMatches so it reacts to navigation without blocking rendering.
 */
export function RouteTelemetry() {
  const location = useLocation();
  const matches = useMatches();

  useEffect(() => {
    const tracer = getTracer();
    if (!tracer) return;

    const span = tracer.startSpan("route_change");

    // Deepest match carries the most specific route metadata
    const deepest = matches[matches.length - 1];
    const accessPolicy = (deepest?.handle as { accessPolicy?: { analyticsRouteId?: string } } | undefined)?.accessPolicy;
    const routeId = accessPolicy?.analyticsRouteId ?? "unknown";
    const routePath = deepest?.pathname ?? location.pathname;

    span.setAttribute("route.id", routeId);
    span.setAttribute("route.path", routePath);
    span.setAttribute("http.url", typeof window !== "undefined" ? window.location.href : location.pathname);

    span.end();
  }, [location.pathname, matches]);

  return null;
}
