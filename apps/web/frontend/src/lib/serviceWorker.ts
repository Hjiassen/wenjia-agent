export const PWA_UPDATE_AVAILABLE_EVENT = "wenjia:pwa-update-available";

const UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1000;
let updateNotified = false;
let currentAssetSignature = "";

function notifyUpdateAvailable() {
  if (updateNotified) {
    return;
  }
  updateNotified = true;
  window.dispatchEvent(new CustomEvent(PWA_UPDATE_AVAILABLE_EVENT));
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
  window.setInterval(checkAppShellUpdate, UPDATE_CHECK_INTERVAL_MS);
  window.addEventListener("focus", checkAppShellUpdate);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      void checkAppShellUpdate();
    }
  });

  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => {
        watchRegistration(registration);
        void registration.update().catch(() => undefined);
      })
      .catch(() => {
        // PWA support is a progressive enhancement; keep chat usable if it fails.
      });
  });
}
