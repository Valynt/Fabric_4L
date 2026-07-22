/**
 * P2-006: Basic service worker for asset caching and offline support.
 *
 * Uses a cache-first strategy for static assets and a network-first
 * strategy for API calls. Caches are versioned for easy updates.
 */
const CACHE_VERSION = "v1";
const STATIC_CACHE = `static-${CACHE_VERSION}`;

const STATIC_ASSETS = ["/", "/index.html"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .flatMap((key) => key !== STATIC_CACHE ? [caches.delete(key)] : [])
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip API calls — let them fail normally when offline
  if (request.url.includes("/api/")) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        // Cache same-origin static assets
        if (
          response.status === 200 &&
          response.type === "basic" &&
          (request.destination === "script" ||
            request.destination === "style" ||
            request.destination === "image" ||
            request.destination === "document")
        ) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    })
  );
});
