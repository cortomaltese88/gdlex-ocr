# Checklist release v0.1.1

## Pre-release

- [ ] Verificare che `gdlex_ocr/version.py` riporti `0.1.1`.
- [ ] Verificare coerenza tra README, changelog e comportamento della GUI.
- [ ] Controllare che `requirements.txt` contenga versioni fissate e installabili.
- [ ] Rileggere `THIRD_PARTY_NOTICES.md` e aggiornare le evidenze di licenza.
- [ ] Verificare launcher, icone e installazione/rimozione desktop per utente.
- [ ] Eseguire i test senza OCR reale:

```bash
.venv/bin/python -m py_compile app.py gdlex_ocr/*.py
bash scripts/smoke.sh
git diff --check
```

## Privacy e dati

- [ ] Confermare che i documenti siano elaborati localmente e non caricati su servizi cloud.
- [ ] Documentare che Docling può scaricare modelli upstream al primo avvio.
- [ ] Usare solo fixture sintetiche o non sensibili nei test e negli esempi.
- [ ] Non includere PDF originali, output OCR, Markdown generati o `run.log`.
- [ ] Verificare che directory temporanee `.gdlex_ocr_*` non siano incluse.
- [ ] Controllare manualmente screenshot e metadati delle immagini prima della pubblicazione.

## Test OCR reale finale

Eseguito il 14 giugno 2026 sul PDF di release da 158 pagine, con profilo
Bilanciato, blocchi da 15 pagine, OCR italiano e PDF ricercabile attivo.

- [x] Markdown finale creato senza payload `data:image`.
- [x] PDF ricercabile valido e composto da 158 pagine.
- [x] Outline limitato a 11 bookmark tecnici per intervalli di pagine.
- [x] Nessun bookmark PDF content-aware.
- [x] Indice atti separato in `_index.md`, con pagine dichiarate stimate e
  corrispondenti all'inizio del blocco Docling.

## File sensibili e contenuto release

- [ ] Verificare lo stato del repository:

```bash
git status --short
git ls-files
git ls-files --others --exclude-standard
find . -path ./.git -prune -o -path ./.venv -prune -o \
  \( -iname '*.pdf' -o -iname '*.log' -o -name '.env' -o \
     -name '.env.*' -o -name '*.pem' -o -name '*.key' \) -print
```

- [ ] Confermare che `.venv/`, cache Python, output, log e dati sensibili siano esclusi.
- [ ] Ispezionare il diff completo prima della release:

```bash
git diff --check
git diff --stat
git diff
```

## Packaging

- [x] Applicare la scelta descritta in `PACKAGING.md`.
- [x] Non incorporare la `.venv` nel pacchetto v0.1.1.
- [ ] Se viene creato un `.deb`, verificarne contenuto, dipendenze e copyright in ambiente pulito.
- [x] Verificare il `.deb` con `dpkg-deb`, estrazione temporanea e `lintian`.
- [x] Non includere modelli Docling/ONNX senza inventario e verifica delle licenze.
- [x] Confermare che OCRmyPDF e Tesseract restino dipendenze opzionali di sistema.

## Tag e release futuri

Questi comandi sono promemoria e non fanno parte delle verifiche automatiche.
Eseguirli solo dopo approvazione esplicita e dopo aver creato il commit di
release:

```bash
git tag -a v0.1.1 -m "GD LEX OCR v0.1.1"
git push origin main
git push origin v0.1.1
gh release create v0.1.1 --title "GD LEX OCR v0.1.1" \
  --notes-file CHANGELOG.md
```

- [ ] Controllare il tag locale prima del push.
- [ ] Allegare solo artefatti riproducibili e già verificati.
- [x] Generare il checksum SHA-256 del pacchetto.
