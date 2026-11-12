import pytest

from archivio.caricamento import carica_componenti
from archivio.modello import ErroreScheda


def test_scheda_valida(crea_scheda):
    radice = crea_scheda("dht22", interfacce=["I2C"])
    componenti = carica_componenti(radice)
    assert len(componenti) == 1
    c = componenti[0]
    assert c.id == "dht22"
    assert c.interfacce == ("I2C",)
    assert c.produttore is None
    assert c.cartella == radice / "componenti" / "dht22"


def test_ordinamento_per_id(crea_scheda):
    crea_scheda("b-x")
    radice = crea_scheda("a-y")
    assert [c.id for c in carica_componenti(radice)] == ["a-y", "b-x"]


def test_cartella_vuota_restituisce_lista_vuota(tmp_path):
    assert carica_componenti(tmp_path) == []
    (tmp_path / "componenti").mkdir()
    (tmp_path / "componenti" / ".gitkeep").write_text("")
    assert carica_componenti(tmp_path) == []


@pytest.mark.parametrize(
    "campi, messaggio",
    [
        ({"nome": None}, "campo obbligatorio mancante: 'nome'"),
        ({"stato": "ok"}, "campo 'stato' non valido: 'ok'"),
        ({"categoria": "boh"}, "campo 'categoria' non valido: 'boh'"),
        ({"quantita": "3"}, "'quantita' deve essere un intero >= 0"),
        ({"quantita": -1}, "'quantita' deve essere un intero >= 0"),
        ({"quantita": True}, "'quantita' deve essere un intero >= 0"),
        ({"id": "altro"}, "'id' diverso dal nome della cartella"),
        ({"interfacce": "I2C"}, "'interfacce' deve essere una lista"),
        ({"colore": "rosso"}, "campo sconosciuto: 'colore'"),
    ],
)
def test_errori(crea_scheda, tmp_path, campi, messaggio):
    # crea_scheda usa l'id come nome cartella; per testare id != cartella
    # scriviamo nella cartella "x" e sovrascriviamo il campo id.
    radice = crea_scheda("x", **campi)
    with pytest.raises(ErroreScheda) as e:
        carica_componenti(radice)
    assert str(e.value).startswith("componenti/x/scheda.yaml: ")
    assert messaggio in str(e.value)


def test_id_non_valido(crea_scheda):
    radice = crea_scheda("Bad_Id")
    with pytest.raises(ErroreScheda, match="'id' non valido"):
        carica_componenti(radice)


def scrivi(tmp_path, testo):
    cartella = tmp_path / "componenti" / "x"
    cartella.mkdir(parents=True)
    (cartella / "scheda.yaml").write_text(testo, encoding="utf-8")


def test_yaml_malformato(tmp_path):
    scrivi(tmp_path, "nome: [\n")
    with pytest.raises(ErroreScheda, match="componenti/x/scheda.yaml: YAML non valido"):
        carica_componenti(tmp_path)


@pytest.mark.parametrize("testo", ["", "- a\n"])
def test_yaml_vuoto_o_non_dizionario(tmp_path, testo):
    scrivi(tmp_path, testo)
    with pytest.raises(ErroreScheda, match="deve contenere un dizionario"):
        carica_componenti(tmp_path)


def test_cartella_senza_scheda(tmp_path):
    (tmp_path / "componenti" / "x").mkdir(parents=True)
    with pytest.raises(ErroreScheda, match="componenti/x/scheda.yaml: file mancante"):
        carica_componenti(tmp_path)
