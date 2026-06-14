# Licenze e componenti terzi

Questo documento registra le licenze rilevate localmente per le dipendenze
dirette di GD LEX OCR v0.1.1 e per gli strumenti di sistema opzionali. Non
costituisce consulenza legale e non sostituisce i testi di licenza upstream.

## Componenti

| Componente | Uso nel progetto | Licenza rilevata | Distribuzione | Note operative |
|---|---|---|---|---|
| Docling 2.102.1 | Conversione locale dei PDF in Markdown e pipeline di analisi | MIT (`License-Expression` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`. Può usare dipendenze transitive e scaricare modelli upstream al primo utilizzo; licenze di dipendenze e modelli non sono coperte integralmente da questo inventario. |
| ONNX Runtime 1.26.0 | Runtime CPU per l'inferenza dei modelli OCR | MIT License (campo `License` e classifier nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`. Verificare separatamente eventuali modelli eseguiti dal runtime. |
| PySide6 6.11.1 | Interfaccia grafica Qt | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` (campo `License` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | I metadata dichiarano disponibilità open source LGPLv3/GPLv2/GPLv3 e commerciale. Prima di distribuire PySide6 o Qt dentro un `.deb` o altro bundle, verificare gli obblighi applicabili alla modalità scelta, inclusi avvisi, testi di licenza e sostituibilità delle librerie. |
| pypdf 6.13.2 | Suddivisione PDF, lettura struttura e gestione segnalibri | BSD-3-Clause (`License-Expression` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`; conservare copyright e testo BSD quando richiesto dalla forma di distribuzione. |
| OCRmyPDF 15.2.0+dfsg1-1 | Creazione opzionale di un PDF ricercabile con layer OCR | MPL-2.0 per i file principali del pacchetto; il copyright Debian elenca licenze ulteriori per file specifici | Dipendenza di sistema esterna; non inclusa nel repository | Pacchetto Ubuntu installato separatamente. È invocato solo per il PDF ricercabile. In caso di redistribuzione del pacchetto, usare il relativo file `debian/copyright` completo e considerare anche le sue dipendenze. |
| Tesseract OCR 5.3.4-1build5 | Motore OCR usato da OCRmyPDF | Apache-2.0 (copyright del pacchetto Debian/Ubuntu) | Dipendenza di sistema esterna; non inclusa nel repository | Installato e aggiornato tramite il gestore pacchetti di sistema. |
| Tesseract dati italiani 4.1.0-2 | Modello linguistico italiano per Tesseract | Apache-2.0 (copyright del pacchetto Debian/Ubuntu) | Dipendenza di sistema esterna; non inclusa nel repository | Pacchetto `tesseract-ocr-ita`, installato separatamente. |

## Fonti locali consultate

Le rilevazioni sono state eseguite il 14 giugno 2026 con:

```bash
.venv/bin/python -m pip show docling onnxruntime PySide6 pypdf
```

Sono stati inoltre letti i campi `License`, `License-Expression`,
`License-File` e i classifier nei file `METADATA` installati sotto
`.venv/lib/python3.12/site-packages`.

Per gli strumenti opzionali:

```bash
apt-cache show ocrmypdf tesseract-ocr tesseract-ocr-ita
dpkg-query -W ocrmypdf tesseract-ocr tesseract-ocr-ita
```

Le licenze sono state verificate nei file locali:

```text
/usr/share/doc/ocrmypdf/copyright
/usr/share/doc/tesseract-ocr/copyright
/usr/share/doc/tesseract-ocr-ita/copyright
```

## Limiti dell'inventario

Questo elenco copre le quattro dipendenze Python dirette dichiarate in
`requirements.txt` e i tre pacchetti di sistema opzionali. Non è un Software
Bill of Materials completo: prima di distribuire un ambiente Python, modelli
OCR, librerie Qt o altri artefatti incorporati occorre generare e verificare
anche l'inventario delle dipendenze transitive e includere gli avvisi richiesti.
