# Benchmark GD LEX OCR

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
