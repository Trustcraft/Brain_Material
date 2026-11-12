"""Riassunto compatto INVENTARIO.md: una riga per componente.

Serve a Claude nei progetti futuri: leggere un solo file breve costa molto meno
che aprire tutte le schede, e basta per capire "cosa c'è".
"""

from .modello import CATEGORIE, Componente

VUOTO = "—"


def _cella(valore: str | None) -> str:
    if not valore:
        return VUOTO
    # '|' separa le colonne in Markdown; a capo romperebbe la riga della tabella.
    return valore.replace("|", "\\|").replace("\n", " ")


def genera_inventario(componenti: list[Componente]) -> str:
    conteggio = {s: sum(1 for c in componenti if c.stato == s) for s in ("confermato", "ipotesi", "da_identificare")}
    righe = [
        "# Inventario componenti",
        "",
        "> File generato da `strumenti/genera_catalogo.py`: non modificarlo a mano.",
        "",
        f"Totale: {len(componenti)} componenti ({conteggio['confermato']} confermati, "
        f"{conteggio['ipotesi']} ipotesi, {conteggio['da_identificare']} da identificare)",
    ]
    for categoria in CATEGORIE:
        gruppo = [c for c in componenti if c.categoria == categoria]
        if not gruppo:
            continue
        righe += [
            "",
            f"## {categoria}",
            "",
            "| id | nome | q.tà | interfacce | tensione | stato |",
            "|---|---|---|---|---|---|",
        ]
        for c in gruppo:
            righe.append(
                f"| {c.id} | {_cella(c.nome)} | {c.quantita} | {_cella(', '.join(c.interfacce))} "
                f"| {_cella(c.tensione)} | {c.stato} |"
            )
    return "\n".join(righe) + "\n"
