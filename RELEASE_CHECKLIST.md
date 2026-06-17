# Checklist release v0.1.7

La release `v0.1.7` è in preparazione. Gli item aperti rimangono promemoria
operativi per audit manuale o pubblicazione; non vanno barrati senza una nuova
verifica effettiva.

## Pre-release v0.1.7

- [x] Verificare che `gdlex_ocr/version.py` riporti `0.1.7`.
- [x] Verificare coerenza tra README, changelog e comportamento della GUI.
- [x] Controllare che `requirements.txt` contenga versioni fissate e installabili.
- [x] Rileggere `THIRD_PARTY_NOTICES.md` e aggiornare le evidenze di licenza.
- [ ] Verificare nuovamente launcher, icone e installazione/rimozione desktop
  per utente prima della prossima release.
- [x] Eseguire i test senza OCR reale:

```bash
.venv/bin/python -m py_compile app.py gdlex_ocr/*.py scripts/*.py scripts/capture-gui-screenshots.py
.venv/bin/python app.py --version
.venv/bin/python app.py --doctor
.venv/bin/python app.py --help
bash scripts/smoke.sh
desktop-file-validate packaging/gdlex-ocr.desktop
bash -n scripts/*.sh
git diff --check
scripts/capture-gui-screenshots.py
```

## Privacy e dati

- [x] Confermare che i documenti siano elaborati localmente e non caricati su servizi cloud.
- [x] Documentare che Docling può scaricare modelli upstream al primo avvio.
- [x] Usare solo fixture sintetiche o non sensibili nei test e negli esempi.
- [x] Non includere PDF originali, output OCR, Markdown generati o `run.log`.
- [x] Verificare che directory temporanee `.gdlex_ocr_*` non siano incluse.
- [ ] Controllare manualmente screenshot e metadati delle immagini prima della
  prossima pubblicazione.

## Perimetro test v0.1.7

- [x] Non eseguire OCR reale durante la preparazione della release.
- [x] Usare esclusivamente smoke test e fixture sintetiche.
- [x] Verificare identità/versione, integrazione desktop, splash, system tray
  payload Debian e benchmark sintetico tramite la suite offline.

## File sensibili e contenuto release

- [x] Verificare lo stato del repository:

```bash
git status --short
git ls-files
git ls-files --others --exclude-standard
find . -path ./.git -prune -o -path ./.venv -prune -o \
  \( -iname '*.pdf' -o -iname '*.log' -o -name '.env' -o \
     -name '.env.*' -o -name '*.pem' -o -name '*.key' \) -print
```

- [x] Confermare che `.venv/`, cache Python, output, log e dati sensibili siano esclusi.
- [x] Ispezionare il diff completo prima della release:

```bash
git diff --check
git diff --stat
git diff
```

## Packaging

- [x] Applicare la scelta descritta in `PACKAGING.md`.
- [x] Non incorporare la `.venv` nel pacchetto v0.1.7.
- [ ] Se viene creato un nuovo `.deb`, verificarne contenuto, dipendenze e
  copyright in ambiente pulito.
- [x] Verificare il `.deb` con `dpkg-deb`, estrazione temporanea e `lintian`.
- [x] Non includere modelli Docling/ONNX senza inventario e verifica delle licenze.
- [x] Confermare che OCRmyPDF e Tesseract restino dipendenze opzionali di sistema.
- [ ] Installare manualmente il pacchetto pubblicato con `sudo apt install`.
- [ ] Eseguire `/usr/bin/gdlex-ocr --doctor` sul pacchetto installato,
  controllando che non venga usato un wrapper `~/.local/bin/gdlex-ocr`.

```bash
bash scripts/build-deb.sh
dpkg-deb -f dist/gdlex-ocr_0.1.7_all.deb Package Version Architecture Depends Suggests
dpkg-deb --contents dist/gdlex-ocr_0.1.7_all.deb | \
  grep -E '(\.venv|__pycache__|\.git|run\.log|manifest\.json|Fascicolo|Downloads|Documenti)' || true
sha256sum dist/gdlex-ocr_0.1.7_all.deb
sudo apt install ./dist/gdlex-ocr_0.1.7_all.deb
/usr/bin/gdlex-ocr --doctor
```

## Tag e release futuri

Questi comandi sono promemoria e non fanno parte delle verifiche automatiche.
Eseguirli solo dopo approvazione esplicita e dopo aver creato il commit di
release. Aggiornare tag e versione prima di riusarli per release successive:

```bash
git tag -a vX.Y.Z -m "GD LEX OCR vX.Y.Z"
git push origin main
git push origin vX.Y.Z
gh release create vX.Y.Z --title "GD LEX OCR vX.Y.Z" \
  --notes-file CHANGELOG.md
```

- [ ] Controllare il tag locale prima del push.
- [ ] Allegare solo artefatti riproducibili e già verificati.
- [x] Generare il checksum SHA-256 del pacchetto.
