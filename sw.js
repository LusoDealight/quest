// Quest : cache hors-ligne simple (réseau d'abord pour la page, cache en secours).
const CACHE = "quest-v4";
const ASSETS = ["./", "./index.html", "./jeu.html", "./vendor/three.module.min.js", "./vendor/loaders/GLTFLoader.js", "./vendor/utils/BufferGeometryUtils.js", "./vendor/utils/SkeletonUtils.js", "./vendor/libs/meshopt_decoder.module.js", "./assets/persos/chevalier.glb", "./assets/persos/clips.glb", "./assets/persos/paysanne.glb", "./assets/persos/maria.glb", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))); self.skipWaiting(); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request).then(r => r || caches.match("./index.html")))
  );
});
