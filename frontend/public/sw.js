/* Service worker mínimo — cache estático do Admin; não cacheia /api nem /bi */
const CACHE = "portal-bi-admin-v1";
const PRECACHE = [
  "/admin/",
  "/admin/index.html",
  "/admin/manifest.webmanifest",
  "/admin/icons/icon-192.png",
  "/admin/icons/icon-512.png",
  "/admin/logos/logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Nunca cachear API nem BI
  if (url.pathname.startsWith("/api") || url.pathname.startsWith("/bi")) {
    return;
  }

  // Somente assets do Admin
  if (!url.pathname.startsWith("/admin")) {
    return;
  }

  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok && (url.pathname.match(/\.(js|css|png|svg|webmanifest|woff2?)$/) || url.pathname.endsWith("/admin/") || url.pathname.endsWith("/admin/index.html"))) {
            const copy = res.clone();
            caches.open(CACHE).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
