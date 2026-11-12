from archivio.caricamento import carica_componenti
from archivio.inventario import genera_inventario


def test_totali(crea_scheda):
    crea_scheda("a", stato="confermato")
    crea_scheda("b", stato="ipotesi")
    radice = crea_scheda("c", stato="da_identificare")
    md = genera_inventario(carica_componenti(radice))
    assert md.startswith("# Inventario componenti\n")
    assert "Totale: 3 componenti (1 confermati, 1 ipotesi, 1 da identificare)" in md


def test_ordine_categorie(crea_scheda):
    crea_scheda("schermo", categoria="display")
    radice = crea_scheda("temp", categoria="sensore", interfacce=["I2C", "SPI"], tensione="3.3V")
    md = genera_inventario(carica_componenti(radice))
    assert md.index("## sensore") < md.index("## display")
    assert "## microcontrollore" not in md
    assert "| temp | Test | 1 | I2C, SPI | 3.3V | confermato |" in md
    assert "| schermo | Test | 1 | — | — | confermato |" in md


def test_pipe_escapata(crea_scheda):
    radice = crea_scheda("a", nome="Modulo A|B")
    assert "Modulo A\\|B" in genera_inventario(carica_componenti(radice))


def test_lista_vuota():
    assert "Totale: 0 componenti" in genera_inventario([])
