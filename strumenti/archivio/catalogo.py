"""Generazione della pagina del catalogo, del manifest PWA e del service worker."""

import io
import json
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageDraw

from .modello import Componente

TEMPLATE = Path(__file__).with_name("template.html")
SEGNAPOSTO = "/*__DATI__*/"

ICONA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" rx="22" fill="#1e5c45"/>
<g fill="#e7f2ec">
<path d="M32.8 20h4.4v10h-4.4zM42.8 20h4.4v10h-4.4zM52.8 20h4.4v10h-4.4zM62.8 20h4.4v10h-4.4zM32.8 70h4.4v10h-4.4zM42.8 70h4.4v10h-4.4zM52.8 70h4.4v10h-4.4zM62.8 70h4.4v10h-4.4zM20 32.8h10v4.4H20zM20 42.8h10v4.4H20zM20 52.8h10v4.4H20zM20 62.8h10v4.4H20zM70 32.8h10v4.4H70zM70 42.8h10v4.4H70zM70 52.8h10v4.4H70zM70 62.8h10v4.4H70z"/>
<rect x="27" y="27" width="46" height="46" rx="5"/>
</g>
<circle cx="36.5" cy="36.5" r="3.5" fill="#1e5c45"/>
</svg>
"""


LATI_ICONA = (180, 192, 512)


def genera_icona_png(lato: int) -> bytes:
    """Icona per la schermata Home: chip con piedini su fondo verde serigrafia.

    Quadrata, opaca e a tutto campo: iOS e Android applicano da soli la maschera
    arrotondata (e iOS riempirebbe di nero le parti trasparenti). Il disegno sta
    nel 60% centrale, così resta intero anche con le maschere "maskable".
    Disegnata 4 volte più grande e poi ridotta, per avere bordi morbidi.
    """
    s = lato * 4
    im = Image.new("RGB", (s, s), (30, 92, 69))
    d = ImageDraw.Draw(im)
    u = s / 100  # unità: percentuale del lato
    chiaro, scuro = (231, 242, 236), (30, 92, 69)
    for i in range(4):
        c = 35 + i * 10
        for x0, y0, x1, y1 in (
            (c - 2.2, 20, c + 2.2, 30), (c - 2.2, 70, c + 2.2, 80),
            (20, c - 2.2, 30, c + 2.2), (70, c - 2.2, 80, c + 2.2),
        ):
            d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=1.2 * u, fill=chiaro)
    d.rounded_rectangle([27 * u, 27 * u, 73 * u, 73 * u], radius=5 * u, fill=chiaro)
    d.ellipse([33 * u, 33 * u, 40 * u, 40 * u], fill=scuro)  # pallino del pin 1
    im = im.resize((lato, lato), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


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
        "icons": [
            {"src": "icona-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": "icona.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
        ],
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
