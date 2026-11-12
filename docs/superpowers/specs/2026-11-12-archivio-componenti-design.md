# Archivio componenti elettronici — Design

Data: 2026-11-12
Stato: in revisione

## 1. Obiettivo

Un inventario dei componenti elettronici posseduti (microcontrollori, sensori, moduli,
attuatori, display, alimentazione, passivi…) che sia:

- **consultabile da me** come catalogo visivo con ricerca e filtri, da PC e da telefono,
  anche **offline**, con copia che si aggiorna da sola;
- **consultabile da Claude** in progetti futuri, in modo rapido ed economico;
- capace di gestire componenti **da identificare** (da foto) separandoli da quelli confermati.

**Successo** = in un progetto futuro chiedo "cosa ho per misurare X?" e la risposta arriva
dall'archivio; al banco apro l'app sul telefono senza rete e vedo subito il pinout.

### Fuori scope (YAGNI)

- PDF dei datasheet nel repo: si salva solo il link e si cerca la versione aggiornata.
- Modulo web di inserimento: le schede si creano via chat con Claude o a mano.
- Protezione con login/password del sito.
- Gestione acquisti, prezzi, fornitori.

## 2. Architettura

```
Brain_Material/
├── CLAUDE.md                  ← istruzioni per sessioni Claude future
├── componenti/
│   └── <id>/
│       ├── scheda.yaml        ← fonte di verità (obbligatorio)
│       ├── pinout.(png|jpg|webp)   ← opzionale ma fortemente consigliato
│       └── foto.(png|jpg|webp)     ← opzionale, foto del pezzo reale
├── da_identificare/           ← foto grezze di componenti sconosciuti
├── strumenti/
│   ├── genera_catalogo.py     ← validazione + generazione
│   ├── template.html          ← template della pagina
│   └── test_*.py              ← test pytest
├── catalogo/                  ← GENERATO, committato, non modificare a mano
│   ├── index.html             ← dati JSON incorporati nella pagina
│   ├── img/                   ← immagini ridimensionate
│   ├── manifest.webmanifest
│   └── sw.js                  ← service worker per offline su telefono
├── INVENTARIO.md              ← GENERATO, riassunto compatto per Claude
└── .github/workflows/catalogo.yml
```

Flusso: `scheda.yaml` + immagini → `genera_catalogo.py` → `catalogo/` + `INVENTARIO.md`
→ commit → deploy statico su Vercel.

## 3. Formato `scheda.yaml`

| Campo | Obbligatorio | Tipo | Note |
|---|---|---|---|
| `id` | sì | stringa | uguale al nome cartella, minuscolo, `a-z0-9-` |
| `nome` | sì | stringa | nome leggibile |
| `categoria` | sì | enum | `microcontrollore`, `sensore`, `modulo`, `attuatore`, `display`, `alimentazione`, `passivo`, `connettore`, `altro` |
| `stato` | sì | enum | `da_identificare`, `ipotesi`, `confermato` |
| `quantita` | sì | intero ≥ 0 | |
| `produttore` | no | stringa | |
| `modello` | no | stringa | sigla/codice; usato per il link "cerca datasheet" |
| `posizione` | no | stringa | dove si trova fisicamente |
| `tensione` | no | stringa | testo libero, es. `3.3V (5V tollerante)` |
| `interfacce` | no | lista stringhe | es. `[I2C, SPI, UART, ADC]` |
| `tag` | no | lista stringhe | |
| `datasheet_url` | no | URL | fonte ufficiale |
| `note` | no | stringa multilinea | avvertenze, trucchi, motivazione dell'identificazione |
| `progetti` | no | lista stringhe | dove è stato usato |

Il pinout e la foto vengono rilevati automaticamente dai file presenti nella cartella.

## 4. Generatore (`strumenti/genera_catalogo.py`)

1. **Validazione** di ogni scheda secondo la tabella sopra; controlla anche `id` == nome
   cartella e `id` univoci. Al primo errore si ferma, indicando file e campo:
   meglio un errore chiaro che un catalogo parziale.
2. **Immagini**: ridimensionate a lato massimo 1200 px e convertite in WebP (Pillow),
   così l'intero catalogo resta di pochi MB e si salva tutto offline sul telefono.
3. **`catalogo/index.html`**: i dati vengono incorporati come JSON nella pagina, perché un
   file aperto da disco (`file://`) non può caricare dati esterni con `fetch`. Così la
   pagina funziona con un doppio clic, senza server né rete.
4. **PWA**: `manifest.webmanifest` + `sw.js`. Il service worker mette in cache tutte le
   risorse (pagina e immagini) al primo accesso e le aggiorna quando c'è rete.
   La versione della cache deriva da un hash del contenuto, così ogni nuovo catalogo
   invalida quello vecchio.
5. **`INVENTARIO.md`**: tabella compatta, una riga per componente
   (id, nome, categoria, quantità, interfacce, tensione, stato), ordinata per categoria.
6. Output deterministico (stesso input → stessi file), così i diff in git sono puliti.

Dipendenze: Python 3, `PyYAML`, `Pillow`, `pytest` (in `strumenti/requirements.txt`).

## 5. Interfaccia del catalogo

- Ricerca libera su nome, modello, tag, note, interfacce.
- Filtri: categoria, stato, interfaccia.
- Lista a schede con miniatura del pinout.
- Dettaglio componente in questo ordine: **pinout** (grande, ingrandibile) → **note** →
  dati tecnici → quantità e posizione → foto del pezzo → link datasheet + pulsante
  "Cerca datasheet aggiornato" (ricerca web con `produttore + modello`).
- Badge evidente per `ipotesi` e `da_identificare`.
- Responsive (telefono e PC), tema chiaro/scuro automatico, nessuna libreria esterna
  (tutto inline, così niente dipende dalla rete).

## 6. Identificazione componenti

1. L'utente mette le foto in `da_identificare/` (o le invia in chat).
2. Claude analizza marcature, package, pin e crea `componenti/<id>/` con
   `stato: ipotesi`; in `note` scrive su cosa si basa, livello di confidenza e,
   se utile, come verificarlo (es. misura col tester).
3. L'utente verifica e porta lo stato a `confermato`; le foto grezze vengono spostate
   nella cartella del componente come `foto.*` o eliminate.

## 7. Uso da parte di Claude

- `CLAUDE.md` descrive struttura, campi, enum, workflow di identificazione e le regole
  (rigenerare il catalogo dopo ogni modifica, non toccare `catalogo/` a mano).
- In un altro progetto: aggiungere questo repo alla sessione, leggere `INVENTARIO.md`
  per la panoramica, aprire solo le `scheda.yaml` rilevanti.

## 8. Aggiornamento automatico e deploy

GitHub Action `catalogo.yml`, su push al branch principale:

1. installa le dipendenze ed esegue `pytest`; se fallisce si ferma (il sito online
   resta all'ultima versione funzionante);
2. esegue `genera_catalogo.py`; se `catalogo/` o `INVENTARIO.md` cambiano, li committa
   (così dopo un `git pull` la copia offline su PC è aggiornata);
3. pubblica `catalogo/` su Vercel come sito statico con la CLI (`vercel deploy --prod`),
   usando un token salvato nei secret del repo (`VERCEL_TOKEN`, `VERCEL_ORG_ID`,
   `VERCEL_PROJECT_ID`). Il deploy via CLI evita il limite del piano Hobby sui repo
   privati di organizzazioni (da verificare in implementazione).

**Privacy — scelta consapevole:** il sito non ha protezione; è "privato" solo perché il
link non viene condiviso. Accettabile perché contiene solo inventario, pinout e note.
Non inserire mai dati sensibili nelle schede.

**Consultazione offline:**
- PC: `git pull` → aprire `catalogo/index.html`.
- Telefono: aprire l'URL Vercel → "Aggiungi a schermata Home" → funziona offline.

## 9. Gestione errori

- Scheda non valida → il generatore termina con codice ≠ 0 e messaggio
  `componenti/<id>/scheda.yaml: campo 'stato' non valido: 'ok' (ammessi: …)`.
- Immagine illeggibile → errore con il percorso del file.
- Cartella in `componenti/` senza `scheda.yaml` → errore.
- Nessun componente → il catalogo viene generato vuoto con un messaggio, non è un errore.

## 10. Test

pytest con schede di esempio in una cartella temporanea:
- scheda valida → generata correttamente, presente nel JSON e in `INVENTARIO.md`;
- campo obbligatorio mancante, enum non valido, `id` diverso dalla cartella,
  `id` duplicato → errore con messaggio chiaro;
- immagine pinout ridimensionata entro 1200 px;
- output deterministico (due esecuzioni → file identici).
Verifica manuale finale: apertura di `index.html` in Chromium (Playwright) per
controllare ricerca, filtri e dettaglio.
