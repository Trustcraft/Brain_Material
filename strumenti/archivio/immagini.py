"""Individuazione e ridimensionamento delle immagini (pinout e foto)."""

from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .modello import ErroreScheda

LATO_MASSIMO = 1200
ESTENSIONI = {".png", ".jpg", ".jpeg", ".webp"}


def trova_immagine(cartella: Path, nome: str, radice: Path) -> Path | None:
    candidati = sorted(
        p
        for p in cartella.iterdir()
        if p.is_file() and p.stem.lower() == nome and p.suffix.lower() in ESTENSIONI
    )
    if len(candidati) > 1:
        # Meglio un errore che scegliere a caso: con due pinout non sappiamo quale è giusto.
        rel = cartella.relative_to(radice).as_posix()
        elenco = ", ".join(p.name for p in candidati)
        raise ErroreScheda(f"{rel}/: più file '{nome}' trovati: {elenco} (tienine uno solo)")
    return candidati[0] if candidati else None


def esporta_immagine(sorgente: Path, destinazione: Path, radice: Path) -> None:
    try:
        with Image.open(sorgente) as im:
            im.load()
            # Le foto da telefono sono spesso salvate "di lato" con un'indicazione
            # di rotazione nei metadati EXIF: la applichiamo ai pixel, poi i metadati
            # vengono scartati (così anche eventuali coordinate GPS non finiscono online).
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA" if _ha_trasparenza(im) else "RGB")
            # thumbnail riduce mantenendo le proporzioni e non ingrandisce mai.
            im.thumbnail((LATO_MASSIMO, LATO_MASSIMO), Image.Resampling.LANCZOS)
            destinazione.parent.mkdir(parents=True, exist_ok=True)
            im.save(destinazione, format="WEBP", quality=80, method=6)
    except (UnidentifiedImageError, OSError) as e:
        rel = sorgente.relative_to(radice).as_posix()
        raise ErroreScheda(f"{rel}: immagine non leggibile") from e


def _ha_trasparenza(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)
