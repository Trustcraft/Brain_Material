import hashlib

from PIL import Image

from genera_catalogo import main


def hash_albero(radice):
    return {
        p.relative_to(radice).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(radice.rglob("*"))
        if p.is_file()
    }


def con_pinout(crea_scheda, id_="dht22"):
    radice = crea_scheda(id_)
    Image.new("RGB", (1600, 800), (10, 120, 90)).save(radice / "componenti" / id_ / "pinout.png")
    return radice


def test_genera_tutto(crea_scheda, capsys):
    radice = con_pinout(crea_scheda)
    assert main(["--radice", str(radice)]) == 0
    for f in ("index.html", "img/dht22-pinout.webp", "sw.js", "manifest.webmanifest", "icona.svg"):
        assert (radice / "catalogo" / f).is_file(), f
    assert (radice / "INVENTARIO.md").is_file()
    html = (radice / "catalogo" / "index.html").read_text(encoding="utf-8")
    assert '"pinout":"img/dht22-pinout.webp"' in html
    assert "img/dht22-pinout.webp" in (radice / "catalogo" / "sw.js").read_text()
    assert "Catalogo generato: 1 componenti" in capsys.readouterr().out


def test_errore_codice_1(crea_scheda, capsys):
    radice = con_pinout(crea_scheda)
    assert main(["--radice", str(radice)]) == 0
    prima = hash_albero(radice / "catalogo")
    crea_scheda("rotto", stato="ok")
    assert main(["--radice", str(radice)]) == 1
    assert "componenti/rotto/scheda.yaml:" in capsys.readouterr().err
    assert hash_albero(radice / "catalogo") == prima


def test_immagine_rotta_non_cancella_catalogo(crea_scheda):
    radice = con_pinout(crea_scheda)
    assert main(["--radice", str(radice)]) == 0
    prima = hash_albero(radice / "catalogo")
    (radice / "componenti" / "dht22" / "foto.jpg").write_bytes(b"rotto")
    assert main(["--radice", str(radice)]) == 1
    assert hash_albero(radice / "catalogo") == prima


def test_deterministico(crea_scheda):
    radice = con_pinout(crea_scheda)
    main(["--radice", str(radice)])
    primo = hash_albero(radice / "catalogo")
    main(["--radice", str(radice)])
    assert hash_albero(radice / "catalogo") == primo


def test_rimuove_immagini_orfane(crea_scheda):
    radice = con_pinout(crea_scheda)
    main(["--radice", str(radice)])
    orfana = radice / "catalogo" / "img" / "vecchio-pinout.webp"
    orfana.write_bytes(b"x")
    main(["--radice", str(radice)])
    assert not orfana.exists()


def test_preserva_vercel_json(crea_scheda):
    radice = con_pinout(crea_scheda)
    (radice / "catalogo").mkdir()
    (radice / "catalogo" / "vercel.json").write_text("{}")
    main(["--radice", str(radice)])
    assert (radice / "catalogo" / "vercel.json").read_text() == "{}"
