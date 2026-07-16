// LykoonAdds service worker — enables "Install app" / "Add to Home Screen"
// on Android, Windows, Linux, macOS (Chrome/Edge) and offline fallback.
// Bump CACHE_NAME whenever you want to force-clear old cached assets.
const CACHE_NAME = "lykoonadds-v2";
const OFFLINE_URL = "/offline/";

const PRECACHE_ASSETS = [
  OFFLINE_URL,
  "/static/core/css/base.css",
  "/static/core/img/logo.svg",
  "/static/core/icons/icon-192.png",
  "/static/core/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Network-first for pages (data must stay fresh — wallet/tasks). Static
// assets (CSS/JS/logo/icons) use "stale-while-revalidate": the cached copy
// is served instantly for speed, but a fresh copy is fetched in the
// background and saved — so the NEXT load already has the update. This
// means installed apps auto-update within one reload, with no need to
// reinstall or bump a version number for every change.
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const isStatic = url.pathname.startsWith("/static/");

  if (isStatic) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(req);
        const networkFetch = fetch(req).then((res) => {
          cache.put(req, res.clone());
          return res;
        }).catch(() => cached);
        return cached || networkFetch;
      })
    );
    return;
  }

  event.respondWith(
    fetch(req).catch(() => caches.match(req).then((cached) => cached || caches.match(OFFLINE_URL)))
  );
});

