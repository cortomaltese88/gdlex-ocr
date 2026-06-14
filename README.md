# GD LEX OCR

**Versione 0.1.0**

GD LEX OCR è un'applicazione desktop locale in Python e PySide6 per
convertire fascicoli e documenti PDF in Markdown tramite Docling.

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

## Licenza

GD LEX OCR è rilasciato con licenza MIT. Il progetto usa Docling e dipendenze
di terze parti: il codebase di Docling è distribuito con licenza MIT, mentre
per i modelli OCR e di analisi del layout e per le altre dipendenze si
applicano le rispettive licenze upstream.

Il software è pensato per elaborare i documenti localmente. Il PDF originale
viene letto durante l'elaborazione e non viene modificato.
