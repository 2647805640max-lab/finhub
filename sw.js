/* FinHub service worker
   原则：页面壳和行情都「网络优先」——装了 App 之后最怕的是打开看到几天前的旧壳。
   只有彻底断网才用缓存兜底，而且页面顶部一直显示「更新 <时间>」，能看出来是不是旧的。 */
const CACHE = 'finhub-v2';

self.addEventListener('install', e => { self.skipWaiting(); });

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const netFirst = /(\.html|\/|manifest\.json|board\.json|state\.json|personal\.json|audit\.jsonl)$/.test(u.pathname);

  if (netFirst) {
    e.respondWith(fetch(e.request, {cache: 'no-store'}).then(r => {
      const c = r.clone();
      caches.open(CACHE).then(x => x.put(e.request, c)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request)));
    return;
  }
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
    const c = resp.clone();
    caches.open(CACHE).then(x => x.put(e.request, c)).catch(() => {});
    return resp;
  }).catch(() => r)));
});
