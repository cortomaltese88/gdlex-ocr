# Checklist release v0.1.0

## Pre-release

- [ ] Verificare che `gdlex_ocr/version.py` riporti `0.1.0`.
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

- [ ] Applicare la scelta descritta in `PACKAGING.md`.
- [ ] Non incorporare la `.venv` nel pacchetto v0.1.0.
- [ ] Se viene creato un `.deb`, verificarne contenuto, dipendenze e copyright in ambiente pulito.
- [ ] Non includere modelli Docling/ONNX senza inventario e verifica delle licenze.
- [ ] Confermare che OCRmyPDF e Tesseract restino dipendenze opzionali di sistema.

## Tag e release futuri

Questi comandi sono promemoria e non fanno parte delle verifiche automatiche.
Eseguirli solo dopo approvazione esplicita e dopo aver creato il commit di
release:

```bash
git tag -a v0.1.0 -m "GD LEX OCR v0.1.0"
git push origin main
git push origin v0.1.0
gh release create v0.1.0 --title "GD LEX OCR v0.1.0" \
  --notes-file CHANGELOG.md
```

- [ ] Controllare il tag locale prima del push.
- [ ] Allegare solo artefatti riproducibili e già verificati.
- [ ] Pubblicare checksum degli eventuali pacchetti.
