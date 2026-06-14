# Piano packaging Debian

## Stato attuale

Il repository non contiene ancora un pacchetto Debian. La directory
`packaging/` contiene soltanto `gdlex-ocr.desktop`; gli script
`install-desktop.sh` e `uninstall-desktop.sh` installano launcher, icone e
wrapper per il singolo utente.

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

## Raccomandazione per v0.1.0

Usare l'opzione C per la release v0.1.0 e non pubblicare ancora un `.deb`.
È la scelta con minore rischio operativo e legale rispetto allo stato attuale.

Per una release successiva, progettare l'opzione A soltanto dopo avere:

1. reso il launcher indipendente dal percorso locale di sviluppo;
2. scelto una strategia supportata per Python e dipendenze;
3. generato un inventario completo delle dipendenze transitive e delle licenze;
4. deciso se e come gestire download, cache e versioni dei modelli;
5. definito architetture supportate, aggiornamenti e test in una VM pulita;
6. preparato metadata Debian (`debian/control`, `rules`, `copyright`,
   `changelog`) e una build riproducibile.

OCRmyPDF, `tesseract-ocr` e `tesseract-ocr-ita` dovrebbero restare componenti
esterni opzionali, senza essere incorporati nell'artefatto.
