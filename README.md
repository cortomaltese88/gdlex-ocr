# GD LEX OCR

**Versione 0.1.0**

GD LEX OCR è un'applicazione desktop locale in Python e PySide6 per
convertire fascicoli e documenti PDF in Markdown tramite Docling.

## Prerequisiti minimi

- Python 3.12
- Un ambiente virtuale Python
- Le dipendenze elencate in `requirements.txt`

Per preparare l'ambiente:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Avvio

Attivare l'ambiente Python 3.12, quindi avviare l'applicazione:

```bash
source .venv/bin/activate
python app.py
```

## Elaborazione locale

L'OCR viene eseguito localmente: nessun documento viene caricato su servizi
cloud. Il PDF originale viene solo letto; i blocchi PDF e Markdown intermedi
sono conservati in una sottocartella `.gdlex_ocr_*` nella cartella di output.

Al primo avvio, Docling può scaricare modelli dai servizi upstream da cui
dipende. L'applicazione non effettua upload cloud dei documenti; download,
cache e gestione di dipendenze e modelli restano soggetti al comportamento e
alle configurazioni dei relativi progetti upstream.

## Licenza

GD LEX OCR è rilasciato con licenza MIT. Il progetto usa Docling e dipendenze
di terze parti: il codebase di Docling è distribuito con licenza MIT, mentre
per i modelli OCR e di analisi del layout e per le altre dipendenze si
applicano le rispettive licenze upstream.

Il software è pensato per elaborare i documenti localmente. Il PDF originale
viene letto durante l'elaborazione e non viene modificato.
