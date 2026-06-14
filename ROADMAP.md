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

Le funzionalità indicate rappresentano obiettivi di sviluppo, non garanzie di
rilascio o accuratezza OCR. Ogni versione richiede verifiche tecniche e
qualitative prima di essere considerata stabile.
