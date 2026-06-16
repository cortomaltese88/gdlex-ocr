# Changelog

Tutte le modifiche rilevanti del progetto saranno documentate in questo file.

## [Unreleased]

## [0.1.6] - 2026-06-16

### Correzioni

- Corretto il launcher Debian per preservare gli argomenti CLI e rafforzata
  la gestione sicura delle opzioni.
- Aggiunti `gdlex-ocr --help`, `gdlex-ocr --version` e comportamento sicuro
  per `app.py --doctor`.
- Aggiunta gestione del timeout OCRmyPDF.

### Funzionalità

- Aggiunti campi SHA-256 degli output nel manifest del job.
- Aggiunte keyword al launcher desktop.

### Documentazione e metadati

- Migliorata la documentazione pubblica, incluso README inglese, note
  local-first/privacy, limiti OCR e troubleshooting.
- Aggiornati avvisi e crediti di terze parti.
- Chiarita nella finestra Informazioni la distinzione tra licenza del progetto
  e componenti di terze parti.
- Documentati i metadati aggiornati del repository GitHub.

## [0.1.5] - 2026-06-16

### Funzionalità

- Aggiunti backend OCR opzionali e diagnostica locale per OCRmyPDF, Tesseract
  e comandi esterni configurati dall'utente.
- Aggiunto il profilo **PDF già ricercabile**, che usa il layer testuale
  esistente e disattiva l'OCR interno Docling.
- Migliorato il profilo **Accurato testo**: genera un PDF ricercabile con
  OCRmyPDF/Tesseract e lo usa come sorgente Docling.
- Evitato l'uso indesiderato dell'OCR interno Docling/RapidOCR come fonte
  primaria nei PDF scannerizzati italiani quando si usa **Accurato testo**.
- Esteso il manifest con metadati dei backend OCR, struttura Markdown e
  `bookmarks.reason`.
- Migliorate generazione struttura Markdown/heading e strategia segnalibri.

### Interfaccia e strumenti

- Riorganizzata la sezione GUI **PDF e output** con schede **Base** e
  **Backend OCR**.
- Aggiunto helper per screenshot GUI con uso automatico della venv.
- Documentata la milestone futura per fascicoli penali Portale/TIAP.

### Test

- Estesi i test offline a 226 casi.

## [0.1.4] - 2026-06-15

### Funzionalità

- Aggiunta la modalità fascicolo opzionale, disattivata per default, che
  raccoglie ogni elaborazione in una sottocartella progressiva
  `<stem>_ocr_job[_N]`.
- Aggiunta in GUI la checkbox **Crea cartella fascicolo per ogni elaborazione**;
  apertura cartella, log, manifest e verifica output seguono la directory
  effettiva del job.
- Esteso additivamente il manifest schema version 1 con `output_layout`, che
  dichiara la modalità strutturata e la directory effettiva del job.
- Aggiunte utility pure per calcolare layout e nomi progressivi e una funzione
  separata per riservare senza sovrascrittura la directory del job.
- Migliorata la gestione di manifest e verifica output, inclusa la durata dei
  job terminati con errore o annullati.
- Aggiunto il workflow manuale per pubblicare una release nel repository APT
  GD LEX.

### Interfaccia

- Migliorati layout e contrasto delle checkbox nei temi Matrix e Chiaro.
- Separati i pulsanti di apertura e verifica output dai pulsanti
  **Avvia** e **Annulla**.

### Test

- Estesi i test offline per layout legacy e strutturato, nomi con spazi e punti
  multipli, directory progressive, worker, checkbox GUI, coerenza manifest e
  payload Debian.

## [0.1.3] - 2026-06-14

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
