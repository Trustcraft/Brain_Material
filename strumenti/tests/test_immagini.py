import pytest
from PIL import Image

from archivio.immagini import LATO_MASSIMO, esporta_immagine, trova_immagine
from archivio.modello import ErroreScheda


def img(percorso, dimensioni=(100, 100), formato=None):
    percorso.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", dimensioni, (200, 30, 30)).save(percorso, format=formato)
    return percorso


def test_trova_estensione_maiuscola(tmp_path):
    cartella = tmp_path / "componenti" / "a"
    p = img(cartella / "pinout.JPG", formato="JPEG")
    assert trova_immagine(cartella, "pinout", tmp_path) == p


def test_nessuna_immagine(tmp_path):
    cartella = tmp_path / "componenti" / "a"
    cartella.mkdir(parents=True)
    (cartella / "pinout.txt").write_text("non immagine")
    assert trova_immagine(cartella, "pinout", tmp_path) is None


def test_due_pinout_errore(tmp_path):
    cartella = tmp_path / "componenti" / "a"
    img(cartella / "pinout.png")
    img(cartella / "pinout.jpg", formato="JPEG")
    with pytest.raises(ErroreScheda, match="più file 'pinout' trovati"):
        trova_immagine(cartella, "pinout", tmp_path)


def test_ridimensiona_lato_lungo(tmp_path):
    sorgente = img(tmp_path / "s.png", (3000, 1500))
    dest = tmp_path / "out" / "d.webp"
    esporta_immagine(sorgente, dest, tmp_path)
    with Image.open(dest) as r:
        assert r.size == (LATO_MASSIMO, 600)
        assert r.format == "WEBP"


def test_non_ingrandisce(tmp_path):
    sorgente = img(tmp_path / "s.png", (400, 300))
    dest = tmp_path / "d.webp"
    esporta_immagine(sorgente, dest, tmp_path)
    with Image.open(dest) as r:
        assert r.size == (400, 300)


def test_immagine_corrotta(tmp_path):
    sorgente = tmp_path / "componenti" / "a" / "pinout.png"
    sorgente.parent.mkdir(parents=True)
    sorgente.write_bytes(b"\x00\x01nonunpng")
    with pytest.raises(ErroreScheda, match="componenti/a/pinout.png: immagine non leggibile"):
        esporta_immagine(sorgente, tmp_path / "d.webp", tmp_path)


def test_esportazione_deterministica(tmp_path):
    sorgente = img(tmp_path / "s.png", (1600, 900))
    esporta_immagine(sorgente, tmp_path / "a.webp", tmp_path)
    esporta_immagine(sorgente, tmp_path / "b.webp", tmp_path)
    assert (tmp_path / "a.webp").read_bytes() == (tmp_path / "b.webp").read_bytes()


def test_png_trasparente_e_rotazione_exif(tmp_path):
    # PNG con trasparenza (RGBA) e foto con rotazione EXIF: casi tipici reali.
    sorgente = tmp_path / "t.png"
    Image.new("RGBA", (200, 100), (0, 0, 0, 0)).save(sorgente)
    esporta_immagine(sorgente, tmp_path / "t.webp", tmp_path)
    foto = tmp_path / "f.jpg"
    im = Image.new("RGB", (200, 100))
    exif = im.getexif()
    exif[0x0112] = 6  # Orientation: ruotare di 90°
    im.save(foto, exif=exif)
    esporta_immagine(foto, tmp_path / "f.webp", tmp_path)
    with Image.open(tmp_path / "f.webp") as r:
        assert r.size == (100, 200)
        assert 0x0112 not in r.getexif()
