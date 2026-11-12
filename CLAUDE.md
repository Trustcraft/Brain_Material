# Archivio componenti elettronici — istruzioni per Claude

Questo repo è l'inventario dei componenti elettronici dell'utente (microcontrollori,
sensori, moduli, …). Rispondi e documenta in **italiano**.

## Consultazione da un altro progetto

1. Leggi **`INVENTARIO.md`**: una riga per componente (id, nome, quantità, interfacce,
   tensione, stato). Di solito basta per capire cosa c'è.
2. Apri solo le `componenti/<id>/scheda.yaml` rilevanti per dettagli e note.
3. Tratta i componenti `ipotesi` e `da_identificare` come **non verificati**: dillo
   all'utente prima di basarci un progetto.

## Struttura

```
componenti/<id>/scheda.yaml   ← fonte di verità
componenti/<id>/pinout.*      ← png|jpg|jpeg|webp, uno solo
componenti/<id>/foto.*        ← opzionale, foto del pezzo reale
da_identificare/              ← foto grezze di componenti sconosciuti
catalogo/, INVENTARIO.md      ← GENERATI: non modificarli a mano
strumenti/                    ← generatore + test
```

## Campi di `scheda.yaml`

| Campo | Obbl. | Tipo | Note |
|---|---|---|---|
| `id` | sì | stringa | uguale al nome cartella, `a-z0-9-` |
| `nome` | sì | stringa | nome leggibile |
| `categoria` | sì | enum | `microcontrollore`, `sensore`, `modulo`, `attuatore`, `display`, `alimentazione`, `passivo`, `connettore`, `altro` |
| `stato` | sì | enum | `da_identificare`, `ipotesi`, `confermato` |
| `quantita` | sì | intero ≥ 0 | |
| `produttore` | no | stringa | |
| `modello` | no | stringa | sigla esatta; usata per "Cerca datasheet" |
| `posizione` | no | stringa | dove si trova fisicamente |
| `tensione` | no | stringa | es. `3.3V (5V tollerante)` |
| `interfacce` | no | lista | es. `[I2C, SPI, UART, ADC, PWM, GPIO]` |
| `tag` | no | lista | |
| `datasheet_url` | no | URL | fonte ufficiale (niente PDF nel repo) |
| `note` | no | testo | avvertenze, trucchi, motivazione dell'identificazione |
| `progetti` | no | lista | dove è stato usato |

Campi sconosciuti sono un errore (di solito sono refusi, es. `quantità`).
Usa nomi di interfaccia coerenti con quelli già presenti in `INVENTARIO.md`.

## Identificare un componente da foto

1. Leggi marcature, package, numero e disposizione dei pin.
2. Crea `componenti/<id>/` con `stato: ipotesi`. In `note` scrivi: su cosa ti basi,
   confidenza (alta/media/bassa) e come verificarlo (es. misura col tester).
3. Sposta la foto migliore in `componenti/<id>/foto.jpg`.
4. Solo l'utente porta lo stato a `confermato`.

## Pinout

Un'immagine pulita del pinout in `pinout.png`/`.jpg`. Se non ne trovi una affidabile,
ritaglia la pagina del pinout dal datasheet ufficiale. Non inventare pinout.

## Dopo ogni modifica

```bash
python strumenti/genera_catalogo.py
python -m pytest -m "not browser" -q
```

Committa schede, immagini, `catalogo/` e `INVENTARIO.md` insieme. Al push sul branch
principale la GitHub Action rigenera e pubblica su Vercel.
Non scrivere dati sensibili nelle schede: il sito è pubblico a chi ha il link.
