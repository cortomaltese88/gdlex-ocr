# GD LEX OCR

Applicazione desktop locale in Python e PySide6 per convertire fascicoli PDF
in Markdown tramite Docling.

## Avvio

Attivare l'ambiente Python 3.12 con `PySide6`, `pypdf` e `docling`, quindi:

```bash
python app.py
```

L'applicazione non carica documenti su servizi cloud. Il PDF originale viene
solo letto; i blocchi PDF e Markdown intermedi sono conservati in una
sottocartella `.gdlex_ocr_*` nella cartella di output.
