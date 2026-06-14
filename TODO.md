# TODO - GD LEX OCR

Lista operativa delle prossime attività. Tutte le verifiche devono essere
eseguite localmente, senza caricare documenti su servizi cloud. Il PDF
originale è sempre trattato in sola lettura e non viene mai modificato.

## Priorità alta

- [ ] Eseguire un test completo locale su `Fascicolo_PM.pdf`, senza registrare
  nel repository contenuti, dati personali o dettagli del documento.
- [ ] Verificare la qualità OCR su un PDF scansionato, controllando testo,
  punteggiatura, intestazioni, numerazione e ordine di lettura.
- [ ] Verificare il Markdown finale: completezza, ordine dei blocchi,
  leggibilità e assenza di duplicazioni o omissioni evidenti.
- [ ] Controllare la corrispondenza tra riferimenti alle pagine originali,
  intervalli dei blocchi e contenuto Markdown prodotto.
- [ ] Migliorare la gestione degli errori Docling, distinguendo almeno comando
  assente, processo non avviabile, uscita anomala, timeout e output mancante.
- [ ] Verificare annullamento, conservazione degli output parziali e messaggi
  mostrati all'utente nei principali scenari di errore.
- [ ] Aggiungere una protezione anti-commit per output sensibili, con controlli
  locali su PDF, log, cartelle temporanee e Markdown OCR generati.

## Priorità media

- [ ] Aggiungere un comando per aprire la cartella di output al termine
  dell'elaborazione o su richiesta dell'utente.
- [ ] Aggiungere un'anteprima Markdown locale, in sola lettura, senza alterare
  il file generato.
- [ ] Definire controlli automatici minimi per conteggio pagine, suddivisione
  in blocchi, unione Markdown e gestione dei percorsi di output.
- [ ] Valutare un indice iniziale del fascicolo con collegamenti o riferimenti
  alle sezioni prodotte.
- [ ] Definire il formato di `fascicolo_per_chatgpt.md`, mantenendo separati
  contenuto OCR, metadati tecnici e avvertenze sulla qualità.

## Priorità futura

- [ ] Preparare il packaging `.deb`, dopo aver stabilizzato dipendenze,
  installazione di Docling e comportamento sui sistemi di destinazione.
- [ ] Valutare profili OCR specifici per differenti categorie documentali,
  senza introdurre trasformazioni irreversibili sulle fonti.
- [ ] Valutare un'integrazione con `gdlex-normattiva` o con un sistema RAG
  locale, definendo prima formati di scambio, tracciabilità delle fonti e
  separazione dei dati.
- [ ] Documentare procedure di installazione, aggiornamento, diagnosi e
  rimozione per l'uso interno.
