# Piano packaging Debian

## Scelta per v0.1.x

L'applicazione usa un pacchetto Debian leggero generato da
`scripts/build-deb.sh`. Il pacchetto installa sorgenti, asset, file desktop,
icone, documentazione e il wrapper `/usr/bin/gdlex-ocr`.

Il pacchetto non incorpora una venv Python. Il wrapper crea invece, al primo
avvio e nel contesto dell'utente corrente:

```text
~/.local/share/gdlex-ocr/venv
```

Il setup esegue `python3 -m venv`, aggiorna `pip` e installa le versioni fissate
in `/usr/share/doc/gdlex-ocr/requirements.txt`. Se la venv esiste ma non espone
gli import essenziali, il wrapper prova ad aggiornare nuovamente i requirements.
Non usa `sudo` e non esegue installazioni Python dal `postinst` Debian.

Il log viene scritto in `~/.local/state/gdlex-ocr/setup.log`. Una directory
`~/.local/state/gdlex-ocr/setup.lock` serializza i tentativi concorrenti. In
caso di errore il wrapper stampa il percorso del log e usa KDialog o Zenity,
quando disponibili, per mostrare un avviso grafico sintetico.

## Comandi operativi

`gdlex-ocr --setup-venv` forza la creazione o l'aggiornamento della venv e poi
esce.

`gdlex-ocr --doctor` controlla Python, venv, import essenziali, OCRmyPDF,
Tesseract, lingua italiana e asset installati senza avviare la GUI o eseguire
OCR. Restituisce:

- `0` se tutti i controlli passano;
- `1` se manca un componente essenziale;
- `2` se mancano soltanto strumenti OCR opzionali.

## Contenuto e dipendenze

Il codice applicativo è installato in `/usr/lib/gdlex-ocr`. Docling, ONNX
Runtime, PySide6 e pypdf vengono installati nella venv utente dal file
requirements incluso nel pacchetto.

OCRmyPDF, Tesseract e il modello linguistico italiano restano componenti di
sistema opzionali dichiarati come `Suggests`. La conversione Markdown continua
a funzionare in loro assenza.

Il `.deb` non contiene `.venv`, cache Python, repository Git, modelli, PDF,
output OCR, log o file `manifest.json`. Il manifest è un file di output
runtime scritto nella cartella dell'utente durante l'elaborazione e non viene
incluso nel pacchetto. Lo script di build controlla il payload e genera il
checksum SHA-256 accanto all'artefatto.

Il modulo `gdlex_ocr/output_layout.py` fa parte del codice applicativo
installato e descrive soltanto i percorsi runtime standard: non crea né include
alcun output nel pacchetto.

## Limiti

Il primo avvio richiede accesso alla rete e può richiedere tempo e spazio su
disco per scaricare le dipendenze Python. Anche Docling può scaricare modelli
upstream al primo utilizzo. Venv, cache e modelli restano dati per-user e non
vengono rimossi automaticamente disinstallando il pacchetto Debian.
