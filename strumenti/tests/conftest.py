from pathlib import Path

import pytest
import yaml

DEFAULT = {"nome": "Test", "categoria": "sensore", "stato": "confermato", "quantita": 1}


@pytest.fixture
def crea_scheda(tmp_path):
    """Restituisce crea(cartella_id, **campi): scrive componenti/<id>/scheda.yaml e ritorna la radice.

    Un campo con valore None viene rimosso dalla scheda (utile per testare i campi mancanti).
    """

    def crea(cartella_id: str, /, **campi) -> Path:
        dati = {"id": cartella_id, **DEFAULT, **campi}
        dati = {k: v for k, v in dati.items() if v is not None}
        cartella = tmp_path / "componenti" / cartella_id
        cartella.mkdir(parents=True, exist_ok=True)
        (cartella / "scheda.yaml").write_text(
            yaml.safe_dump(dati, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        return tmp_path

    return crea
