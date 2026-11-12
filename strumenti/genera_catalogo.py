"""Genera catalogo/ e INVENTARIO.md a partire da componenti/*/scheda.yaml.

Uso:  python strumenti/genera_catalogo.py [--radice PERCORSO]
"""

import argparse
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from archivio.caricamento import carica_componenti  # noqa: E402
from archivio.catalogo import (  # noqa: E402
    ICONA_SVG,
    LATI_ICONA,
    dati_componente,
    genera_html,
    genera_icona_png,
    genera_manifest,
    genera_sw,
)
from archivio.immagini import esporta_immagine, trova_immagine  # noqa: E402
from archivio.inventario import genera_inventario  # noqa: E402
from archivio.modello import ErroreScheda  # noqa: E402

# File e cartelle che stanno in catalogo/ ma non sono generati: vanno conservati.
# .vercel/ viene creata da `vercel link` e contiene il collegamento al progetto.
CONSERVA = ("vercel.json", ".vercel")


def scrivi(percorso: Path, testo: str) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": stessi byte su Windows e Linux, quindi diff git puliti.
    percorso.write_text(testo, encoding="utf-8", newline="\n")


def costruisci(radice: Path, uscita: Path, inventario: Path) -> int:
    """Genera il catalogo completo in `uscita`. Solleva ErroreScheda se qualcosa non va."""
    componenti = carica_componenti(radice)
    dati = []
    for c in componenti:
        percorsi = {}
        for tipo in ("pinout", "foto"):
            sorgente = trova_immagine(c.cartella, tipo, radice)
            if sorgente:
                rel = f"img/{c.id}-{tipo}.webp"
                esporta_immagine(sorgente, uscita / rel, radice)
                percorsi[tipo] = rel
        dati.append(dati_componente(c, percorsi.get("pinout"), percorsi.get("foto")))

    scrivi(uscita / "index.html", genera_html(dati))
    scrivi(uscita / "manifest.webmanifest", genera_manifest())
    scrivi(uscita / "icona.svg", ICONA_SVG)
    for lato in LATI_ICONA:
        (uscita / f"icona-{lato}.png").write_bytes(genera_icona_png(lato))

    # La versione della cache offline è l'hash di tutto il contenuto: cambia
    # solo quando cambia davvero qualcosa, e allora il telefono scarica la nuova copia.
    file = sorted(p.relative_to(uscita).as_posix() for p in uscita.rglob("*") if p.is_file())
    h = hashlib.sha256()
    for nome in file:
        h.update(nome.encode())
        h.update((uscita / nome).read_bytes())
    scrivi(uscita / "sw.js", genera_sw(file, h.hexdigest()[:12]))
    scrivi(inventario, genera_inventario(componenti))
    return len(componenti)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera il catalogo dei componenti.")
    parser.add_argument("--radice", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    radice: Path = args.radice.resolve()
    catalogo = radice / "catalogo"

    # Tutto viene costruito in una cartella temporanea e sostituito solo alla fine:
    # se una scheda o un'immagine è sbagliata, il catalogo precedente resta intatto
    # e la copia offline non va mai persa.
    with tempfile.TemporaryDirectory(dir=radice, prefix=".catalogo-") as tmp:
        tmp = Path(tmp)
        uscita, inventario = tmp / "catalogo", tmp / "INVENTARIO.md"
        try:
            n = costruisci(radice, uscita, inventario)
        except ErroreScheda as e:
            print(f"ERRORE: {e}", file=sys.stderr)
            return 1
        # Copiati dopo il calcolo della versione: non entrano nella cache offline.
        for nome in CONSERVA:
            if (catalogo / nome).is_dir():
                shutil.copytree(catalogo / nome, uscita / nome)
            elif (catalogo / nome).is_file():
                shutil.copy2(catalogo / nome, uscita / nome)
        # Scambio con due spostamenti (rename, istantanei sullo stesso disco) invece di
        # cancellare e poi copiare: se qualcosa va storto a metà, il vecchio catalogo
        # viene rimesso al suo posto. Il vecchio finisce nella cartella temporanea,
        # che viene eliminata automaticamente all'uscita dal blocco "with".
        vecchio = tmp / "vecchio"
        if catalogo.exists():
            catalogo.rename(vecchio)
        try:
            uscita.rename(catalogo)
        except OSError:
            if vecchio.exists():
                vecchio.rename(catalogo)
            raise
        inventario.replace(radice / "INVENTARIO.md")

    print(f"Catalogo generato: {n} componenti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
