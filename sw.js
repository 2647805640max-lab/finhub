/* FinHub service worker
   原则：页面壳和行情都「网络优先」——装了 App 之后最怕打开看到几天前的旧壳。
   只有彻底断网才用缓存兜底，而且页面顶部一直显示「更新 <时间>」，能看出来是不是旧的。

   ⚠️ 2026-11-03 修正（v3）：
   旧版把「任何响应」都写进缓存，包括 GitHub Pages 重建窗口里返回的 404。
   一旦缓存里存下 404 页面，弱网时就会拿它兜底 → 主页看起来永久 404。
   现在只缓存 r.ok 的响应；缓存里的旧 404 在 activate 时随旧 cache 一起清掉。
*/
const CACHE = 'finhub-v4';

self.addEventListener('install', e => { self.skipWaiting(); });

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
    await self.clients.claim();
    // 装好就主动抓一份正常的主页壳，避免缓存里只有「上次失败的那个 404」
    try {
      const scope = self.registration.scope;
      const r = await fetch(scope, { cache: 'no-store' });
      if (r.ok) await (await caches.open(CACHE)).put(scope, r);
    } catch (_) {}
  })());
});

const isOk = r => r && r.ok && r.status !== 404 && r.status !== 410;

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const netFirst = /(\.html|\/|manifest\.json|board\.json|state\.json|personal\.json|audit\.jsonl)$/.test(u.pathname);

  if (netFirst) {
    e.respondWith(fetch(e.request, { cache: 'no-store' }).then(r => {
      if (isOk(r)) {
        const c = r.clone();
        caches.open(CACHE).then(x => x.put(e.request, c)).catch(() => {});
      }
      return r;
    }).catch(async () => {
      const hit = await caches.match(e.request);
      return isOk(hit) ? hit : Response.error();
    }));
    return;
  }

  e.respondWith(caches.match(e.request).then(hit => {
    if (isOk(hit)) return hit;
    return fetch(e.request).then(resp => {
      if (isOk(resp)) {
        const c = resp.clone();
        caches.open(CACHE).then(x => x.put(e.request, c)).catch(() => {});
      }
      return resp;
    });
  }));
});
