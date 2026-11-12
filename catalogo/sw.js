const CACHE = "archivio-9b25bdf65a72";
const FILE = ["./", "icona.svg", "index.html", "manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

// Rete con tempo massimo: con segnale debole non si aspetta all'infinito.
// Se la rete non risponde entro ATTESA_MS e c'è una copia salvata, si usa quella;
// la richiesta di rete continua in sottofondo e, se arriva, aggiorna la copia.
const ATTESA_MS = 3000;

function dallaCache(req) {
  return caches.match(req, { ignoreSearch: true }).then(
    // Pagine non salvate (es. un indirizzo con #ancora o ?parametri): si ripiega sulla pagina principale.
    (r) => r || (req.mode === "navigate" ? caches.match("./") : undefined)
  );
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const rete = fetch(req).then((r) => {
    if (r.ok && r.status === 200) {
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copia)).catch(() => {});
    }
    return r;
  });
  e.waitUntil(rete.catch(() => {}));
  e.respondWith(new Promise((risolvi) => {
    let fatto = false;
    const usa = (r) => { if (!fatto && r) { fatto = true; risolvi(r); } };
    const timer = setTimeout(() => dallaCache(req).then(usa), ATTESA_MS);
    rete.then((r) => { clearTimeout(timer); usa(r); })
      .catch(() => dallaCache(req).then((r) => { clearTimeout(timer); usa(r || Response.error()); }));
  }));
});
