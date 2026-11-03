// Минимальный Service Worker для активации PWA-режима
const CACHE_NAME = 'schulbert-v1.01';

self.addEventListener('install', (event) => {
    // Пропускаем этап ожидания, чтобы воркер активировался мгновенно
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

// Просто перехватываем запросы для проформы (требование Android/iOS для установки иконки)
self.addEventListener('fetch', (event) => {
    event.respondWith(fetch(event.request));
});
