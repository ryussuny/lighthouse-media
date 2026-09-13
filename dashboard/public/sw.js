// lh-media 서비스워커
// v2 (2026-09-13): HTML·JS·JSON은 네트워크 우선(오프라인 시에만 캐시) — v1이 jarvis.html 등 문서를 캐시 우선으로
// 저장해 배포 후에도 옛 관제탑을 계속 보여주던 문제 수리. 이미지·폰트·CSS만 캐시 우선 유지.
const CACHE = 'lh-media-v2';
const STATIC = [
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  'https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// 항상 최신이어야 하는 요청: 문서(HTML)·스크립트·JSON·매니페스트
function isFreshFirst(req, url) {
  if (req.mode === 'navigate') return true;
  if (req.destination === 'document' || req.destination === 'script') return true;
  return /\.(html|js|json|webmanifest)$/.test(url.pathname) || url.pathname.endsWith('/');
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);

  // API 요청은 항상 네트워크 (캐시 안 함)
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify([]), { headers: { 'Content-Type': 'application/json' } })
      )
    );
    return;
  }

  // 문서·스크립트·JSON: 네트워크 우선, 실패(오프라인) 시에만 캐시 사본
  if (isFreshFirst(e.request, url)) {
    e.respondWith(
      fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  // 이미지·폰트·CSS 등 정적 자산: 캐시 우선
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
    })
  );
});
