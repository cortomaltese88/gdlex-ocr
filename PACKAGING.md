# Piano packaging Debian

## Stato attuale

La v0.1.0 usa un pacchetto Debian leggero generato da
`scripts/build-deb.sh`. Il pacchetto installa sorgenti, asset, file desktop,
icone, documentazione e il wrapper `/usr/bin/gdlex-ocr`.

La distribuzione `.deb` richiede una decisione esplicita su come fornire Python
3.12, le dipendenze Python non necessariamente disponibili come pacchetti
Debian, le librerie Qt/PySide6 e gli eventuali modelli scaricati da Docling.

## Opzione A: pacchetto launcher/source leggero

Il `.deb` installa codice sorgente, icone, file desktop e un launcher in
percorsi di sistema. Le dipendenze Python vengono predisposte separatamente,
per esempio da uno script amministrato o da istruzioni post-installazione.

Vantaggi:

- pacchetto piccolo;
- nessun modello OCR incorporato;
- OCRmyPDF e Tesseract possono restare `Suggests` o `Recommends`.

Criticità:

- esperienza di installazione incompleta senza una strategia Python definita;
- installare pacchetti con `pip` durante `postinst` è fragile e non conforme
  alle normali aspettative di packaging Debian;
- serve stabilire percorsi, aggiornamenti, disinstallazione e accesso alla rete.

## Opzione B: pacchetto con ambiente virtuale incorporato

Il `.deb` contiene una `.venv` già popolata con Docling, ONNX Runtime, PySide6,
pypdf e dipendenze transitive.

Vantaggi:

- avvio immediato su un sistema molto simile a quello di build;
- versioni Python completamente fissate.

Criticità:

- soluzione non raccomandata per v0.1.0;
- pacchetto grande, poco riproducibile e sensibile ad ABI, architettura e
  versione di glibc/Python;
- duplicazione di librerie gestite dal sistema e aggiornamenti di sicurezza più
  difficili;
- obblighi di licenza e notice più ampi, in particolare per Qt/PySide6,
  dipendenze transitive e modelli eventualmente inclusi.

## Opzione C: sorgente e installazione desktop per utente

La release distribuisce il repository sorgente, `requirements.txt` e gli script
desktop esistenti. L'utente crea la `.venv`, installa le dipendenze Python e
registra il launcher senza privilegi amministrativi.

Vantaggi:

- corrisponde al flusso già documentato e testato;
- non incorpora dipendenze o modelli di terzi;
- non richiede `sudo` e mantiene OCRmyPDF/Tesseract opzionali.

Criticità:

- richiede preparazione manuale dell'ambiente;
- il launcher attuale contiene il percorso assoluto del checkout e quindi non è
  ancora adatto a installazioni generiche o multiutente.

## Scelta per v0.1.0

La release usa una variante minima dell'opzione A:

- codice installato in `/usr/lib/gdlex-ocr`;
- launcher, icone e wrapper installati nei percorsi di sistema;
- dipendenze Python fissate in
  `/usr/share/doc/gdlex-ocr/requirements.txt`, ma non vendorizzate;
- venv utente esterna in `~/.local/share/gdlex-ocr/venv`, oppure interprete
  indicato tramite `GDLEX_OCR_PYTHON`;
- OCRmyPDF e Tesseract dichiarati come componenti opzionali;
- nessun download o `pip install` eseguito dagli script Debian.

Il pacchetto non contiene `.venv`, cache, modelli, PDF, output OCR o log. Lo
script di build controlla automaticamente il payload prima di dichiarare
l'artefatto completato.

Per una release successiva, rendere il pacchetto autosufficiente soltanto dopo
avere:

1. reso il launcher indipendente dal percorso locale di sviluppo;
2. scelto una strategia supportata per Python e dipendenze;
3. generato un inventario completo delle dipendenze transitive e delle licenze;
4. deciso se e come gestire download, cache e versioni dei modelli;
5. definito architetture supportate, aggiornamenti e test in una VM pulita;
6. preparato metadata Debian (`debian/control`, `rules`, `copyright`,
   `changelog`) e una build riproducibile.

OCRmyPDF, `tesseract-ocr` e `tesseract-ocr-ita` dovrebbero restare componenti
esterni opzionali, senza essere incorporati nell'artefatto.
