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

## Distribuzione tramite repository APT GD LEX

La pubblicazione APT segue il modello di `yt-transcriber` e usa il workflow
manuale `.github/workflows/publish-apt-repo.yml`. Il workflow non costruisce un
nuovo pacchetto: scarica l'asset
`gdlex-ocr_<versione>_all.deb` dalla release GitHub `v<versione>`, ne verifica
nome, versione e architettura, quindi aggiorna il repository separato
`cortomaltese88/gdlex-apt-repo`.

Nel repository APT il pacchetto viene copiato in:

```text
pool/main/g/gdlex-ocr/gdlex-ocr_<versione>_all.deb
```

Gli indici condivisi vengono rigenerati in
`dists/stable/main/binary-amd64/` con `apt-ftparchive` e `gzip`. Il pacchetto
resta `Architecture: all`; l'indice `binary-amd64` è quello già pubblicato dal
repository GD LEX per i client supportati. Il file `Release` usa
`apt-ftparchive.conf` del repository APT.

La firma genera `dists/stable/Release.gpg` e
`dists/stable/InRelease`. La chiave privata non appartiene a questo repository
e non deve essere salvata nei file di progetto. Il workflow si aspetta che
GitHub Actions disponga già dei secret usati anche da `yt-transcriber`:

- `GDLEX_APT_REPO_TOKEN`
- `GDLEX_APT_GPG_PRIVATE_KEY_B64`
- `GDLEX_APT_GPG_PASSPHRASE`
- `GDLEX_APT_GPG_KEY_ID`

I tool richiesti dal workflow sono `apt-ftparchive` (`apt-utils`), gli
strumenti Debian (`dpkg-dev`), `gpg` (`gnupg`), `gzip`, `curl` e GitHub CLI
`gh`.

Per una release già pubblicata, sostituire `<versione>` con la versione senza
prefisso `v` e avviare il workflow:

```bash
gh workflow run publish-apt-repo.yml -f version=<versione>
gh run list --workflow publish-apt-repo.yml
```

Questi comandi pubblicano realmente nel repository APT e devono essere
eseguiti solo dopo approvazione esplicita. Prima dell'avvio occorre verificare
che la release `v<versione>` contenga esattamente
`gdlex-ocr_<versione>_all.deb` e che i secret siano configurati senza esporne
il contenuto.

La configurazione prevista per l'utente finale usa la chiave pubblica ospitata
dal repository APT e `signed-by`:

```bash
curl -fsSL https://cortomaltese88.github.io/gdlex-apt-repo/keys/gdlex-archive-keyring.asc \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/gdlex-archive-keyring.gpg >/dev/null

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gdlex-archive-keyring.gpg] https://cortomaltese88.github.io/gdlex-apt-repo stable main" \
  | sudo tee /etc/apt/sources.list.d/gdlex.list

sudo apt update
sudo apt install gdlex-ocr
```

## Limiti

Il primo avvio richiede accesso alla rete e può richiedere tempo e spazio su
disco per scaricare le dipendenze Python. Anche Docling può scaricare modelli
upstream al primo utilizzo. Venv, cache e modelli restano dati per-user e non
vengono rimossi automaticamente disinstallando il pacchetto Debian.
