const CACHE_NAME = "wenjia-pwa-v2";
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
      .then(() => self.clients.claim()),
  );
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
