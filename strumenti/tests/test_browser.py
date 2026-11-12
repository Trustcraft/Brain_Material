"""Verifica del catalogo in un browser vero (Chromium via Playwright).

Saltati automaticamente se Playwright non è installato, così la CI non ne dipende.
"""

import functools
import os
import http.server
import threading

import pytest
from PIL import Image

from genera_catalogo import main

pw = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.browser


@pytest.fixture
def catalogo(crea_scheda):
    crea_scheda("esp32", nome="ESP32 DevKit", categoria="microcontrollore", interfacce=["WiFi", "I2C"])
    crea_scheda("rele-5v", nome="Modulo relè 5V", categoria="attuatore", note="Attivo basso </script>")
    radice = crea_scheda("misterioso", nome="Chip misterioso", stato="ipotesi")
    Image.new("RGB", (800, 600), (30, 30, 200)).save(radice / "componenti" / "esp32" / "pinout.png")
    assert main(["--radice", str(radice)]) == 0
    return radice / "catalogo"


@pytest.fixture
def pagina():
    with pw.sync_playwright() as p:
        # CHROMIUM_PATH: per ambienti con un Chromium preinstallato diverso
        # da quello che il pacchetto Playwright si aspetta.
        percorso = os.environ.get("CHROMIUM_PATH")
        browser = p.chromium.launch(executable_path=percorso) if percorso else p.chromium.launch()
        yield browser
        browser.close()


def visibili(page):
    return page.locator("#lista .scheda").count()


def test_file_locale(catalogo, pagina):
    page = pagina.new_page()
    errori = []
    page.on("console", lambda m: m.type == "error" and errori.append(m.text))
    page.on("pageerror", lambda e: errori.append(str(e)))
    page.goto((catalogo / "index.html").as_uri())

    assert visibili(page) == 3
    assert errori == []

    page.fill("#cerca", "rele")  # senza accento e minuscolo
    assert visibili(page) == 1
    assert "relè" in page.locator("#lista .nome").inner_text()

    page.fill("#cerca", "")
    page.select_option("#f-stato", "ipotesi")
    assert visibili(page) == 1
    assert page.locator("#lista .badge.ipotesi").is_visible()

    page.select_option("#f-stato", "")
    page.fill("#cerca", "nessunacorrispondenza")
    testo = page.locator("#vuoto").inner_text()
    assert testo.startswith("Nessun risultato.") and "filtro" in testo

    page.fill("#cerca", "esp32")
    page.locator("#lista .scheda").first.click()
    assert page.locator("#dettaglio").is_visible()
    primo = page.locator("#dlg-corpo > *").first
    assert primo.locator("img.pinout").count() == 1


def test_note_con_script_resta_testo(catalogo, pagina):
    page = pagina.new_page()
    page.goto((catalogo / "index.html").as_uri())
    page.fill("#cerca", "rele")
    page.locator("#lista .scheda").first.click()
    assert "</script>" in page.locator("#dlg-corpo .note").inner_text()


def test_telefono_senza_scroll_orizzontale(catalogo, pagina):
    page = pagina.new_page(viewport={"width": 375, "height": 800})
    page.goto((catalogo / "index.html").as_uri())
    assert page.evaluate("document.documentElement.scrollWidth") <= 375
    page.locator("#lista .scheda").first.click()
    assert page.evaluate("document.documentElement.scrollWidth") <= 375


def test_offline_con_service_worker(catalogo, pagina):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(catalogo))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        context = pagina.new_context()
        page = context.new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        # Il service worker chiama clients.claim(): appena attivo controlla la pagina
        # (e ha già salvato tutto in cache), senza bisogno di ricaricare.
        page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=10000)
        context.set_offline(True)
        page.reload()
        assert visibili(page) == 3
        assert page.locator("#lista .anteprima img").first.evaluate("i => i.complete && i.naturalWidth > 0")
    finally:
        server.shutdown()


def test_rete_lenta_usa_la_copia_salvata(catalogo, pagina):
    # Segnale debole (es. in negozio): la rete risponde ma lentissima.
    # La pagina deve comparire dalla copia offline entro pochi secondi.
    import time

    ritardo = {"s": 0}

    class Lento(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(catalogo), **k)

        def do_GET(self):
            time.sleep(ritardo["s"])
            super().do_GET()

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lento)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        page = pagina.new_context().new_page()
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=10000)
        ritardo["s"] = 15
        inizio = time.monotonic()
        page.reload(timeout=30000)
        assert time.monotonic() - inizio < 8
        assert visibili(page) == 3
    finally:
        ritardo["s"] = 0
        server.shutdown()


def test_filtro_categoria_e_chiusura_trascinando(catalogo, pagina):
    page = pagina.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
    page.goto((catalogo / "index.html").as_uri())
    page.click('.cat[data-cat="attuatore"]')
    assert visibili(page) == 1
    assert page.get_attribute('.cat[data-cat="attuatore"]', "aria-pressed") == "true"
    page.click('.cat[data-cat=""]')
    assert visibili(page) == 3

    page.locator("#lista .scheda").first.click()
    assert page.locator("#dettaglio").is_visible()
    page.wait_for_timeout(400)  # fine dell'animazione di apertura
    box = page.locator("#testa").bounding_box()
    x, y = box["x"] + 60, box["y"] + 10
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + 200, steps=8)
    page.mouse.up()
    page.wait_for_timeout(300)
    assert not page.locator("#dettaglio").is_visible()


def test_sigla_chip_senza_pinout(catalogo, pagina):
    page = pagina.new_page()
    page.goto((catalogo / "index.html").as_uri())
    # "Modulo relè 5V": nessun modello; "5V" ha lettere e cifre ma è troppo corta → prima parola.
    assert page.locator('.scheda[data-id="rele-5v"] .ic text').text_content() == "MODULO"
