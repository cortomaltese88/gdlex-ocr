# Benchmark GD LEX OCR

I benchmark sono preliminari e servono solo come riferimento interno. Non
includere nel repository contenuti OCR, PDF reali, log o dati sensibili.
Confrontare i risultati solo sullo stesso documento, stessa macchina e stessa
configurazione.

## Benchmark sintetico ripetibile

Il benchmark sintetico è il percorso consigliato per confronti locali tra
modifiche del codice. Genera fixture PDF senza contenuti reali e salva fixture,
blocchi e risultati runtime sotto `tmp/benchmark-synthetic/`, directory già
esclusa da git.

Comando rapido:

```bash
.venv/bin/python scripts/benchmark_synthetic.py \
  --profile "PDF già ricercabile" \
  --pages 6 \
  --runs 3
```

Il comando genera e misura:

- `synthetic_searchable.pdf`: PDF testuale/ricercabile generato con `pypdf`;
- `synthetic_image.pdf`: PDF raster sintetico generato con Pillow, se presente;
- conteggio pagine, suddivisione in blocchi secondo il profilo scelto e verifica
  del testo estraibile;
- un report JSON runtime in
  `tmp/benchmark-synthetic/results/latest.json`.

Se Pillow non è disponibile, limitare il benchmark al caso testuale:

```bash
.venv/bin/python scripts/benchmark_synthetic.py --cases searchable
```

Per misurare anche OCRmyPDF su input raster sintetico locale:

```bash
.venv/bin/python scripts/benchmark_synthetic.py \
  --profile "Accurato testo" \
  --pages 4 \
  --runs 1 \
  --run-ocr \
  --ocr-timeout 600 \
  --ocr-jobs 2
```

`--run-ocr` fallisce con un errore esplicito se `ocrmypdf` o le dipendenze di
sistema non sono disponibili. Non usare PDF reali o sensibili per questo
benchmark.

### Metodologia

Registrare sempre:

- commit o tag locale testato;
- comando esatto;
- profilo e block size;
- numero pagine e numero run;
- presenza o assenza di `--run-ocr`;
- CPU/macchina e carico anomalo, se rilevante;
- percorso del JSON prodotto.

I numeri non sono promesse di prestazione assoluta. Servono solo per confronti
relativi sulla stessa macchina e con la stessa configurazione.

## Baseline reale - 2026-06-14

Documento: Fascicolo_PM.pdf
Pagine: 158
Profilo: v0.1.0 default
Block size: 5 pagine
Docling: 2.102.1
Device: CPU
OCR: attivo
Tabelle/layout: default Docling

Durata totale: 27 min 43 sec
Velocità: 5,7 pagine/minuto

Note:

- Output Markdown generato correttamente.
- Elaborazione completata senza crash.
- Intermedi conservati in `.gdlex_ocr_*`.

## Obiettivo successivo

Battere la baseline con il profilo **Bilanciato** (block size 15, num_threads 10,
page_batch_size 6, onnxruntime 1.26.0).

Target: > 5,7 pagine/minuto — durata totale < 27m43s su stesso documento e
stessa macchina (CPU).

Registrare qui il risultato quando disponibile, senza includere contenuti del
documento né dati sensibili.

## Stato post v0.1.5 / pre v0.1.6

La v0.1.5 ha introdotto il profilo **PDF già ricercabile** e ha migliorato
**Accurato testo**, che ora può creare un PDF ricercabile tramite
OCRmyPDF/Tesseract e usarlo come sorgente Docling. Per confronti futuri usare
il benchmark sintetico sopra e registrare comando, profilo, versione, backend
OCR, numero pagine, CPU, durata totale e pagine/minuto.
