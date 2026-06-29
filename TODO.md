# TODO - GD LEX OCR

Lista operativa sintetica. Le verifiche devono restare locali; fixture e output
reali o sensibili non vanno salvati nel repository.

## Bugfix brevi

- [ ] Migliorare la distinzione degli errori Docling: comando assente, avvio
  fallito, timeout, uscita anomala e output mancante.
- [ ] Verificare annullamento e conservazione sicura degli output parziali nei
  principali scenari di errore.
- [ ] Aggiungere controlli locali anti-commit per PDF, log, cartelle temporanee
  e Markdown OCR generati.

## UX

- [ ] Valutare watcher filesystem live per aggiornare i pulsanti report quando
  cambiano gli output nella cartella selezionata.
- [ ] Valutare un filtro warning nella tabella di revisione del merge plan.
- [ ] Ridurre rumore e duplicazione nei messaggi di stato del flusso fascicolo.
- [ ] Ridurre, dopo verifica dei layout, la dimensione minima della GUI.
- [ ] Valutare un'anteprima Markdown locale in sola lettura.

## OCR / futuro

- [ ] Validare localmente qualità, ordine di lettura e riferimenti pagina su
  documenti di prova, senza registrarli nel repository.
- [ ] Eseguire ulteriori test manuali su fascicoli pesanti non sensibili sotto
  `/tmp`, senza salvare output nel repository.
- [ ] Valutare sidecar TXT per output testuali separati.
- [ ] Rafforzare il rilevamento di PDF già testuali per evitare OCR superfluo.
- [ ] Verificare cancellazione e process group Docling durante OCR locale.
- [ ] Valutare profili OCR mirati solo in presenza di casi d'uso misurabili.

## Backlog

- [ ] Valutare pulizia opzionale degli intermedi, mantenendo la conservazione
  come comportamento sicuro.
- [ ] Valutare export immagini separato e formati adatti a LLM/RAG locali.
- [ ] Documentare ulteriormente diagnosi, aggiornamento e rimozione.
- [ ] Valutare integrazioni locali con altri strumenti GD LEX tramite formati
  auditabili e senza upload.
