# Changelog

Tutte le modifiche rilevanti del progetto saranno documentate in questo file.

## [0.1.0] - 2026-06-14

Prima release pubblica di GD LEX OCR.

### Funzionalità

- OCR ed elaborazione locale di documenti PDF con output Markdown.
- Profili di elaborazione Veloce, Bilanciato e Accurato.
- Rimozione delle immagini embedded e dei payload base64 dal Markdown.
- Cartella di output configurabile dall'interfaccia.
- Creazione opzionale di un PDF ricercabile tramite OCRmyPDF e Tesseract.
- Segnalibri PDF content-aware dai titoli degli atti, con indice Markdown di
  audit e fallback tecnico per intervalli di pagine.
- Temi Matrix e Chiaro con preferenza locale.
- Icona e launcher per KDE/Linux installabili per il singolo utente.
- Smoke test offline con fixture sintetiche, senza avvio di Docling.
