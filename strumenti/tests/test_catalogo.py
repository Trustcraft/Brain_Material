import json
import re
from pathlib import Path

from archivio.caricamento import carica_componenti
from archivio.catalogo import (
    dati_componente,
    genera_html,
    genera_manifest,
    genera_sw,
    json_sicuro,
)

TEMPLATE = Path(__file__).parents[1] / "archivio" / "template.html"


def test_json_sicuro_non_chiude_script():
    valore = {"note": "</script><!-- & ok"}
    out = json_sicuro(valore)
    assert "</" not in out and "<!--" not in out and "&" not in out
    assert json.loads(out) == valore


def test_dati_componente(crea_scheda):
    c = carica_componenti(crea_scheda("dht22", interfacce=["I2C"]))[0]
    d = dati_componente(c, "img/dht22-pinout.webp", None)
    assert d["id"] == "dht22"
    assert d["interfacce"] == ["I2C"]
    assert d["pinout"] == "img/dht22-pinout.webp" and d["foto"] is None
    assert "cartella" not in d


def test_html_contiene_dati(crea_scheda):
    c = carica_componenti(crea_scheda("dht22"))[0]
    html = genera_html([dati_componente(c, None, None)])
    assert '"id":"dht22"' in html
    assert "/*__DATI__*/" not in html


def test_html_nessuna_risorsa_esterna():
    testo = TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r'(src|href)\s*=\s*["\']https?:', testo)
    assert "@import" not in testo
    # innerHTML con dati utente permetterebbe di iniettare HTML dalle note.
    assert "innerHTML" not in testo


def test_sw_versione_e_file():
    sw = genera_sw(["index.html", "img/a.webp"], "abc123")
    assert "archivio-abc123" in sw
    assert '"img/a.webp"' in sw


def test_manifest_valido():
    m = json.loads(genera_manifest())
    assert m["display"] == "standalone"
    assert m["start_url"] == "./"
    assert m["name"] == "Archivio componenti"
