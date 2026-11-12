"""Generazione della pagina del catalogo, del manifest PWA e del service worker."""

import json
from dataclasses import asdict
from pathlib import Path

from .modello import Componente

TEMPLATE = Path(__file__).with_name("template.html")
SEGNAPOSTO = "/*__DATI__*/"

ICONA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="12" fill="#1f6f5c"/>
<rect x="18" y="18" width="28" height="28" rx="3" fill="#e8f3ef"/>
<g stroke="#e8f3ef" stroke-width="3" stroke-linecap="round">
<path d="M24 10v8M32 10v8M40 10v8M24 46v8M32 46v8M40 46v8M10 24h8M10 32h8M10 40h8M46 24h8M46 32h8M46 40h8"/>
</g>
</svg>
"""


def dati_componente(c: Componente, pinout: str | None, foto: str | None) -> dict:
    d = asdict(c)
    del d["cartella"]  # percorso locale: non serve alla pagina e non va pubblicato
    for k, v in d.items():
        if isinstance(v, tuple):
            d[k] = list(v)
    d["pinout"] = pinout
    d["foto"] = foto
    return d


def json_sicuro(obj) -> str:
    # Il JSON finisce dentro un tag <script>: se una nota contenesse "</script>"
    # chiuderebbe il tag e romperebbe la pagina. Scrivere <, > e & come escape
    # Unicode (<...) dà lo stesso valore dopo JSON.parse ma non è più HTML.
    testo = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return testo.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def genera_html(dati: list[dict]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(SEGNAPOSTO) != 1:
        raise RuntimeError("template.html deve contenere il segnaposto dei dati una sola volta")
    return template.replace(SEGNAPOSTO, json_sicuro(dati))


def genera_sw(file_da_cachare: list[str], versione: str) -> str:
    elenco = json.dumps(["./", *file_da_cachare])
    # Strategia "prima la rete, con tempo massimo": online si vede l'ultima versione,
    # offline o con rete lentissima si usa l'ultima copia salvata. Il nome della cache contiene
    # un hash del contenuto, così un catalogo nuovo sostituisce quello vecchio.
    return f"""const CACHE = "archivio-{versione}";
const FILE = {elenco};

self.addEventListener("install", (e) => {{
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILE)).then(() => self.skipWaiting()));
}});

self.addEventListener("activate", (e) => {{
  e.waitUntil(
    caches.keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
}});

// Rete con tempo massimo: con segnale debole non si aspetta all'infinito.
// Se la rete non risponde entro ATTESA_MS e c'è una copia salvata, si usa quella;
// la richiesta di rete continua in sottofondo e, se arriva, aggiorna la copia.
const ATTESA_MS = 3000;

function dallaCache(req) {{
  return caches.match(req, {{ ignoreSearch: true }}).then(
    // Pagine non salvate (es. un indirizzo con #ancora o ?parametri): si ripiega sulla pagina principale.
    (r) => r || (req.mode === "navigate" ? caches.match("./") : undefined)
  );
}}

self.addEventListener("fetch", (e) => {{
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const rete = fetch(req).then((r) => {{
    if (r.ok && r.status === 200) {{
      const copia = r.clone();
      caches.open(CACHE).then((c) => c.put(req, copia)).catch(() => {{}});
    }}
    return r;
  }});
  e.waitUntil(rete.catch(() => {{}}));
  e.respondWith(new Promise((risolvi) => {{
    let fatto = false;
    const usa = (r) => {{ if (!fatto && r) {{ fatto = true; risolvi(r); }} }};
    const timer = setTimeout(() => dallaCache(req).then(usa), ATTESA_MS);
    rete.then((r) => {{ clearTimeout(timer); usa(r); }})
      .catch(() => dallaCache(req).then((r) => {{ clearTimeout(timer); usa(r || Response.error()); }}));
  }}));
}});
"""


def genera_manifest() -> str:
    manifest = {
        "name": "Archivio componenti",
        "short_name": "Componenti",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f2f2f7",
        "theme_color": "#f2f2f7",
        "icons": [{"src": "icona.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}],
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
