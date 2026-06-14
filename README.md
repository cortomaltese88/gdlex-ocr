# GD LEX OCR

## Versione 0.1.1

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

### Strumenti di sistema opzionali (PDF ricercabile)

Per la funzione **PDF ricercabile OCR** sono necessari strumenti di sistema
non inclusi in `requirements.txt`:

```bash
sudo apt install ocrmypdf tesseract-ocr tesseract-ocr-ita
```

- `ocrmypdf` — aggiunge il layer di testo OCR al PDF originale
- `tesseract-ocr` — motore OCR usato da OCRmyPDF
- `tesseract-ocr-ita` — modello linguistico italiano per Tesseract

La funzione è opzionale: se non installata, la generazione Markdown Docling
rimane pienamente funzionante. Il PDF ricercabile viene creato dall'originale
senza modificarlo; l'output è `<nome>_searchable.pdf` nella cartella di output.
Attualmente il PDF riceve esclusivamente segnalibri tecnici affidabili per
intervalli di pagine, ad esempio `Fallback tecnico - Pagine 1–15`. Accanto al
Markdown viene creato anche `<stem>_index.md`: è un indice atti sperimentale e
auditabile, nel quale la pagina indicata è soltanto la stima dell'inizio del
blocco Docling. I segnalibri PDF content-aware sono rimandati a una versione
futura, quando saranno disponibili riferimenti di pagina intra-blocco
affidabili.

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
nelle dimensioni desktop comuni. L'applicazione usa direttamente l'SVG anche
quando viene avviata dalla directory di sviluppo.

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

Il pacchetto `.deb` v0.1.1 installa sorgenti, asset, launcher e documentazione,
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

## Test

La suite smoke offline usa solo fixture sintetiche e non avvia Docling:

```bash
bash scripts/smoke.sh
```

## Profili di elaborazione

L'applicazione offre tre profili selezionabili dalla GUI. Il default è **Bilanciato**.

| Profilo     | Blocco | Thread | Batch | Tabelle  | Immagini | Grafici |
|-------------|-------:|-------:|------:|----------|----------|---------|
| Veloce      |  25 p. |     12 |     8 | fast     | no       | no      |
| Bilanciato  |  15 p. |     10 |     6 | fast     | no       | no      |
| Accurato    |  10 p. |      6 |     4 | accurate | sì       | sì      |

Il cambio profilo aggiorna automaticamente la dimensione blocco. La dimensione
può essere modificata manualmente dopo aver selezionato il profilo.

**Veloce** massimizza la velocità disabilitando l'analisi di immagini e grafici
e usando blocchi grandi. Adatto a documenti con prevalente contenuto testuale.

**Bilanciato** (default) bilancia velocità e qualità; ottimizzato per fascicoli
di uso comune.

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
(`docling`, `onnxruntime`, `PySide6` e `pypdf`). OCRmyPDF, Tesseract e il
modello linguistico italiano sono invece strumenti di sistema opzionali,
richiamati solo quando viene richiesta la creazione del PDF ricercabile e non
sono inclusi nel repository.

Licenze rilevate, modalità di distribuzione e note operative sono raccolte in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). Le dipendenze transitive e
i modelli eventualmente scaricati da Docling conservano le rispettive licenze
upstream e devono essere verificati separatamente prima di distribuirli in un
pacchetto autonomo.

Il software è pensato per elaborare i documenti localmente. Il PDF originale
viene letto durante l'elaborazione e non viene modificato.
