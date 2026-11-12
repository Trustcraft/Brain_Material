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
    assert page.locator("#vuoto").inner_text() == "Nessun risultato."

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
        assert page.locator("#lista img.anteprima").first.evaluate("i => i.complete && i.naturalWidth > 0")
    finally:
        server.shutdown()
