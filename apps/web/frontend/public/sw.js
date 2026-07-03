const CACHE_NAME = "wenjia-pwa-v3";
const UPDATE_READY_MESSAGE = "WENJIA_PWA_UPDATE_READY";
const APP_SHELL = [
  "/",
  "/manifest.webmanifest",
  "/wenjia-mark.svg",
  "/icons/icon-180.png",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: "window", includeUncontrolled: true }))
      .then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: UPDATE_READY_MESSAGE, cacheName: CACHE_NAME });
        });
      }),
  );
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

function shouldSkip(request) {
  if (request.method !== "GET") {
    return true;
  }
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return true;
  }
  return url.pathname.startsWith("/api/") || url.pathname === "/health";
}

function networkFirst(request) {
  return fetch(request)
    .then((response) => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put("/", copy));
      return response;
    })
    .catch(() => caches.match("/"));
}

function staleWhileRevalidate(request) {
  return caches.match(request).then((cached) => {
    const refresh = fetch(request)
      .then((response) => {
        if (response && response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
        }
        return response;
      })
      .catch(() => cached);
    return cached || refresh;
  });
}

self.addEventListener("fetch", (event) => {
  if (shouldSkip(event.request)) {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(networkFirst(event.request));
    return;
  }

  if (["script", "style", "image", "font", "manifest"].includes(event.request.destination)) {
    event.respondWith(staleWhileRevalidate(event.request));
  }
});
