"""Lettura e validazione delle schede in componenti/<id>/scheda.yaml."""

import re
from pathlib import Path

import yaml

from .modello import CATEGORIE, STATI, Componente, ErroreScheda

RE_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
OBBLIGATORI = ("id", "nome", "categoria", "stato", "quantita")
TESTI_OPZIONALI = ("produttore", "modello", "posizione", "tensione", "datasheet_url", "note")
LISTE = ("interfacce", "tag", "progetti")
AMMESSI = set(OBBLIGATORI) | set(TESTI_OPZIONALI) | set(LISTE)


def carica_componenti(radice: Path) -> list[Componente]:
    cartella_componenti = radice / "componenti"
    if not cartella_componenti.is_dir():
        return []
    cartelle = sorted(
        p for p in cartella_componenti.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
    # Ordinare per nome cartella (== id) rende l'output deterministico,
    # indipendente dall'ordine in cui il filesystem restituisce le voci.
    return [_carica(cartella, radice) for cartella in cartelle]


def _carica(cartella: Path, radice: Path) -> Componente:
    file = cartella / "scheda.yaml"
    rel = file.relative_to(radice).as_posix()

    def errore(msg: str) -> ErroreScheda:
        return ErroreScheda(f"{rel}: {msg}")

    if not file.is_file():
        raise errore("file mancante")
    try:
        # safe_load costruisce solo tipi semplici (dict, list, str, int...):
        # un file YAML non può mai far eseguire codice.
        dati = yaml.safe_load(file.read_text(encoding="utf-8"))
    except UnicodeDecodeError as e:
        raise errore("il file deve essere salvato in UTF-8 (contiene caratteri in un'altra codifica)") from e
    except yaml.YAMLError as e:
        riga = getattr(getattr(e, "problem_mark", None), "line", None)
        dove = f" (riga {riga + 1})" if riga is not None else ""
        raise errore(f"YAML non valido{dove}") from e
    if not isinstance(dati, dict):
        raise errore("deve contenere un dizionario di campi (es. 'nome: ...')")

    # I campi sconosciuti sono un errore: quasi sempre sono refusi
    # (es. 'quantità' invece di 'quantita') che altrimenti verrebbero persi in silenzio.
    for chiave in dati:
        if chiave not in AMMESSI:
            raise errore(f"campo sconosciuto: '{chiave}'")
    for campo in OBBLIGATORI:
        if dati.get(campo) is None:
            raise errore(f"campo obbligatorio mancante: '{campo}'")

    id_ = dati["id"]
    if not isinstance(id_, str) or not RE_ID.match(id_):
        raise errore(f"'id' non valido: {id_!r} (solo a-z, 0-9 e trattini)")
    if id_ != cartella.name:
        raise errore(f"'id' diverso dal nome della cartella: {id_!r} != {cartella.name!r}")
    if dati["categoria"] not in CATEGORIE:
        raise errore(
            f"campo 'categoria' non valido: {dati['categoria']!r} (ammessi: {', '.join(CATEGORIE)})"
        )
    if dati["stato"] not in STATI:
        raise errore(f"campo 'stato' non valido: {dati['stato']!r} (ammessi: {', '.join(STATI)})")
    q = dati["quantita"]
    # bool è una sottoclasse di int in Python (True == 1): va escluso esplicitamente.
    if isinstance(q, bool) or not isinstance(q, int) or q < 0:
        raise errore(f"'quantita' deve essere un intero >= 0, trovato {q!r}")
    if not isinstance(dati["nome"], str):
        raise errore("'nome' deve essere un testo")

    testi = {}
    for campo in TESTI_OPZIONALI:
        v = dati.get(campo)
        if v is not None and not isinstance(v, (str, int, float)):
            raise errore(f"'{campo}' deve essere un testo")
        testi[campo] = None if v is None else str(v)

    liste = {}
    for campo in LISTE:
        v = dati.get(campo)
        if v is None:
            v = []
        if not isinstance(v, list):
            raise errore(f"'{campo}' deve essere una lista, es. [I2C, SPI]")
        liste[campo] = tuple(str(x) for x in v)

    return Componente(
        id=id_,
        nome=dati["nome"],
        categoria=dati["categoria"],
        stato=dati["stato"],
        quantita=q,
        cartella=cartella,
        **testi,
        **liste,
    )
