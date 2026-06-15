# Roadmap - GD LEX OCR

Roadmap tecnica indicativa, soggetta a revisione dopo test su documenti
eterogenei. L'elaborazione resta locale: il PDF originale viene letto ma non
viene mai modificato.

## v0.1.0 - Prototipo

- Prototipo funzionante.
- GUI PySide6.
- Elaborazione Docling a blocchi.
- Progress bar ed ETA.
- Tema Matrix / GD LEX.
- Splash screen generato localmente.

## v0.2.0 - Performance e UX

- Profili di elaborazione: Veloce, Bilanciato (default), Accurato.
- Parametri Docling configurabili: num_threads, page_batch_size, table_mode,
  enrich_picture, enrich_chart.
- onnxruntime come runtime OCR locale (CPU).
- Selettore profilo in GUI con riepilogo parametri.
- Pulsanti "Apri cartella output", "Apri Markdown" e "Apri PDF OCR"
  post-elaborazione.
- Report finale: durata totale, pagine/minuto, blocco più lento.
- PDF ricercabile opzionale via OCRmyPDF (richiede installazione di sistema).
- Segnalibri PDF a blocchi pagina (standard PDF outline, compatibile con
  Okular, Evince, Adobe Reader, Firefox/Chrome).
- Selettore lingua OCR per OCRmyPDF (italiano, inglese, misto, altre lingue).
- Icona applicativa Matrix / GD LEX e integrazione menu KDE/Linux per utente.
- Obiettivo: battere baseline 27m43s / 5,7 pag/min su 158 pagine.

## v0.3.0 - Qualità dell'output

- Miglioramento e verifica della qualità dell'output.
- Indice del fascicolo.
- Generazione di `fascicolo_per_chatgpt.md`.
- Anteprima Markdown locale.
- Controlli OCR e diagnostica più accurati.
- Profilo Solo Testo: rilevamento PDF testuale e skip OCR.

## v0.4.0 - Profili e formati

- Profili operativi: fascicolo penale, fascicolo civile, sentenza, APE e
  documenti misti.
- Esportazione TXT, Markdown e JSON.
- Report delle pagine problematiche o con qualità OCR incerta.

## v0.5.0 - Distribuzione desktop

- Packaging `.deb`.
- Eventuale affinamento grafico dell'icona in base alle prove d'uso.
- Configurazione utente persistente.

## v1.0.0 - Uso interno stabile

- Tool GD LEX OCR stabile per uso interno.
- Pipeline locale affidabile e verificabile.
- Nessun upload cloud.
- Output strutturato per l'uso con ChatGPT, Claude o sistemi RAG locali.

## v1.x.0 - Ricostruzione fascicoli penali da Portale Deposito Atti Penali / TIAP

> **Milestone futura.** Nessuna data di rilascio fissata. Dipende dalla
> disponibilità di fixture di test sintetiche e dal completamento della
> pipeline base (v1.0.0).

### Obiettivo

Modalità dedicata all'importazione e ricostruzione di fascicoli penali
scaricati dal Portale Deposito Atti Penali (PDAP) o da TIAP. Gli applicativi
ufficiali della Procura/TIAP sono spesso legati a Windows e non adatti
all'uso quotidiano; questa modalità deve essere completamente indipendente da
essi, operando esclusivamente sui file esportati/scaricati.

La funzione lavora **interamente in locale** e non invia nulla online.

### Input

- Una cartella fascicolo così come scaricata dal portale (struttura piatta o
  ad albero).
- Spesso contiene molti PDF con nomi numerici o poco evocativi.
- Spesso è presente un file indice fascicolo in HTML (`index.html` o simile).

### Rilevamento e analisi automatica

- Rileva automaticamente il file indice HTML nella cartella.
- Analizza l'indice HTML per estrarre:
  - ordine / affoliazione;
  - descrizione dell'atto;
  - data dell'atto (se presente);
  - collegamento o riferimento al file PDF corrispondente.
- Scopre ricorsivamente tutti i PDF presenti nella cartella.
- Associa le voci dell'indice ai PDF trovati.

### Diagnostica e warning

Segnala in anteprima e nel manifest:

- voci indice senza PDF corrispondente;
- PDF non presenti nell'indice (file "orfani");
- duplicati (stesso contenuto o stesso nome in percorsi diversi);
- file corrotti o non apribili;
- date mancanti nell'indice;
- nomi file incoerenti rispetto alle aspettative del formato portale.

### Preview e ordinamento

- Mostra una preview tabellare del fascicolo ricostruito prima della
  generazione dell'output.
- Consente all'utente di scegliere l'ordinamento da menu a tendina:
  - ordine indice / affoliazione (default);
  - data atto;
  - data file (mtime);
  - nome file;
  - ordine manuale (drag-and-drop o editing testo, da valutare).

### Elaborazione

- Unisce i PDF ordinati in un unico fascicolo.
- Genera segnalibri PDF derivati dalle descrizioni dell'indice HTML (riusa
  la pipeline `bookmarks` esistente).
- Esegue **OCR selettivo**: solo i PDF scansionati o non ricercabili vengono
  processati; i PDF già nativi/testuali vengono preservati intatti.
- Genera Markdown strutturato del fascicolo.
- Genera indice Markdown (`fascicolo_index.md`).
- Genera `manifest.json` auditabile con sezione `case_import`.
- Genera `run.log`.
- **Non modifica mai i file originali.**

### Output atteso

```text
output/
├── fascicolo_unico.pdf
├── fascicolo_unico_ocr.pdf
├── fascicolo.md
├── fascicolo_index.md
├── manifest.json
└── run.log
```

### Sezione manifest `case_import`

```json
{
  "case_import": {
    "source": "portale_penale_tiap",
    "index_file": "index.html",
    "ordering": "indice_affoliazione",
    "documents_count": 0,
    "matched_count": 0,
    "unmatched_index_items": 0,
    "unlisted_pdfs": 0,
    "warnings": []
  }
}
```

### Riuso componenti esistenti

La funzione dovrà riutilizzare, ove disponibili, i moduli della pipeline:

- output strutturato (`markdown_structure`);
- manifest (`manifest.py`);
- log (`run.log`);
- OCR selettivo (backend OCRmyPDF);
- generazione segnalibri (`bookmarks.py`, `pdf_outline.py`);
- profilo "Accurato testo" quando disponibile (`profiles.py`).

### Note architetturali

- Nessuna dipendenza dagli applicativi TIAP/Windows.
- Il parser HTML deve essere robusto rispetto a indici diversi o parziali
  (struttura tabellare, lista puntata, varianti di portale).
- I PDF già spezzettati per singolo atto possono essere un vantaggio: spesso
  ogni file corrisponde esattamente a un'affoliazione.
- Il parser HTML va testato con **fixture sintetiche**, mai con fascicoli
  reali contenenti dati personali o giudiziari.

### Test necessari

- Fixture HTML sintetiche che simulano indici di portale in formato diverso.
- PDF finti/minimali (1 pagina testo + 1 pagina immagine scansionata).
- Test di matching indice → PDF (corretto, incompleto, sovrannumerario).
- Test di ordinamento per affoliazione, data atto, data file, nome file.
- Test di warning su mismatch (voci orfane, PDF orfani, duplicati).
- Test di merge PDF con verifica dell'ordine delle pagine risultanti.
- Test di generazione segnalibri da indice HTML.
- Test di OCR selettivo (mockato) che verifica quali PDF vengono processati.
- Test del manifest `case_import` con conteggi e warning attesi.

---

Le funzionalità indicate rappresentano obiettivi di sviluppo, non garanzie di
rilascio o accuratezza OCR. Ogni versione richiede verifiche tecniche e
qualitative prima di essere considerata stabile.
