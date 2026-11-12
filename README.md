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
