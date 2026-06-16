# GD LEX OCR

## Versione 0.1.5

GD LEX OCR è un'applicazione desktop locale in Python e PySide6 per
convertire fascicoli e documenti PDF in Markdown tramite Docling.

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

La pipeline predefinita resta libera e usa OCRmyPDF con Tesseract, installati
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

Un backend esterno deve essere già installato e regolarmente licenziato
dall'utente. GD LEX OCR non installa, aggira licenze o automatizza interfacce
grafiche. Se il backend non è disponibile, la conversione Markdown continua
dal PDF originale con un warning chiaro.

L'opzione **Usa il PDF ricercabile come sorgente Docling** crea prima il PDF
con il backend selezionato e poi lo usa per la conversione. È pensata
soprattutto per **Accurato testo**. Il PDF originale non viene modificato.

Tesseract viene rilevato come motore OCR, ma non è usato direttamente come
backend PDF multipagina: tale integrazione resta affidata a OCRmyPDF.

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

Il pacchetto `.deb` v0.1.5 installa sorgenti, asset, launcher e documentazione,
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

## Test

La suite smoke offline usa solo fixture sintetiche e non avvia Docling:

```bash
bash scripts/smoke.sh
```

Per rigenerare gli screenshot diagnostici della GUI senza OCR reale:

```bash
scripts/capture-gui-screenshots.py
```

Lo script si rilancia automaticamente con `.venv/bin/python` quando viene
avviato dall'interprete di sistema e la venv del progetto è presente.

## Profili di elaborazione

L'applicazione offre cinque profili selezionabili dalla GUI. Il default è **Bilanciato**.

| Profilo     | Blocco | Thread | Batch | Tabelle  | Immagini | Grafici | Struttura MD |
|-------------|-------:|-------:|------:|----------|----------|---------|--------------|
| Veloce      |  25 p. |     12 |     8 | fast     | no       | no      | no           |
| Bilanciato  |  15 p. |     10 |     6 | fast     | no       | no      | sì           |
| Accurato testo | 10 p. |      6 |     4 | accurate | no       | no      | sì           |
| PDF già ricercabile | 15 p. | 10 | 6 | accurate | no | no | sì |
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

I profili **Bilanciato** e **Accurato testo** applicano inoltre un
post-processing strutturale conservativo al Markdown finale. Righe isolate e
chiaramente riconoscibili come titoli (capitoli, sezioni, articoli e
numerazioni) vengono promosse a heading senza riscrivere il testo. Tabelle,
blocchi codice, citazioni, URL, email, hash e payload base64 sono esclusi.

**Accurato** attiva l'analisi di immagini e grafici e usa blocchi più piccoli per
maggiore robustezza. Adatto a documenti con tabelle complesse o contenuto misto.

## Elaborazione locale

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
