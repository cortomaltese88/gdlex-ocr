# GD LEX OCR

[English README](README.en.md)

## Versione 0.5.1

GD LEX OCR è un'applicazione desktop locale in Python e PySide6 per
convertire fascicoli e documenti PDF in Markdown tramite Docling. È pensata
per workflow legali in cui servono elaborazione locale, output verificabile e
tracciabilità tecnica del risultato, senza modificare il PDF originale. La
linea 0.5 completa il flusso locale **Fascicoli PDP/TIAP**: analisi e
unità documentali, merge plan revisionabile, PDF unico navigabile con
segnalibri e report, copia light opzionale e passaggio manuale alla scheda OCR.
La versione 0.5.1 consolida il flusso con correzioni, test dei casi limite e
warning più visibili, senza aggiungere nuove funzionalità.

## Prerequisiti minimi

- Python 3.12
- Un ambiente virtuale Python
- Le dipendenze elencate in `requirements.txt`

### Dipendenze Python

Le dipendenze Python dirette, installate nell'ambiente virtuale e usate per
l'applicazione e la conversione PDF → Markdown, sono:

| Pacchetto      | Versione  | Scopo                                    |
|----------------|-----------|------------------------------------------|
| docling        | 2.102.1   | OCR e conversione PDF → Markdown         |
| onnxruntime    | 1.26.0    | Inferenza modelli OCR (CPU)              |
| PySide6        | 6.11.1    | Interfaccia grafica                      |
| pypdf          | 6.13.2    | Suddivisione in blocchi PDF e segnalibri |

### Backend OCR locali opzionali

Per creare PDF ricercabili la pipeline usa OCRmyPDF con Tesseract, installati
separatamente dal pacchetto:

```bash
sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-ita
```

- `ocrmypdf` — aggiunge il layer di testo OCR al PDF originale
- `tesseract-ocr` — motore OCR usato da OCRmyPDF
- `tesseract-ocr-ita` — modello linguistico italiano per Tesseract

La GUI permette di scegliere:

- **Automatico**: usa OCRmyPDF quando disponibile;
- **OCRmyPDF**: selezione esplicita del backend libero;
- **Comando esterno**: template locale esplicito, eseguito senza shell, che
  deve contenere `{input}` e `{output}`; `{language}` è facoltativo.

Nelle impostazioni backend della GUI sono disponibili anche **Timeout
OCRmyPDF** e **Jobs OCRmyPDF**. I valori vengono conservati tramite
`QSettings` insieme alle altre preferenze locali, senza salvare percorsi di
input o output derivati automaticamente.

Un backend esterno deve essere già installato e regolarmente licenziato
dall'utente. GD LEX OCR non installa, aggira licenze o automatizza interfacce
grafiche. Se il backend non è disponibile, la conversione Markdown continua
dal PDF originale con un warning chiaro.

L'opzione **Usa il PDF ricercabile come sorgente Docling** crea prima il PDF
con il backend selezionato e poi lo usa per la conversione. È pensata
soprattutto per **Accurato testo**. Il PDF originale non viene modificato.

Tesseract viene rilevato come motore OCR, ma non è usato direttamente come
backend PDF multipagina: tale integrazione resta affidata a OCRmyPDF.

Docling può inoltre usare componenti OCR interni o transitivi, inclusi
RapidOCR e ONNX Runtime, secondo il profilo selezionato e la configurazione
upstream. Il profilo **Accurato testo** privilegia OCRmyPDF/Tesseract per
creare un PDF ricercabile locale e usarlo come sorgente della conversione.

#### Master PDF Editor e altri strumenti proprietari

Nel sistema di sviluppo `masterpdfeditor5` è stato rilevato, ma le opzioni
`--help` e `--version` non hanno esposto una CLI OCR batch utilizzabile.
Pertanto non viene automatizzato. Workflow manuale supportato:

1. aprire il PDF in Master PDF Editor;
2. eseguire l'OCR secondo la licenza del prodotto;
3. salvare un nuovo PDF ricercabile;
4. aprirlo in GD LEX OCR con il profilo **PDF già ricercabile**, che disattiva
   l'OCR Docling e mantiene il post-processing strutturale Markdown.

Lo stesso criterio vale per PDF Studio o altri prodotti: integrazione
automatica solo in presenza di una CLI locale, documentata e stabile.

Per verificare installazione, versioni e lingue Tesseract disponibili senza
installare né modificare nulla:

```bash
bash scripts/check-ocr-deps.sh
```

Lo script segnala anche l'eventuale assenza del modello italiano e mostra il
comando `apt` suggerito. Non esegue OCR e non legge PDF.

Per preparare l'ambiente:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Avvio

Attivare l'ambiente Python 3.12, quindi avviare l'applicazione:

```bash
source .venv/bin/activate
python app.py
```

Dal menu **Visualizza → Tema** è possibile scegliere tra il tema Matrix
predefinito e il tema Chiaro. La preferenza viene conservata localmente tramite
le impostazioni Qt dell'utente. Il menu **Aiuto → Informazioni** mostra credits,
componenti principali, licenza e nota sul trattamento locale dei documenti.

## Icona e menu KDE/Linux

L'icona applicativa Matrix / GD LEX è disponibile come SVG vettoriale e PNG
nelle dimensioni desktop comuni. Splash e system tray usano varianti raster
dedicate per una resa affidabile nell'ambiente desktop.

Per installare il launcher solo per l'utente corrente, senza `sudo`:

```bash
bash scripts/install-desktop.sh
```

Lo script installa icone e file `.desktop` sotto `~/.local/share`, crea il
wrapper di sviluppo `~/.local/bin/gdlex-ocr` e aggiorna la cache KDE quando
`kbuildsycoca6` è disponibile. Il wrapper avvia la `.venv` presente in questa
directory di progetto; `~/.local/bin` deve essere incluso in `PATH`.

Per rimuovere launcher, wrapper e icone installati localmente:

```bash
bash scripts/uninstall-desktop.sh
```

## Pacchetto Debian leggero

Il pacchetto `.deb` v0.5.1 installa sorgenti, asset, launcher e documentazione,
ma non incorpora `.venv`, dipendenze Python, modelli OCR o documenti elaborati.
Per costruirlo:

```bash
bash scripts/build-deb.sh
```

Al primo avvio il wrapper crea automaticamente la venv utente, aggiorna `pip`,
installa le dipendenze fissate nel pacchetto e avvia l'applicazione:

```bash
gdlex-ocr
```

La venv è conservata in `~/.local/share/gdlex-ocr/venv`; il log del setup è
`~/.local/state/gdlex-ocr/setup.log`. Non vengono usati `sudo` o script Debian
eseguiti come root. Per forzare un aggiornamento della venv:

```bash
gdlex-ocr --setup-venv
```

Per stampare la diagnostica senza avviare la GUI:

```bash
gdlex-ocr --doctor
```

Il comando restituisce `0` se tutti i controlli passano, `1` se mancano
componenti essenziali e `2` se mancano soltanto OCRmyPDF, Tesseract o la lingua
italiana. Questi strumenti di sistema restano opzionali.

Per controllare la versione installata:

```bash
gdlex-ocr --version
```

Opzioni OCR avanzate:

- `--ocr-timeout SECONDS`: imposta il timeout massimo per OCRmyPDF; default
  1800 secondi.
- `--ocr-jobs N`: passa a OCRmyPDF il numero di job paralleli; se omesso,
  viene lasciato il comportamento predefinito di OCRmyPDF.

Durante la creazione di PDF ricercabili con OCRmyPDF, stdout e stderr vengono
scritti in tempo reale nel log GUI e in `run.log`; timeout configurato e
gestione degli errori restano attivi.

Analisi sentenza dopo conversione PDF -> Markdown:

```bash
gdlex-ocr sentenza.pdf --output output/ --analyze-judgment-after-conversion
```

Questa opzione crea `sentenza_analysis.md` accanto al Markdown principale,
senza modificarlo. Lavora localmente sul Markdown appena generato e non calcola
termini definitivi di impugnazione. Quando è attivo il manifest del job,
aggiunge anche la sezione `judgment_analysis` con soli metadati tecnici e
segnali privacy-safe.

Analisi sentenza da Markdown gia' generato:

```bash
gdlex-ocr --analyze-judgment sentenza.md --output sentenza_analysis.md
gdlex-ocr --analyze-judgment sentenza.md --output sentenza_con_scheda.md --prepend
```

Questa modalita' lavora offline su un file Markdown esistente, non esegue OCR,
non invoca Docling e non modifica l'input. La scheda e' euristica: non calcola
termini definitivi di impugnazione e non sostituisce la verifica professionale.

La stessa analisi sentenza è disponibile anche dalla GUI tramite la checkbox
**Analisi sentenza per impugnazione**. Anche in questo caso l'elaborazione resta
locale, genera `sentenza_analysis.md`, non modifica il Markdown principale e
non sostituisce la verifica professionale.

Analisi fascicolo locale:

```bash
gdlex-ocr --analyze-casefile cartella_fascicolo/ --output output/
```

Analizza una cartella fascicolo e genera `fascicolo_index.json`,
`fascicolo_index.md`, `fascicolo_index.csv` e `fascicolo_unita.csv` nella
directory di output. L'analisi e' euristica e lavora sui nomi dei file, sugli
hash SHA-256 e sugli indici leggeri trovati nella cartella. Non esegue OCR,
non legge il contenuto dei PDF e non interpreta giuridicamente il fascicolo.
Rileva possibili duplicati, classifica i documenti per filename, individua e
interpreta in modo leggero indici TXT/CSV/HTML/XML e tenta il matching tra
voci di indice e documenti presenti. L'elaborazione e' interamente locale e
gli output sono privacy-safe: non includono path assoluti ne' contenuto
documentale.

Il report Markdown include la sezione "File più grandi" con i primi 10 file
per dimensione e il "Riepilogo operativo" con dimensione totale del
fascicolo, copertura indice, warning e conteggio unità documentali.

Il CSV `fascicolo_unita.csv` contiene una riga per ogni unità documentale
PDP/TIAP, con ID unità, PDF principale, dimensione, indice allegati,
marker COMPLETE, conteggi file e SHA-256.

L'analisi produce anche il merge plan automatico
`fascicolo_merge_plan.json`, `fascicolo_merge_plan.csv` e
`fascicolo_merge_plan.md`.

Dal merge plan generato e revisionabile si può creare il PDF unico:

```bash
gdlex-ocr --merge-casefile-pdf cartella_fascicolo/ --output output/
```

La CLI e la GUI possono stimare dimensione e pagine del PDF unico prima della
generazione:

```bash
gdlex-ocr --estimate-casefile-pdf cartella_fascicolo/ --output output/
```

La stima usa prima `fascicolo_merge_plan_revised.json`, se presente, e
altrimenti `fascicolo_merge_plan.json`, senza creare PDF o report finali. Il
flag `--write-estimate-reports` esporta la stima del PDF unico in JSON,
Markdown e CSV senza generare il PDF. Il merge stampa prima una stima basata
sulla somma delle dimensioni dei PDF
inclusi. La dimensione finale può differire per l'overhead del merge. Per creare
anche una copia locale alleggerita, senza sovrascrivere l'originale:

```bash
gdlex-ocr --merge-casefile-pdf cartella_fascicolo/ --output output/ --pdf-optimize balanced
```

I profili disponibili sono `none` (default), `balanced` (prudente e consigliato
per atti legali), `small` e `screen`. I profili diversi da `none` richiedono
Ghostscript (`gs`) installato localmente e generano
`fascicolo_unico_light.pdf`. Se Ghostscript non è disponibile il PDF originale
continua a essere utilizzabile, la copia ottimizzata non viene creata e CLI o
GUI mostrano un errore esplicito. Ghostscript è un componente locale opzionale:
il merge e l'ottimizzazione non caricano alcun documento online.

Il comando usa prima `fascicolo_merge_plan_revised.json`, se presente, e
altrimenti `fascicolo_merge_plan.json`. Genera `fascicolo_unico.pdf` con un
segnalibro per ogni documento incluso, oltre ai report privacy-safe
`fascicolo_unico_report.json` e `fascicolo_unico_report.md`. Il merge usa
`pypdf`, non esegue OCR e non estrae testo dai PDF.

La stessa analisi fascicolo è disponibile anche dalla GUI tramite la sezione
**Fascicolo**. Si selezionano la cartella del fascicolo e la cartella di output,
quindi si avvia l'analisi con il pulsante **Analizza fascicolo**. L'elaborazione
avviene in background senza bloccare l'interfaccia. Non viene eseguito OCR, non
viene letto il contenuto dei PDF e il path della cartella fascicolo non viene
salvato nelle impostazioni (`QSettings`). Al termine, i pulsanti **Apri
cartella output** e **Apri report Markdown** consentono di accedere
direttamente agli output prodotti. Il log mostra percorsi di input, output e
conteggi dettagliati.
Nella revisione del merge plan, **Genera PDF unico** avvia il merge in
background e **Apri PDF unico** apre il risultato con l'applicazione locale
predefinita. La tabella consente di includere o escludere gli atti, indicare il
motivo dell'esclusione, modificare i segnalibri e cambiare l'ordine con i
pulsanti, il trascinamento o `Alt+Up` / `Alt+Down`; un doppio click apre il PDF
sorgente locale senza modificare il piano. **Salva piano revisionato** crea le
varianti JSON, CSV e Markdown con suffisso `_revised`.
La validazione del piano PDF può essere esportata in JSON e Markdown per
conservare un report auditabile.

Il profilo PDF scelto nella GUI ha gli stessi effetti dell'opzione CLI
`--pdf-optimize`: **Apri PDF leggero** è disponibile solo quando Ghostscript ha
creato la copia alleggerita. **Invia PDF unico a OCR** seleziona la copia light
se esiste, altrimenti l'originale, e passa alla scheda OCR senza avviare
automaticamente alcuna elaborazione.

La stima della dimensione è approssimativa; Ghostscript non garantisce una
riduzione per ogni documento e può modificare la resa. Se il PDF light è più
grande o uguale all'originale, report JSON/Markdown, CLI e GUI mostrano un
warning senza eliminare nessuno dei due file. Prima dell'uso è quindi necessario
controllare visivamente il PDF unico, i segnalibri e l'eventuale copia
alleggerita rispetto ai documenti sorgente.

Se dopo l'installazione APT parte una vecchia copia di sviluppo, verificare il
`PATH`: un wrapper `~/.local/bin/gdlex-ocr` può avere precedenza su
`/usr/bin/gdlex-ocr`. In quel caso usare `/usr/bin/gdlex-ocr --doctor` oppure
rimuovere il wrapper locale con `bash scripts/uninstall-desktop.sh` dalla copia
di sviluppo.

## Installazione tramite repository APT GD LEX

Il repository APT pubblico GD LEX usa una chiave dedicata e la configurazione
`signed-by`. Per configurarlo su Debian/Ubuntu amd64:

```bash
curl -fsSL https://cortomaltese88.github.io/gdlex-apt-repo/keys/gdlex-archive-keyring.asc \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/gdlex-archive-keyring.gpg >/dev/null

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gdlex-archive-keyring.gpg] https://cortomaltese88.github.io/gdlex-apt-repo stable main" \
  | sudo tee /etc/apt/sources.list.d/gdlex.list

sudo apt update
sudo apt install gdlex-ocr
```

Gli strumenti client necessari per aggiungere il repository sono `curl`, `gpg`
e `sudo`. Il pacchetto `gdlex-ocr` ha architettura Debian `all`, mentre il
repository GD LEX pubblica attualmente l'indice per client `amd64`.
Non usare `trusted=yes`: la firma viene verificata tramite il keyring indicato.

## Output auditabile (manifest.json)

Al termine di ogni elaborazione OCR/convert, nella cartella di output viene
creato un file `manifest.json` con schema fisso, leggibile da editor o da
script. Il manifest include: identità app e versione, ID job UUID, timestamp
di avvio e fine, stato (`success`, `failed`, `cancelled`), dati dell'input
(path, dimensione, SHA-256, numero pagine), profilo usato, statistiche blocchi,
metadati del backend OCR, struttura Markdown applicata, motivazione della
strategia segnalibri, percorsi di tutti gli output prodotti, warning ed errori.
Quando viene richiesta l'analisi sentenza post-conversione, include anche
`judgment_analysis` con output `sentenza_analysis.md`, stato dell'analisi e
segnali tecnici privacy-safe, senza copiare il testo della sentenza.

La GUI consente di aprire direttamente `manifest.json` e `run.log`. Il pulsante
**Verifica output** controlla che i file dichiarati esistano e siano file
regolari, senza leggere il contenuto OCR o documentale.

La checkbox **Crea cartella fascicolo per ogni elaborazione**, disattivata per
default, organizza tutti gli output del job in una sottocartella dedicata:
`<stem>_ocr_job`, poi `<stem>_ocr_job_2`, `<stem>_ocr_job_3` e così via se il
nome è già occupato. Markdown, indice, PDF ricercabile, `run.log` e
`manifest.json` restano così separati dagli output dei job precedenti. Con la
checkbox disattivata il layout storico nella cartella di output non cambia.

Il manifest è un file runtime e non viene incluso nel pacchetto Debian.

Gli hash SHA-256 registrati nel manifest permettono di verificare quale input
è stato elaborato e quali output sono stati prodotti, senza includere nel
repository documenti, log o risultati OCR.

## Test

La suite smoke offline usa solo fixture sintetiche e non avvia Docling:

```bash
bash scripts/smoke.sh
```

Per eseguire un benchmark sintetico ripetibile e local-first, senza documenti
reali:

```bash
.venv/bin/python scripts/benchmark_synthetic.py
```

I PDF sintetici, i blocchi temporanei e i risultati runtime vengono generati
sotto `tmp/benchmark-synthetic/`. Vedere [BENCHMARK.md](BENCHMARK.md) per
opzioni e limiti. Il benchmark include anche un caso per il profilo
**Fascicolo legale**.

Per rigenerare gli screenshot diagnostici della GUI senza OCR reale:

```bash
scripts/capture-gui-screenshots.py
```

Lo script si rilancia automaticamente con `.venv/bin/python` quando viene
avviato dall'interprete di sistema e la venv del progetto è presente.

## Profili di elaborazione

L'applicazione offre sei profili selezionabili dalla GUI. Il default è **Bilanciato**.

| Profilo     | Blocco | Thread | Batch | Tabelle  | Immagini | Grafici | Struttura MD |
|-------------|-------:|-------:|------:|----------|----------|---------|--------------|
| Veloce      |  25 p. |     12 |     8 | fast     | no       | no      | no           |
| Bilanciato  |  15 p. |     10 |     6 | fast     | no       | no      | sì           |
| Accurato testo | 10 p. |      6 |     4 | accurate | no       | no      | sì           |
| PDF già ricercabile | 15 p. | 10 | 6 | accurate | no | no | sì |
| Fascicolo legale | 25 p. | 8 | 6 | accurate | no | no | sì |
| Accurato    |  10 p. |      6 |     4 | accurate | sì       | sì      | no           |

Il cambio profilo aggiorna automaticamente la dimensione blocco. La dimensione
può essere modificata manualmente dopo aver selezionato il profilo.

**Veloce** massimizza la velocità disabilitando l'analisi di immagini e grafici
e usando blocchi grandi. Adatto a documenti con prevalente contenuto testuale.

**Bilanciato** (default) bilancia velocità e qualità; ottimizzato per fascicoli
di uso comune.

**Accurato testo** usa tabelle accurate, batch e blocchi più piccoli, senza
analisi di immagini o grafici. È il profilo indicato quando la priorità è la
qualità del testo Markdown senza contenuti immagine incorporati.

**PDF già ricercabile** disattiva l'OCR Docling e usa il layer testuale già
presente, mantenendo tabelle accurate e struttura Markdown conservativa.

**Fascicolo legale** è pensato per PDF lunghi e già testuali: usa blocchi più
grandi, non forza l'OCR Docling, mantiene tabelle accurate e struttura Markdown
conservativa. Il PDF ricercabile resta opzionale dalle impostazioni dedicate.

I profili **Bilanciato**, **Accurato testo**, **PDF già ricercabile** e
**Fascicolo legale** applicano inoltre un
post-processing strutturale conservativo al Markdown finale. Righe isolate e
chiaramente riconoscibili come titoli (capitoli, sezioni, articoli e
numerazioni) vengono promosse a heading senza riscrivere il testo. Tabelle,
blocchi codice, citazioni, URL, email, hash e payload base64 sono esclusi.

**Accurato** attiva l'analisi di immagini e grafici e usa blocchi più piccoli per
maggiore robustezza. Adatto a documenti con tabelle complesse o contenuto misto.

## Elaborazione locale e privacy

L'OCR viene eseguito localmente: nessun documento viene caricato su servizi
cloud. Il PDF originale viene solo letto; i blocchi PDF e Markdown intermedi
sono conservati in una sottocartella `.gdlex_ocr_*` nella cartella di output.

Il Markdown prodotto è ottimizzato per l'uso con LLM e sistemi RAG. Le
immagini embedded e i relativi payload base64 non vengono inclusi: la loro
posizione nel documento viene conservata tramite un placeholder testuale
breve. Un controllo aggiuntivo rimuove eventuali payload residui prima
dell'unione dei blocchi.

Al primo avvio, Docling può scaricare modelli dai servizi upstream da cui
dipende. L'applicazione non effettua upload cloud dei documenti; download,
cache e gestione di dipendenze e modelli restano soggetti al comportamento e
alle configurazioni dei relativi progetti upstream.

## Limiti noti OCR

L'OCR è uno strumento di supporto e richiede verifica umana, soprattutto in
ambito legale. La qualità può variare in presenza di scansioni scure o storte,
documenti fotografati, timbri, annotazioni manuali, tabelle complesse, layout
multi-colonna, allegati con immagini, pagine ruotate o fascicoli molto grandi.

Il Markdown finale va sempre confrontato con il PDF originale prima di usarlo
per deposito, pareri, atti, ricerche probatorie o altri usi professionali.

## Licenze e componenti terzi

GD LEX OCR è © 2026 Studio GD LEX - Avv. Marco Gianese ed è rilasciato con
licenza MIT; il testo completo è nel file `LICENSE`.

L'applicazione usa dipendenze Python installate nell'ambiente virtuale
(`docling`, `onnxruntime`, `PySide6` e `pypdf`). OCRmyPDF, Tesseract, modelli
linguistici ed eventuali backend esterni sono strumenti di sistema opzionali,
richiamati solo su richiesta e non inclusi nel repository.

Licenze rilevate, modalità di distribuzione e note operative sono raccolte in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Le dipendenze transitive e
i modelli eventualmente scaricati da Docling conservano le rispettive licenze
upstream e devono essere verificati separatamente prima di distribuirli in un
pacchetto autonomo.

Il software è pensato per elaborare i documenti localmente. Il PDF originale
viene letto durante l'elaborazione e non viene modificato.
