# Changelog

Tutte le modifiche rilevanti del progetto saranno documentate in questo file.

## [Unreleased]

## [0.4.0] - 2026-06-19

### Funzionalità

- Generazione `fascicolo_index.csv` con inventario documenti dall'analisi
  fascicolo PDP/TIAP.
- Generazione `fascicolo_unita.csv` con una riga per unità documentale
  PDP/TIAP (ID unità, PDF principale, dimensione, allegati, COMPLETE,
  conteggi, SHA-256).
- Aggiunta sezione "File più grandi" nel report Markdown con i primi 10 file
  per dimensione.
- Aggiunta sezione "Riepilogo operativo" nel report Markdown con dimensione
  totale, copertura indice, warning e conteggio unità.
- Aggiunti pulsanti GUI "Apri cartella output" e "Apri report Markdown"
  nella sezione Fascicolo.
- Log fascicolo con percorsi input/output e path di ciascun file generato.
- Conteggio match indice e unità documentali nel riepilogo GUI e nel dialogo
  di completamento.
- CLI analisi fascicolo produce anche `fascicolo_index.csv` e
  `fascicolo_unita.csv`.

### Test

- Test reale su fascicolo ministeriale: 237 file, 79 PDF, 79 indici,
  79 match, 79 unità, 0 warning, CSV unità 80 righe totali.
- Suite offline a 474 test sintetici.

### Privacy

- Output con path relativi, niente upload, niente lettura contenuto PDF.

## [0.3.3] - 2026-06-18

### Interfaccia

- Migliorata visibilità delle linguette principali della GUI (OCR documento /
  Fascicolo).
- Migliorata visibilità dei sub-tab OCR (Base / Backend OCR).
- Aggiunto stato selezionato/hover più marcato per le linguette nei temi
  Matrix e Chiaro.
- Aggiunte regole stylesheet `QTabWidget::pane`, `QTabBar::tab`,
  `QTabBar::tab:selected`, `QTabBar::tab:hover:!selected`.

### Test

- Aggiunti test strutturali e stylesheet per la GUI.

## [0.3.2] - 2026-06-18

### Funzionalità

- Riconoscimento unità documentali PDP/TIAP basate su directory numeriche.
- Classificazione `COMPLETE` come marker tecnico di unità documentale.
- Riconoscimento `ListaAllegati.html` come indice locale di unità documentale.
- Parsing e matching degli indici locali `ListaAllegati.html` con i documenti
  della relativa unità.
- Export JSON con sezione `units` e nuovi campi summary (`unit_count`,
  `technical_file_count`, `index_count`, `index_entry_count`,
  `index_match_count`).
- Export Markdown con sezione "Unità documentali PDP/TIAP".

### Correzioni

- Soppressione warning duplicati per file `COMPLETE` nelle unità documentali.
- Soppressione del falso positivo `multiple_casefile_indexes` per
  `ListaAllegati.html` presenti nelle directory numeriche locali.

### Test

- Test reale su fascicolo ministeriale: 79 unità, 79 indici, 79 match,
  0 warning.
- Suite offline a 450 test sintetici.

## [0.3.1] - 2026-06-18

### Funzionalità

- Aggiunta interfaccia grafica minima per Fascicoli PDP/TIAP.
- Nuova sezione GUI `Fascicolo` con selezione cartella fascicolo, selezione
  cartella output e pulsante `Analizza fascicolo`.
- L'analisi fascicolo è ora disponibile sia da CLI sia da GUI.
- Worker in background (`CasefileWorker`) per non bloccare l'interfaccia.
- Generazione di `fascicolo_index.json` e `fascicolo_index.md` dalla GUI.
- L'analisi non esegue OCR e non legge il contenuto dei PDF.
- Il path della cartella fascicolo non viene salvato in `QSettings`.

### Test

- Aggiunti test GUI dedicati per la sezione Fascicolo.
- Suite offline a 429 test sintetici.

## [0.3.0] - 2026-06-18

### Funzionalità

- Prima release della linea **Fascicoli PDP/TIAP**.
- Aggiunta analisi locale fascicolo con CLI
  `--analyze-casefile INPUT_DIR --output OUTPUT_DIR`.
- Generazione degli output privacy-safe `fascicolo_index.json` e
  `fascicolo_index.md`.
- Scan locale della cartella senza OCR e senza lettura del contenuto dei PDF:
  l'analisi lavora su nomi file, hash SHA-256 e indici leggeri.
- Calcolo hash SHA-256 dei documenti e warning per possibili duplicati.
- Classificazione euristica dei documenti in base al filename.
- Rilevamento indici fascicolo e parsing leggero TXT, CSV, HTML e XML.
- Matching euristico indice-documenti con segnalazioni non bloccanti per
  voci non abbinate o ambigue.

### Correzioni e hardening

- Export JSON e Markdown senza path assoluti e senza contenuto documentale.
- Hardening audit pre-release su filename vuoto, path traversal e parsing XML
  tramite `defusedxml`.
- Ampliata la suite offline a 418 test sintetici.

## [0.2.0] - 2026-06-18

### Funzionalità

- Prima release della linea **Sentenze / Impugnazioni**.
- Aggiunto parser offline per sentenze da Markdown, con estrazione euristica
  privacy-safe di autorità, parti, imputazioni, dispositivo, termini e alert
  utili alla verifica dell'impugnazione.
- Aggiunta CLI `--analyze-judgment INPUT.md --output OUTPUT` per generare una
  scheda locale da Markdown già prodotto, senza OCR e senza Docling.
- Aggiunta opzione `--prepend` per anteporre la scheda al Markdown di output
  mantenendo invariato il file di input.
- Aggiunta integrazione post-conversione PDF
  `--analyze-judgment-after-conversion`, che crea `sentenza_analysis.md`
  accanto al Markdown principale senza modificarlo.
- Esteso il manifest runtime con la sezione `judgment_analysis`, limitata a
  metadati tecnici e segnali privacy-safe.
- Aggiunta checkbox GUI **Analisi sentenza per impugnazione** per usare la
  stessa analisi locale dopo la conversione PDF.

### Correzioni e hardening

- Rafforzato il parser sentenze su autorità giudiziaria, prescrizione,
  patteggiamento, formule assolutorie e termini espressi in lettere.
- Ampliati i test sintetici offline per CLI, flusso PDF, GUI, manifest e casi
  limite del parser. La suite corrente copre 331 test.

## [0.1.9] - 2026-06-17

### Correzioni e hardening

- Corretta inizializzazione system tray icon per evitare doppia registrazione
  su KDE.
- Rimossa notifica KDE hide-to-tray che causava l'icona "i" indesiderata nella
  tray.
- Icone cartella tematizzate nei file dialog Qt per seguire il tema di sistema.
- Hardening subprocess OCRmyPDF: encoding UTF-8 esplicito con
  `errors="replace"`, terminazione del processo in caso di eccezione nel
  callback, separatore `--` prima dei path.
- Guard `isVisible()` sul controllo di `_cancelled` per evitare accessi a
  widget già distrutti.

### Strumenti e test

- Aggiunto stress test offline per subprocess OCRmyPDF: copertura di percorsi
  di errore e casi limite di encoding.
- Aggiunta copertura packaging e doctor per l'asset `folder-matrix.svg`.

## [0.1.8] - 2026-06-17

### Funzionalità

- Aggiunti controlli GUI per `Timeout OCRmyPDF` e `Jobs OCRmyPDF`, con
  persistenza locale tramite `QSettings`.
- Aggiunto streaming realtime di stdout/stderr OCRmyPDF nel log GUI,
  preservando timeout configurato e gestione degli errori.
- Aggiunto il profilo **Fascicolo legale**, conservativo per fascicoli e
  documenti lunghi.

### Strumenti e test

- Aggiornato il benchmark sintetico con esempio e copertura per
  **Fascicolo legale**.
- Abilitata la discovery standard dei test: `.venv/bin/python -m unittest`
  trova ora la suite.
- Aggiornati i test offline per opzioni GUI/OCRmyPDF, profili, benchmark e
  packaging.

## [0.1.7] - 2026-06-17

### Funzionalità

- Aggiunta persistenza locale delle preferenze GUI con `QSettings`, senza
  salvare percorsi input/PDF o output derivati automaticamente.
- Aggiunte opzioni CLI OCRmyPDF `--ocr-timeout SECONDS` e `--ocr-jobs N`.
- Aggiornato il manifest per registrare timeout e numero di job OCRmyPDF
  effettivamente usati.
- Aggiunto benchmark sintetico ripetibile e local-first con PDF generati sotto
  `tmp/benchmark-synthetic/`.

### Test

- Aggiunti e aggiornati test offline per preferenze GUI, opzioni OCRmyPDF,
  manifest runtime e benchmark sintetico.

### Documentazione

- Documentate le opzioni CLI OCRmyPDF e il benchmark sintetico locale.

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
