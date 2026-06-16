# Licenze e componenti terzi

Questo documento registra le licenze rilevate localmente per GD LEX OCR v0.1.6
e per lo stato post-audit successivo. Non costituisce consulenza legale e non
sostituisce i testi di licenza upstream.

GD LEX OCR è codice del progetto, rilasciato con la licenza indicata nel file
`LICENSE` del repository. I componenti di terze parti mantengono le rispettive
licenze. Il progetto non incorpora necessariamente il codice sorgente, i
modelli o gli asset di tutti i componenti elencati: molti sono installati come
dipendenze Python, pacchetti di sistema o runtime opzionali.

Per termini autorevoli, obblighi di redistribuzione, copyright completi e
licenze di file specifici, verificare sempre i file di licenza upstream e i
metadata dei pacchetti effettivamente distribuiti.

## Dipendenze Python dirette

| Componente | Uso nel progetto | Licenza rilevata | Distribuzione | Note operative |
|---|---|---|---|---|
| Docling 2.102.1 | Conversione locale dei PDF in Markdown e pipeline di analisi | MIT (`License-Expression` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`. Può usare dipendenze transitive e scaricare modelli upstream al primo utilizzo; licenze di dipendenze e modelli non sono coperte integralmente da questo inventario. |
| ONNX Runtime 1.26.0 | Runtime CPU per l'inferenza dei modelli OCR | MIT License (campo `License` e classifier nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`. Verificare separatamente eventuali modelli eseguiti dal runtime. |
| PySide6 6.11.1 | Interfaccia grafica Qt | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` (campo `License` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | I metadata dichiarano disponibilità open source LGPLv3/GPLv2/GPLv3 e commerciale. Prima di distribuire PySide6 o Qt dentro un `.deb` o altro bundle, verificare gli obblighi applicabili alla modalità scelta, inclusi avvisi, testi di licenza e sostituibilità delle librerie. |
| pypdf 6.13.2 | Suddivisione PDF, lettura struttura e gestione segnalibri | BSD-3-Clause (`License-Expression` nei metadata Python) | Dipendenza Python esterna; non inclusa nel repository | Installata tramite `requirements.txt`; conservare copyright e testo BSD quando richiesto dalla forma di distribuzione. |

## Strumenti di sistema opzionali

| Componente | Uso nel progetto | Licenza rilevata | Distribuzione | Note operative |
|---|---|---|---|---|
| OCRmyPDF 15.2.0+dfsg1-1 | Creazione opzionale di un PDF ricercabile con layer OCR | MPL-2.0 per i file principali del pacchetto; il copyright Debian elenca licenze ulteriori per file specifici | Dipendenza di sistema esterna; non inclusa nel repository | Pacchetto Ubuntu installato separatamente. È invocato solo per il PDF ricercabile. In caso di redistribuzione del pacchetto, usare il relativo file `debian/copyright` completo e considerare anche le sue dipendenze. |
| Tesseract OCR 5.3.4-1build5 | Motore OCR usato da OCRmyPDF | Apache-2.0 (copyright del pacchetto Debian/Ubuntu) | Dipendenza di sistema esterna; non inclusa nel repository | Installato e aggiornato tramite il gestore pacchetti di sistema. |
| Tesseract dati italiani 4.1.0-2 | Modello linguistico italiano per Tesseract | Apache-2.0 (copyright del pacchetto Debian/Ubuntu) | Dipendenza di sistema esterna; non inclusa nel repository | Pacchetto `tesseract-ocr-ita`, installato separatamente. |

Eventuali backend esterni configurati dall'utente, inclusi prodotti
proprietari, non sono distribuiti né licenziati da GD LEX OCR. L'utente deve
verificarne licenza, documentazione CLI e condizioni d'uso. Master PDF Editor
e PDF Studio non vengono automatizzati in assenza di una CLI OCR batch
verificata.

## Componenti transitivi e runtime

| Componente | Uso nel progetto | Licenza rilevata | Distribuzione | Note operative |
|---|---|---|---|---|
| RapidOCR / OCR interno usato da Docling | OCR interno nella pipeline Docling, quando abilitato dal profilo e dalla configurazione Docling | Da verificare nei pacchetti transitivi effettivamente installati | Dipendenza transitiva/runtime di Docling; non dichiarata direttamente in `requirements.txt` | Non viene vendored nel repository. Dal ciclo v0.1.5 / v0.1.6 il profilo **Accurato testo** privilegia OCRmyPDF/Tesseract per creare un PDF ricercabile prima della conversione; altri profili possono ancora usare l'OCR interno di Docling. Verificare i file upstream per termini autorevoli. |
| Python 3.12 | Runtime dell'applicazione e della venv utente | Python Software Foundation License e licenze correlate, secondo la build installata | Runtime esterno; non incluso nel repository | Il pacchetto Debian leggero usa l'interprete di sistema e crea una venv utente. Verificare la licenza della distribuzione Python usata nel sistema di destinazione. |
| Dipendenze transitive Python | Librerie richieste da Docling, ONNX Runtime, PySide6 e pypdf | Variabile per pacchetto | Installate nella venv da `pip` | Questo documento non è un SBOM completo. Prima di redistribuire una venv o un bundle autonomo, generare e verificare l'inventario completo delle dipendenze transitive e dei relativi avvisi. |
| Modelli Docling/OCR eventualmente scaricati | Modelli usati da componenti upstream al primo utilizzo | Variabile per modello | Cache/runtime upstream; non inclusi nel repository | L'applicazione non effettua upload cloud dei documenti, ma Docling può scaricare modelli dai servizi upstream da cui dipende. Verificare licenze, cache e condizioni di distribuzione dei modelli separatamente. |

## Packaging, desktop integration e asset

| Componente | Uso nel progetto | Licenza rilevata | Distribuzione | Note operative |
|---|---|---|---|---|
| Debian tooling | Build del pacchetto leggero, wrapper, launcher e file desktop | Strumenti di sistema con licenze proprie | Strumenti esterni; non inclusi nel repository salvo script del progetto | `scripts/build-deb.sh`, `packaging/gdlex-ocr`, `packaging/gdlex-ocr.desktop` e la pagina man sono file del progetto. Gli strumenti Debian invocati localmente mantengono le rispettive licenze. |
| Asset icona e splash GD LEX OCR | Identità applicativa, launcher, tray e splash screen | Licenza del progetto, salvo diversa indicazione nei singoli file | Inclusi nel repository | Gli asset sotto `assets/` sono parte del progetto. Prima di sostituirli con asset esterni, conservare provenienza e licenza nel repository. |

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

Questo elenco copre le dipendenze Python dirette dichiarate in
`requirements.txt`, i principali strumenti di sistema opzionali, componenti
transitivi rilevanti per l'OCR e gli asset noti del progetto. Non è un Software
Bill of Materials completo: prima di distribuire un ambiente Python, modelli
OCR, librerie Qt o altri artefatti incorporati occorre generare e verificare
anche l'inventario delle dipendenze transitive e includere gli avvisi richiesti.
