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
- [ ] Battere la baseline di 5,7 pag/min (27m43s su 158 pag) usando il profilo
  Bilanciato con onnxruntime.
- [ ] Migliorare la gestione degli errori Docling, distinguendo almeno comando
  assente, processo non avviabile, uscita anomala, timeout e output mancante.
- [ ] Verificare annullamento, conservazione degli output parziali e messaggi
  mostrati all'utente nei principali scenari di errore.
- [ ] Aggiungere una protezione anti-commit per output sensibili, con controlli
  locali su PDF, log, cartelle temporanee e Markdown OCR generati.

## Priorità media

- [ ] Aggiungere un'anteprima Markdown locale, in sola lettura, senza alterare
  il file generato.
- [x] Definire controlli automatici minimi per conteggio pagine, suddivisione
  in blocchi, unione Markdown e gestione dei percorsi di output.
- [ ] Valutare un indice iniziale del fascicolo con collegamenti o riferimenti
  alle sezioni prodotte.
- [ ] Definire il formato di `fascicolo_per_chatgpt.md`, mantenendo separati
  contenuto OCR, metadati tecnici e avvertenze sulla qualità.

## Priorità futura

- [ ] Profilo **Solo Testo**: rilevare se il PDF contiene già testo selezionabile
  (PDF testuale) e saltare l'OCR, estraendo direttamente il testo con pypdf o
  Docling in modalità senza OCR. Utile per documenti nativi digitali, atti
  informatici e sentenze redatte in formato testuale.
- [ ] Valutare la pulizia opzionale dei PDF e Markdown intermedi al termine
  dell'elaborazione, mantenendo la conservazione come comportamento sicuro.
- [ ] Migliorare il logging buffered del processo Docling per rendere più
  regolare l'aggiornamento dei messaggi durante elaborazioni lunghe.
- [ ] Verificare il comportamento del process group Docling durante un OCR
  reale, inclusi annullamento, `SIGTERM` e fallback `SIGKILL`.
- [ ] Preparare il packaging `.deb`, dopo aver stabilizzato dipendenze,
  installazione di Docling e comportamento sui sistemi di destinazione.
- [ ] Valutare profili OCR specifici per differenti categorie documentali,
  senza introdurre trasformazioni irreversibili sulle fonti.
- [ ] Aggiungere l'esportazione opzionale delle immagini come file separati,
  mantenendo il Markdown leggero e adatto a LLM/RAG.
- [ ] Valutare una scelta avanzata tra esportazione immagini `embedded`,
  `referenced` e `placeholder`, qualora emerga un caso d'uso concreto.
- [ ] Valutare un'integrazione con `gdlex-normattiva` o con un sistema RAG
  locale, definendo prima formati di scambio, tracciabilità delle fonti e
  separazione dei dati.
- [ ] Documentare procedure di installazione, aggiornamento, diagnosi e
  rimozione per l'uso interno.

## UI / identità visiva

- [x] Rifare la splash screen in stile Matrix / GD LEX, con pioggia digitale
  animata, durata leggibile e avvio non bloccante.
- [x] Aggiungere temi Matrix e Chiaro con cambio live e preferenza persistente.
- [x] Aggiungere dialog Informazioni con credits, componenti, licenza e privacy.
- [ ] Creare icona applicazione coerente con la suite GD LEX.
  - stile Matrix / GD LEX;
  - leggibile anche in formato piccolo;
  - compatibile con launcher Linux;
  - nessuna immagine sensibile o derivata da fascicoli reali;
  - formati target: SVG sorgente, PNG 256x256/128x128/64x64.
