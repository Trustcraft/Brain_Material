# Archivio componenti elettronici

Inventario dei miei componenti (microcontrollori, sensori, moduli…) con pinout e note,
consultabile come catalogo offline da PC e telefono.

## Consultare

- **PC, offline:** `git pull`, poi apri `catalogo/index.html` con doppio clic.
- **Telefono:** apri il link Vercel → menu del browser → *Aggiungi a schermata Home*.
  Dopo la prima apertura funziona anche senza rete e si aggiorna da sola quando torni online.
- **Con Claude:** in un altro progetto chiedi di aggiungere questo repo alla sessione;
  Claude legge `INVENTARIO.md` e le schede (vedi `CLAUDE.md`).

## Aggiungere un componente

Il modo più semplice: descrivilo a Claude o mandagli le foto. A mano:

1. Crea `componenti/<id>/scheda.yaml` (id minuscolo con trattini, es. `esp32-wroom-32`):
   ```yaml
   id: esp32-wroom-32
   nome: ESP32 DevKit v1 (WROOM-32)
   categoria: microcontrollore
   stato: confermato
   quantita: 3
   interfacce: [WiFi, BLE, I2C, SPI, UART, ADC]
   note: "GPIO 6-11 riservati alla flash"
   ```
2. Metti l'immagine del pinout in `componenti/<id>/pinout.png` (o `.jpg`).
3. Rigenera e verifica:
   ```bash
   pip install -r strumenti/requirements.txt
   python strumenti/genera_catalogo.py
   ```

Componenti sconosciuti: metti le foto in `da_identificare/` e chiedi a Claude.

L'elenco completo dei campi è in `CLAUDE.md`.

## Pubblicazione su Vercel (da fare una volta)

Ad ogni push sul branch `main` la GitHub Action `.github/workflows/catalogo.yml` esegue i test,
rigenera il catalogo e lo pubblica. Per collegarla a Vercel:

1. Su vercel.com crea un account (piano Hobby gratuito) e un token in
   *Account Settings → Tokens*.
2. In locale, nella cartella del repo: `npx vercel link --cwd catalogo` → crea il progetto.
   Gli ID si trovano poi in `catalogo/.vercel/project.json` (`orgId`, `projectId`).
   La cartella `.vercel/` è ignorata da git: non va committata.
3. Nel repo GitHub, *Settings → Secrets and variables → Actions*, aggiungi
   `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
4. Su Vercel, nel progetto, *Settings → Deployment Protection*: lasciando la protezione
   standard, l'indirizzo di produzione `<progetto>.vercel.app` resta aperto a chi ha il link.

Senza i secret l'Action genera comunque il catalogo, ma non lo pubblica.
Il sito non ha password: non scrivere dati sensibili nelle schede.
