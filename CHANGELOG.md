# Changelog

Tutte le modifiche rilevanti del progetto saranno documentate in questo file.

## [Unreleased]

### Funzionalità

- Ogni elaborazione OCR/convert genera un file `manifest.json` nella cartella
  di output con schema version, identità app, ID job, tempi, input (path,
  dimensione, SHA-256, numero pagine), profilo, dettagli blocchi, output
  prodotti (Markdown, indice, PDF ricercabile), warning ed errori.
- Il manifest viene scritto all'avvio del job con `status: running` e
  aggiornato a fine job con `status: success`, `failed` o `cancelled`.
- Nuovo modulo `gdlex_ocr/manifest.py` con funzioni pure e testabili offline:
  `file_sha256`, `utc_now_iso`, `build_initial_manifest`, `write_manifest`,
  `safe_write_manifest`.
- Pulsante **Apri manifest** nella barra azioni della GUI, abilitato al
  termine dell'elaborazione (successo o errore) se `manifest.json` esiste.
- Verifica offline degli output dichiarati nel manifest, con report di file
  mancanti e warning non bloccanti per il PDF ricercabile opzionale.
- Pulsanti **Apri log** e **Verifica output** nella GUI.
- Nuova utility pura `build_output_layout` per centralizzare i nomi standard
  degli output senza cambiare il formato corrente.

## [0.1.2] - 2026-06-14

### Funzionalità

- Aggiunto il menu **File > Esci** con scorciatoia `Ctrl+Q`, collegato al
  flusso di chiusura condiviso con la system tray.
- L'apertura della cartella di output, del Markdown e del PDF ricercabile usa
  ora `QDesktopServices.openUrl`.
- Lo splash iniziale può essere disabilitato impostando
  `GDLEX_OCR_DISABLE_SPLASH`.

### Integrazione desktop

- Impostato `app.setDesktopFileName("gdlex-ocr")` per l'identità Linux.
- Splash e system tray usano icone raster dedicate.
- Rafforzata la gestione dell'icona della system tray per non creare il
  placeholder generico "i" quando l'icona applicativa non è disponibile.

### Test

- Aggiunti controlli offline di coerenza per identità e versione
  dell'applicazione.
- Estesi i test per splash, system tray, apertura degli output e contenuto
  effettivo del pacchetto Debian.

## [0.1.1] - 2026-06-14

### Correzioni

- Il wrapper Debian crea al primo avvio la venv utente in
  `~/.local/share/gdlex-ocr/venv` e installa automaticamente le dipendenze.
- Se gli import essenziali non sono disponibili, il wrapper prova ad aggiornare
  la venv senza richiedere istruzioni manuali o privilegi amministrativi.
- Il setup usa un lock per evitare avvii concorrenti e scrive il log in
  `~/.local/state/gdlex-ocr/setup.log`.
- In caso di errore viene mostrato un messaggio da terminale e, quando
  disponibile, un dialogo tramite KDialog o Zenity.

### Strumenti

- Aggiunti `gdlex-ocr --setup-venv` e `gdlex-ocr --doctor`.
- Aggiornati test e controlli del pacchetto Debian per escludere venv, cache,
  documenti e log dal payload.

## [0.1.0] - 2026-06-14

Prima release pubblica di GD LEX OCR.

### Funzionalità

- OCR ed elaborazione locale di documenti PDF con output Markdown.
- Profili di elaborazione Veloce, Bilanciato e Accurato.
- Rimozione delle immagini embedded e dei payload base64 dal Markdown.
- Cartella di output configurabile dall'interfaccia.
- Creazione opzionale di un PDF ricercabile tramite OCRmyPDF e Tesseract.
- Segnalibri PDF tecnici affidabili per intervalli di pagine.
- Indice atti Markdown sperimentale e auditabile, con pagina stimata
  corrispondente all'inizio del blocco Docling.
- Segnalibri PDF content-aware rimandati a una versione futura, in attesa di
  riferimenti di pagina intra-blocco affidabili.
- Temi Matrix e Chiaro con preferenza locale.
- Icona e launcher per KDE/Linux installabili per il singolo utente.
- Pacchetto Debian leggero senza dipendenze Python o modelli vendorizzati.
- Smoke test offline con fixture sintetiche, senza avvio di Docling.
