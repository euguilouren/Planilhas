const CACHE_NAME = 'pfp-v1';

// Only static shell assets — never cache dynamic/financial responses
const PRECACHE_URLS = [
  self.registration.scope,
  self.registration.scope + 'index.html',
  self.registration.scope + 'manifest.json'
];

// Static file extensions safe to cache
const STATIC_EXT = /\.(html|js|css|png|svg|ico|woff2?|ttf|webmanifest|json)$/i;

// CDN hostnames whose static assets can be cached (SheetJS, Chart.js, fonts)
const CDN_HOSTS = new Set([
  'cdn.jsdelivr.net',
  'cdnjs.cloudflare.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdn.sheetjs.com'
]);

// Max age for CDN cached assets (24h) — forces revalidation for security updates
const CDN_MAX_AGE_MS = 24 * 60 * 60 * 1000;

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
      .catch(err => console.warn('[SW] install precache failed:', err))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Only cache GET requests
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // CDN assets — cache-first with 24h TTL
  if (CDN_HOSTS.has(url.hostname)) {
    event.respondWith(
      caches.open(CACHE_NAME).then(cache =>
        cache.match(req).then(cached => {
          if (cached) {
            const date = cached.headers.get('sw-cached-at');
            if (date && Date.now() - Number(date) < CDN_MAX_AGE_MS) {
              return cached;
            }
          }
          return fetch(req).then(res => {
            if (res.ok) {
              const headers = new Headers(res.headers);
              headers.set('sw-cached-at', String(Date.now()));
              const modified = new Response(res.body, { status: res.status, statusText: res.statusText, headers });
              cache.put(req, modified.clone());
              return modified;
            }
            return res;
          }).catch(() => cached || Response.error());
        })
      )
    );
    return;
  }

  // Same-origin: only cache static file extensions — never cache API calls or financial data
  if (url.hostname === location.hostname && STATIC_EXT.test(url.pathname)) {
    event.respondWith(
      caches.open(CACHE_NAME).then(cache =>
        fetch(req)
          .then(res => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() =>
            cache.match(req).then(cached => {
              if (cached) return cached;
              // Offline fallback for navigation requests
              if (req.mode === 'navigate') {
                return cache.match(self.registration.scope + 'index.html')
                  || cache.match(self.registration.scope);
              }
              return Response.error();
            })
          )
      )
    );
    return;
  }

  // All other same-origin requests (API calls, fetch with financial data) — network only, no cache
});
