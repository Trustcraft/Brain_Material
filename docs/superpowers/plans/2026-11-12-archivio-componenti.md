# Archivio componenti — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Archivio di componenti elettronici in YAML da cui si generano un catalogo HTML offline/PWA e un riassunto `INVENTARIO.md`, pubblicati automaticamente su Vercel.

**Architecture:** `componenti/<id>/scheda.yaml` è la fonte di verità. Un pacchetto Python in `strumenti/` valida le schede, ridimensiona le immagini, genera `catalogo/` (HTML con JSON incorporato + manifest + service worker) e `INVENTARIO.md`. Una GitHub Action esegue test, generazione, commit dell'output e deploy statico con la CLI Vercel.

**Tech Stack:** Python 3.11+, PyYAML, Pillow, pytest; HTML/CSS/JS vanilla senza librerie esterne; GitHub Actions; Vercel CLI.

**Spec:** `docs/superpowers/specs/2026-11-12-archivio-componenti-design.md`

## Global Constraints

- Lingua di interfaccia, messaggi di errore e documentazione: **italiano**.
- `id`: regex `^[a-z0-9]+(-[a-z0-9]+)*$`, uguale al nome della cartella, univoco.
- `categoria` ∈ `microcontrollore, sensore, modulo, attuatore, display, alimentazione, passivo, connettore, altro`.
- `stato` ∈ `da_identificare, ipotesi, confermato`.
- `quantita`: intero ≥ 0 (un bool o una stringa come `"3"` è un errore).
- Immagini: lato massimo **1200 px**, output **WebP**; file riconosciuti `pinout.*` e `foto.*` con estensione `png|jpg|jpeg|webp`, senza distinzione maiuscole/minuscole.
- Formato errore: `componenti/<id>/scheda.yaml: <descrizione>`; uscita con codice 1.
- Nessuna risorsa esterna nella pagina (niente CDN, font o script remoti).
- Output deterministico: due esecuzioni sullo stesso input producono byte identici.
- Nessuna protezione sul sito (scelta consapevole dell'utente).

## Review Focus

1. **Note contenenti `</script>` o `<!--`** → il JSON incorporato non deve chiudere il tag; serializzare con `<`, `>`, `&` escapati come `<`, `>`, `&` (test nel Task 4).
2. **Due file pinout nella stessa cartella** (`pinout.png` e `pinout.jpg`) → errore esplicito, non scelta arbitraria (test nel Task 2).
3. **YAML malformato o vuoto** (tab, file vuoto, non un dizionario) → errore con percorso, non traceback (test nel Task 1).
4. **Apertura da `file://`** → la registrazione del service worker è protetta da `location.protocol.startsWith('http')`, così la pagina funziona senza errori (verifica nel Task 6).
5. **Ricerca con accenti e maiuscole** ("modulo relè" vs "Rele") → la ricerca normalizza con `NFD` + rimozione dei diacritici + minuscole (verifica nel Task 6).

---

## File Structure

| File | Responsabilità |
|---|---|
| `strumenti/archivio/__init__.py` | vuoto |
| `strumenti/archivio/modello.py` | dataclass `Componente`, costanti enum, `ErroreScheda` |
| `strumenti/archivio/caricamento.py` | lettura e validazione di `componenti/` |
| `strumenti/archivio/immagini.py` | individuazione e ridimensionamento immagini |
| `strumenti/archivio/inventario.py` | rendering `INVENTARIO.md` |
| `strumenti/archivio/catalogo.py` | rendering `index.html`, manifest, `sw.js` |
| `strumenti/archivio/template.html` | pagina (CSS + JS inline) con segnaposto `/*__DATI__*/` |
| `strumenti/genera_catalogo.py` | CLI: orchestrazione, gestione errori, codice di uscita |
| `strumenti/requirements.txt` | `PyYAML`, `Pillow`, `pytest` (versioni fissate) |
| `strumenti/tests/` | test pytest + `conftest.py` con fixture `crea_scheda` |
| `CLAUDE.md`, `README.md` | istruzioni per Claude e per l'utente |
| `.github/workflows/catalogo.yml` | test → genera → commit → deploy |

---

### Task 1: Modello e validazione delle schede

**Files:**
- Create: `strumenti/archivio/__init__.py`, `strumenti/archivio/modello.py`, `strumenti/archivio/caricamento.py`, `strumenti/requirements.txt`, `strumenti/tests/conftest.py`, `strumenti/tests/test_caricamento.py`, `pytest.ini` (`pythonpath = strumenti`, `testpaths = strumenti/tests`), `.gitignore` (`__pycache__/`, `.pytest_cache/`, `.vercel/`), `componenti/.gitkeep`, `da_identificare/.gitkeep`

**Interfaces:**
- Produces:
  - `class ErroreScheda(Exception)` — `str(e)` è il messaggio nel formato globale.
  - `@dataclass(frozen=True) class Componente`: `id: str, nome: str, categoria: str, stato: str, quantita: int, produttore: str|None, modello: str|None, posizione: str|None, tensione: str|None, interfacce: tuple[str,...], tag: tuple[str,...], datasheet_url: str|None, note: str|None, progetti: tuple[str,...], cartella: Path`
  - `CATEGORIE: tuple[str,...]`, `STATI: tuple[str,...]` (ordine come nei Global Constraints)
  - `carica_componenti(radice: Path) -> list[Componente]` — legge `radice/"componenti"`, ignora file che non sono cartelle e i nomi che iniziano con `.`, restituisce la lista ordinata per `id`.
  - Fixture `crea_scheda(tmp_path)` → funzione `crea(id: str, **campi) -> Path` che scrive `tmp_path/componenti/<id>/scheda.yaml` con i default `nome="Test", categoria="sensore", stato="confermato", quantita=1, id=<id>`; `campi[k]=None` rimuove la chiave. Restituisce `tmp_path`.

- [ ] **Step 1: Scrivere i test che falliscono** in `test_caricamento.py`:
  - `test_scheda_valida`: un componente con `interfacce=["I2C"]` → `len==1`, `c.interfacce == ("I2C",)`, `c.produttore is None`.
  - `test_ordinamento_per_id`: `b-x`, `a-y` → ids `["a-y", "b-x"]`.
  - `test_cartella_vuota_restituisce_lista_vuota` (anche se `componenti/` non esiste).
  - Parametrizzato `test_errori` con `pytest.raises(ErroreScheda, match=...)`:
    - campo `nome=None` → `"campo obbligatorio mancante: 'nome'"`
    - `stato="ok"` → `"campo 'stato' non valido: 'ok'"`
    - `categoria="boh"` → `"campo 'categoria' non valido: 'boh'"`
    - `quantita="3"` e `quantita=-1` e `quantita=True` → `"'quantita' deve essere un intero >= 0"`
    - `id="altro"` in cartella `x` → `"'id' diverso dal nome della cartella"`
    - id cartella `"Bad_Id"` → `"'id' non valido"`
    - `interfacce="I2C"` (non lista) → `"'interfacce' deve essere una lista"`
    - campo sconosciuto `colore="rosso"` → `"campo sconosciuto: 'colore'"`
  - `test_yaml_malformato`: contenuto `"nome: [\n"` → match `"componenti/x/scheda.yaml: YAML non valido"`.
  - `test_yaml_vuoto_o_non_dizionario`: contenuto `""` e `"- a\n"` → match `"deve contenere un dizionario"`.
  - `test_cartella_senza_scheda`: `componenti/x/` vuota → match `"componenti/x/scheda.yaml: file mancante"`.
  - Il messaggio inizia sempre con il percorso relativo alla radice, scritto con `/`.

- [ ] **Step 2: Eseguire** `pytest strumenti/tests/test_caricamento.py -v` → FAIL (`ModuleNotFoundError: archivio`).

- [ ] **Step 3: Implementare** `modello.py` e `caricamento.py`. Usare `yaml.safe_load` (mai `yaml.load`: carica solo tipi semplici, quindi niente esecuzione di oggetti arbitrari). Liste convertite in tuple, così `Componente` è immutabile. Il controllo dei duplicati è garantito dall'uguaglianza `id` == cartella, perché due cartelle non possono avere lo stesso nome; non serve un controllo separato.

- [ ] **Step 4: Eseguire** `pytest strumenti/tests/test_caricamento.py -v` → PASS.

- [ ] **Step 5: Commit** `feat: modello e validazione delle schede componente`

---

### Task 2: Immagini

**Files:**
- Create: `strumenti/archivio/immagini.py`, `strumenti/tests/test_immagini.py`

**Interfaces:**
- Consumes: `Componente`, `ErroreScheda` (Task 1).
- Produces:
  - `LATO_MASSIMO = 1200`
  - `trova_immagine(cartella: Path, nome: str, radice: Path) -> Path | None` — `nome` è `"pinout"` o `"foto"`; più di un candidato → `ErroreScheda("<rel>/: più file '<nome>' trovati: a, b")`.
  - `esporta_immagine(sorgente: Path, destinazione: Path, radice: Path) -> None` — WebP, `quality=80`, `method=6`, lato massimo `LATO_MASSIMO` mantenendo le proporzioni, senza ingrandire immagini più piccole; applica `ImageOps.exif_transpose` (le foto da telefono hanno la rotazione nei metadati EXIF: senza, verrebbero mostrate storte); immagine illeggibile → `ErroreScheda("<rel percorso>: immagine non leggibile")`.

- [ ] **Step 1: Test che falliscono** (creare le immagini con Pillow in `tmp_path`):
  - `test_trova_estensione_maiuscola`: `pinout.JPG` → trovato.
  - `test_nessuna_immagine` → `None`.
  - `test_due_pinout_errore`: `pinout.png` + `pinout.jpg` → match `"più file 'pinout' trovati"`.
  - `test_ridimensiona_lato_lungo`: 3000×1500 → output `(1200, 600)`, formato `WEBP`.
  - `test_non_ingrandisce`: 400×300 → `(400, 300)`.
  - `test_immagine_corrotta`: byte casuali in `pinout.png` → match `"immagine non leggibile"`.
  - `test_esportazione_deterministica`: due esportazioni → byte identici.
- [ ] **Step 2:** `pytest strumenti/tests/test_immagini.py -v` → FAIL.
- [ ] **Step 3:** Implementare. Salvare senza metadati (niente `exif=`), così l'output è deterministico e la posizione GPS della foto non finisce online.
- [ ] **Step 4:** `pytest strumenti/tests/test_immagini.py -v` → PASS.
- [ ] **Step 5: Commit** `feat: individuazione e ridimensionamento immagini`

---

### Task 3: INVENTARIO.md

**Files:**
- Create: `strumenti/archivio/inventario.py`, `strumenti/tests/test_inventario.py`

**Interfaces:**
- Consumes: `Componente`, `CATEGORIE`.
- Produces: `genera_inventario(componenti: list[Componente]) -> str`

Formato: intestazione `# Inventario componenti`, riga `Totale: N componenti (X confermati, Y ipotesi, Z da identificare)`, poi una sezione `## <categoria>` per ogni categoria non vuota, nell'ordine di `CATEGORIE`, con la tabella `| id | nome | q.tà | interfacce | tensione | stato |`. Interfacce unite con `, `; valori mancanti `—`; il carattere `|` nei valori viene escapato come `\|`.

- [ ] **Step 1: Test:** `test_totali`, `test_ordine_categorie` (sensore prima di display, categorie vuote assenti), `test_pipe_escapata`, `test_lista_vuota` (contiene `Totale: 0 componenti`).
- [ ] **Step 2:** FAIL. **Step 3:** implementare. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat: generazione INVENTARIO.md`

---

### Task 4: Catalogo HTML e PWA

**Files:**
- Create: `strumenti/archivio/catalogo.py`, `strumenti/archivio/template.html`, `strumenti/tests/test_catalogo.py`

**Interfaces:**
- Consumes: `Componente`.
- Produces:
  - `dati_componente(c: Componente, pinout: str|None, foto: str|None) -> dict` — tutti i campi del dataclass tranne `cartella`, più `pinout`/`foto` come percorsi relativi `img/<id>-pinout.webp`.
  - `json_sicuro(obj) -> str` — `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` con `<`, `>`, `&` sostituiti da `<`, `>`, `&`.
  - `genera_html(dati: list[dict]) -> str` — sostituisce `/*__DATI__*/` nel template con `json_sicuro(dati)`.
  - `genera_sw(file_da_cachare: list[str], versione: str) -> str`
  - `genera_manifest() -> str` — `name: "Archivio componenti"`, `short_name: "Componenti"`, `start_url: "./"`, `display: "standalone"`, icona SVG inline generata come file `icona.svg`.

Template (`template.html`): `<script id="dati" type="application/json">/*__DATI__*/</script>`. JS: ricerca su nome, modello, produttore, tag, note, interfacce normalizzati (NFD, rimozione dei diacritici `\p{Diacritic}`, minuscole); filtri `<select>` per categoria, stato e interfaccia (valori ricavati dai dati); lista a schede con miniatura del pinout; dettaglio in `<dialog>` nell'ordine pinout → note → dati tecnici → quantità/posizione → foto → `datasheet_url` + "Cerca datasheet aggiornato" (`https://duckduckgo.com/?q=` + `encodeURIComponent(produttore + " " + (modello||nome) + " datasheet pdf")`); badge per `ipotesi` (giallo) e `da_identificare` (rosso); colori come variabili CSS su `:root` con `prefers-color-scheme: dark`; nessuno scroll orizzontale su schermi stretti; con zero componenti mostra "Nessun componente in archivio", con zero risultati di ricerca "Nessun risultato". Tutti i testi delle schede inseriti con `textContent` e mai con `innerHTML`, così il contenuto delle note non può iniettare HTML. Registrazione del service worker solo se `location.protocol.startsWith('http')`.

`sw.js`: `CACHE = "archivio-<versione>"`; `install` → `cache.addAll(file)`; `activate` → elimina le cache con nome diverso; `fetch` → prima la rete, con salvataggio in cache, e la cache se la rete manca. Prima la rete perché così, quando sei online, vedi sempre l'ultima versione; offline resta l'ultima copia salvata.

- [ ] **Step 1: Test:**
  - `test_json_sicuro_non_chiude_script`: note `"</script><!--"` → output senza `</` né `<!--`, e `json.loads` dell'output restituisce il valore originale.
  - `test_html_contiene_dati`: un componente → `genera_html` contiene `"id":"dht22"` e non contiene più `/*__DATI__*/`.
  - `test_html_nessuna_risorsa_esterna`: nessuna occorrenza di `src="http` o `href="http` nel template, ammesso solo il link DuckDuckGo costruito nel JS.
  - `test_sw_versione_e_file`: `genera_sw(["index.html","img/a.webp"], "abc123")` contiene `archivio-abc123` e `img/a.webp`.
  - `test_manifest_valido`: `json.loads` ok, `display == "standalone"`.
- [ ] **Step 2:** FAIL. **Step 3:** implementare. **Step 4:** PASS.
- [ ] **Step 5: Commit** `feat: catalogo HTML offline e PWA`

---

### Task 5: CLI di generazione, documentazione e componente di esempio

**Files:**
- Create: `strumenti/genera_catalogo.py`, `strumenti/tests/test_cli.py`, `CLAUDE.md`, `README.md`

**Interfaces:**
- Consumes: tutto quanto sopra.
- Produces: `main(argv: list[str] | None = None) -> int` con opzione `--radice` (default: la cartella superiore a `strumenti/`). Esegue `carica_componenti` → svuota e ricrea `catalogo/` → esporta le immagini in `catalogo/img/<id>-pinout.webp` e `<id>-foto.webp` → scrive `index.html`, `manifest.webmanifest`, `icona.svg`, `sw.js` (versione = primi 12 caratteri dello SHA-256 di tutti i file generati, in ordine di percorso) → scrive `INVENTARIO.md` nella radice. In caso di `ErroreScheda` stampa il messaggio su stderr e restituisce 1; altrimenti stampa `Catalogo generato: N componenti` e restituisce 0. Tutti i file sono scritti in UTF-8 con `\n`.

- [ ] **Step 1: Test:**
  - `test_genera_tutto`: un componente con pinout → esistono `catalogo/index.html`, `catalogo/img/<id>-pinout.webp`, `catalogo/sw.js`, `INVENTARIO.md`; codice 0.
  - `test_errore_codice_1`: scheda non valida → 1, stderr contiene `scheda.yaml:`, e un `catalogo/` già esistente resta intatto. La validazione avviene prima di cancellare qualsiasi cosa: un errore non deve lasciarti senza catalogo offline.
  - `test_deterministico`: due esecuzioni → hash identici di tutti i file.
  - `test_rimuove_immagini_orfane`: un'immagine in `catalogo/img/` di un componente eliminato sparisce.
- [ ] **Step 2:** FAIL. **Step 3:** implementare `main`.
- [ ] **Step 4:** `pytest -v` → tutti PASS.
- [ ] **Step 5:** Scrivere `CLAUDE.md`: struttura, tabella dei campi (copiata dalla spec §3), workflow di identificazione (spec §6), regole (non modificare `catalogo/` né `INVENTARIO.md` a mano; dopo ogni modifica eseguire `python strumenti/genera_catalogo.py`; in `note` delle `ipotesi` indicare le prove e la confidenza; consultazione da altri progetti: leggere prima `INVENTARIO.md`). Scrivere `README.md` per l'utente: come consultare (PC/telefono), come aggiungere un componente, come installare le dipendenze.
- [ ] **Step 6:** Eseguire `pip install -r strumenti/requirements.txt && python strumenti/genera_catalogo.py` sul repo reale (catalogo vuoto) → `Catalogo generato: 0 componenti`.
- [ ] **Step 7: Commit** `feat: CLI generazione catalogo e documentazione`

---

### Task 6: Verifica nel browser

**Files:**
- Create: `strumenti/tests/test_browser.py` (marcato `@pytest.mark.browser`; saltato con `pytest.importorskip("playwright")`, così la CI non dipende da un browser)
- Modify: `pytest.ini` (registrare il marker `browser`)

- [ ] **Step 1: Test** con Playwright su un catalogo generato in `tmp_path` con 3 componenti (uno `ipotesi`, uno con nota `"Relè"`), aperto con `file://`:
  - nessun errore in console (verifica il punto 4 della Review Focus);
  - ricerca `"rele"` → 1 scheda visibile (punto 5);
  - filtro stato `ipotesi` → 1 scheda, con badge visibile;
  - clic su una scheda → `<dialog>` aperto, il primo elemento del contenuto è l'immagine del pinout;
  - viewport 375×800 → `document.documentElement.scrollWidth <= 375`.
- [ ] **Step 2:** `pytest -m browser -v` → FAIL, poi correggere il template, poi PASS.
- [ ] **Step 3:** Servire `catalogo/` con `python -m http.server`, verificare che il service worker si registri e che, dopo `context.set_offline(True)` e ricarica, la pagina si apra.
- [ ] **Step 4: Commit** `test: verifica catalogo nel browser`

---

### Task 7: GitHub Action e deploy Vercel

**Files:**
- Create: `.github/workflows/catalogo.yml`, `catalogo/vercel.json` (solo header: `Cache-Control: no-cache` per `sw.js` e `index.html`, così il telefono riceve subito le versioni nuove)

- [ ] **Step 1:** Verificare sulla documentazione aggiornata di Vercel (strumento `search_vercel_documentation`): (a) se il piano Hobby può collegarsi a un repo privato di un'organizzazione GitHub; (b) che il deploy via CLI con `VERCEL_TOKEN` funzioni sul piano Hobby. Riportare i risultati all'utente prima di procedere.
- [ ] **Step 2:** Scrivere il workflow: trigger `push` sul branch principale (ignorando i commit fatti dalla Action stessa con `if: github.actor != 'github-actions[bot]'`, altrimenti ogni commit della Action ne lancerebbe un'altra all'infinito) e `workflow_dispatch`. Job: `actions/checkout@v4` → `actions/setup-python@v5` (3.12) → `pip install -r strumenti/requirements.txt` → `pytest -m "not browser"` → `python strumenti/genera_catalogo.py` → se `git status --porcelain catalogo INVENTARIO.md` non è vuoto, commit `chore: rigenera catalogo` e push → `npx vercel@<versione fissata> deploy catalogo --prod --yes --token "$VERCEL_TOKEN"` con `VERCEL_ORG_ID` e `VERCEL_PROJECT_ID` dai secret. `permissions: contents: write`.
- [ ] **Step 3:** Validare la sintassi YAML del workflow (`python -c "import yaml; yaml.safe_load(open('.github/workflows/catalogo.yml'))"`).
- [ ] **Step 4: Commit** `ci: genera e pubblica il catalogo su Vercel`
- [ ] **Step 5:** Istruire l'utente (in chat e nel README) su cosa fare: creare il progetto Vercel, generare il token, aggiungere i tre secret nel repo GitHub. Il primo deploy si verifica insieme, dopo il merge sul branch principale.

---

## Fuori da questo piano

Il primo caricamento dei componenti reali (descrizioni e foto da identificare) è lavoro sui dati, non codice: si fa dopo il Task 5, in conversazione.
