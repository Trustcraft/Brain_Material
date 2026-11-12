"""Modello dati dell'archivio: costanti ammesse, errore e componente."""

from dataclasses import dataclass
from pathlib import Path

CATEGORIE = (
    "microcontrollore",
    "sensore",
    "modulo",
    "attuatore",
    "display",
    "alimentazione",
    "passivo",
    "connettore",
    "altro",
)
STATI = ("da_identificare", "ipotesi", "confermato")


class ErroreScheda(Exception):
    """Errore di una scheda. Il messaggio inizia sempre con il percorso del file."""


@dataclass(frozen=True)
class Componente:
    # frozen=True: un componente caricato non cambia più; così può essere
    # passato a generatori diversi senza rischio che uno lo modifichi per l'altro.
    id: str
    nome: str
    categoria: str
    stato: str
    quantita: int
    produttore: str | None
    modello: str | None
    posizione: str | None
    tensione: str | None
    interfacce: tuple[str, ...]
    tag: tuple[str, ...]
    datasheet_url: str | None
    note: str | None
    progetti: tuple[str, ...]
    cartella: Path
