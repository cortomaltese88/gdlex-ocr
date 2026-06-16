# Benchmark GD LEX OCR

I benchmark sono preliminari e servono solo come riferimento interno. Non
includere nel repository contenuti OCR, PDF reali, log o dati sensibili.
Confrontare i risultati solo sullo stesso documento, stessa macchina e stessa
configurazione.

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
OCRmyPDF/Tesseract e usarlo come sorgente Docling. Non ci sono ancora dati
comparabili e ripetibili nel repository per questi profili. Le modifiche
pre-release v0.1.6 non aggiungono nuove misure di benchmark.

TODO: eseguire un benchmark ripetibile su fixture o documento locale non
sensibile, registrando almeno profilo, versione, backend OCR, numero pagine,
CPU, durata totale e pagine/minuto.
