# Roadmap - GD LEX OCR

Roadmap tecnica indicativa, senza date o garanzie di rilascio. L'elaborazione
resta locale: i documenti originali vengono letti ma non modificati.

## Versioni consolidate

- **v0.1.0-v0.3.x**: pipeline OCR locale, GUI, profili, output strutturati e
  prime analisi locali per sentenze e fascicoli PDP/TIAP.
- **v0.4.0**: output operativi per fascicoli ed export JSON, Markdown e CSV,
  inclusi inventario, unità documentali e riepiloghi.
- **v0.5.0**: flusso fascicolo PDP/TIAP completo dall'analisi al merge plan
  revisionabile, PDF unico con segnalibri, copia PDF light opzionale e handoff
  esplicito alla pipeline OCR.
- **v0.6.0**: consolidamento del flusso fascicolo con progress e annullamento
  per il PDF unico, progress dell'analisi, warning evidenziati nella revisione,
  scelta OCR handoff originale/leggero/automatico, stima dry-run, validazione
  merge plan, export report e pulsanti rapidi per aprire i report.

Molte funzioni inizialmente ipotizzate per la linea `v1.x` sono quindi già
disponibili. La numerazione futura descrive il consolidamento progressivo del
flusso esistente, non una promessa di nuove funzioni o date.

## v0.5.1 - Consolidamento post-release

- Micro-fix emersi dall'audit di `v0.5.0`.
- Copertura dei casi limite PDF, merge e parser degli indici.
- Allineamento di documentazione, warning e messaggi utente.
- Nessuna modifica sostanziale al flusso principale.

## Prossimi candidati

- Watcher filesystem live per aggiornare i pulsanti report quando cambiano gli
  output nella cartella selezionata.
- Ulteriori test manuali su fascicoli pesanti non sensibili generati sotto
  `/tmp`.
- Eventuale filtro warning nella tabella di revisione.
- Rifiniture incrementali del flusso fascicolo e dei messaggi utente.
- Riduzione della dimensione minima della finestra GUI.

## Direzione verso v1.0

- Stabilità per l'uso interno e diagnostica verificabile.
- Miglioramento incrementale della qualità OCR e degli output strutturati.
- Compatibilità con flussi LLM/RAG mantenendo separati dati e metadati tecnici.
- Elaborazione sempre locale, senza upload cloud e senza modificare gli
  originali.

Ogni versione richiede verifiche tecniche e qualitative con fixture sintetiche
prima di essere considerata stabile.
