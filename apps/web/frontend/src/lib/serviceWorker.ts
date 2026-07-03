export const PWA_UPDATE_AVAILABLE_EVENT = "wenjia:pwa-update-available";

const UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1000;
const STARTUP_UPDATE_CHECK_DELAYS = [1200, 5000];
const PWA_CACHE_PREFIX = "wenjia-pwa-";
const PWA_UPDATE_READY_MESSAGE = "WENJIA_PWA_UPDATE_READY";
let updateNotified = false;
let currentAssetSignature = "";

function notifyUpdateAvailable() {
  if (updateNotified) {
    return;
  }
  updateNotified = true;
  window.dispatchEvent(new CustomEvent(PWA_UPDATE_AVAILABLE_EVENT));
}

export function isPwaUpdateAvailable(): boolean {
  return updateNotified;
}

function normalizeAssetUrl(value: string | null): string | null {
  if (!value) {
    return null;
  }
  try {
    const url = new URL(value, window.location.href);
    return `${url.pathname}${url.search}`;
  } catch {
    return value;
  }
}

function getAssetSignature(documentLike: Document): string {
  const scripts = Array.from(documentLike.querySelectorAll<HTMLScriptElement>("script[src]"))
    .map((item) => normalizeAssetUrl(item.getAttribute("src")))
    .filter(Boolean);
  const styles = Array.from(
    documentLike.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"][href]'),
  )
    .map((item) => normalizeAssetUrl(item.getAttribute("href")))
    .filter(Boolean);

  return [...scripts, ...styles].sort().join("|");
}

async function checkAppShellUpdate() {
  if (!currentAssetSignature) {
    return;
  }

  try {
    const response = await fetch(`/?_wenjia_update=${Date.now()}`, {
      cache: "no-store",
      headers: { "Cache-Control": "no-cache" },
    });
    if (!response.ok) {
      return;
    }
    const html = await response.text();
    const nextDocument = new DOMParser().parseFromString(html, "text/html");
    const nextSignature = getAssetSignature(nextDocument);
    if (nextSignature && nextSignature !== currentAssetSignature) {
      notifyUpdateAvailable();
    }
  } catch {
    // Update checks are best-effort and should never affect chat usage.
  }
}

async function getServiceWorkerRegistrations(): Promise<readonly ServiceWorkerRegistration[]> {
  const container = navigator.serviceWorker;
  if (typeof container.getRegistrations === "function") {
    return container.getRegistrations();
  }

  const registration = await container.getRegistration();
  return registration ? [registration] : [];
}

function requestSkipWaiting(registration: ServiceWorkerRegistration) {
  registration.waiting?.postMessage({ type: "SKIP_WAITING" });
}

export async function reloadForPwaUpdate() {
  try {
    if ("serviceWorker" in navigator) {
      const registrations = await getServiceWorkerRegistrations();
      await Promise.all(
        registrations.map(async (registration) => {
          requestSkipWaiting(registration);
          await registration.update().catch(() => undefined);
          requestSkipWaiting(registration);
        }),
      );
    }

    if ("caches" in window) {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith(PWA_CACHE_PREFIX))
          .map((key) => caches.delete(key)),
      );
    }
  } catch {
    // A hard reload is still the best available fallback.
  } finally {
    const url = new URL(window.location.href);
    url.searchParams.set("_wenjia_reload", Date.now().toString());
    window.location.replace(url.toString());
  }
}

function watchRegistration(registration: ServiceWorkerRegistration) {
  if (registration.waiting && navigator.serviceWorker.controller) {
    notifyUpdateAvailable();
  }

  registration.addEventListener("updatefound", () => {
    const worker = registration.installing;
    if (!worker) {
      return;
    }

    worker.addEventListener("statechange", () => {
      if (
        (worker.state === "installed" || worker.state === "activated") &&
        navigator.serviceWorker.controller
      ) {
        notifyUpdateAvailable();
      }
    });
  });
}

export function registerServiceWorker() {
  if (!import.meta.env.PROD) {
    return;
  }

  currentAssetSignature = getAssetSignature(document);
  window.setInterval(() => void checkAppShellUpdate(), UPDATE_CHECK_INTERVAL_MS);
  STARTUP_UPDATE_CHECK_DELAYS.forEach((delay) => {
    window.setTimeout(() => void checkAppShellUpdate(), delay);
  });
  window.addEventListener("focus", () => void checkAppShellUpdate());
  window.addEventListener("pageshow", () => void checkAppShellUpdate());
  window.addEventListener("online", () => void checkAppShellUpdate());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      void checkAppShellUpdate();
    }
  });

  if (!("serviceWorker" in navigator)) {
    return;
  }

  const hadControllerBeforeRegister = Boolean(navigator.serviceWorker.controller);
  navigator.serviceWorker.addEventListener("message", (event) => {
    if (hadControllerBeforeRegister && event.data?.type === PWA_UPDATE_READY_MESSAGE) {
      notifyUpdateAvailable();
    }
  });
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (hadControllerBeforeRegister) {
      notifyUpdateAvailable();
    }
  });

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js", { updateViaCache: "none" })
      .then((registration) => {
        watchRegistration(registration);
        void registration.update().catch(() => undefined);
        void checkAppShellUpdate();
      })
      .catch(() => {
        // PWA support is a progressive enhancement; keep chat usable if it fails.
      });
  });
}
