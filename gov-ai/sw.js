// 政务中台 Service Worker - 离线缓存
const CACHE_NAME = 'gov-ai-cache-v1';
const OFFLINE_URL = '/gov-ai/';

// 核心资源缓存（安装时预缓存）
const CORE_ASSETS = [
  '/gov-ai/',
  '/gov-ai/index.html',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// 网络优先，失败回退缓存（适用于HTML页面）
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  // 只处理GET请求
  if (request.method !== 'GET') return;
  
  const url = new URL(request.url);
  
  // API请求不缓存（网络优先）
  if (url.pathname.includes('/api/') || url.pathname.includes('/gov-api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(JSON.stringify({ error: 'offline' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }
  
  // 静态资源：缓存优先
  if (url.pathname.match(/\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf)$/)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        }).catch(() => cached);
      })
    );
    return;
  }
  
  // HTML页面：网络优先，失败回退缓存
  event.respondWith(
    fetch(request).then((response) => {
      const clone = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
      return response;
    }).catch(() => {
      return caches.match(request).then((cached) => {
        return cached || caches.match(OFFLINE_URL);
      });
    })
  );
});
