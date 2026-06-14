# GD LEX OCR

## Versione 0.1.0

GD LEX OCR è un'applicazione desktop locale in Python e PySide6 per
convertire fascicoli e documenti PDF in Markdown tramite Docling.

## Prerequisiti minimi

- Python 3.12
- Un ambiente virtuale Python
- Le dipendenze elencate in `requirements.txt`

Dipendenze principali:

| Pacchetto      | Versione  | Scopo                              |
|----------------|-----------|------------------------------------|
| docling        | 2.102.1   | OCR e conversione PDF → Markdown   |
| onnxruntime    | 1.26.0    | Inferenza modelli OCR (CPU)        |
| PySide6        | 6.11.1    | Interfaccia grafica                |
| pypdf          | 6.13.2    | Suddivisione in blocchi PDF        |

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

## Test

La suite smoke offline usa solo fixture sintetiche e non avvia Docling:

```bash
bash scripts/smoke.sh
```

## Profili di elaborazione

L'applicazione offre tre profili selezionabili dalla GUI. Il default è **Bilanciato**.

| Profilo     | Blocco | Thread | Batch | Tabelle  | Immagini | Grafici |
|-------------|-------:|-------:|------:|----------|----------|---------|
| Veloce      |  25 p. |     12 |     8 | fast     | no       | no      |
| Bilanciato  |  15 p. |     10 |     6 | fast     | no       | no      |
| Accurato    |  10 p. |      6 |     4 | accurate | sì       | sì      |

Il cambio profilo aggiorna automaticamente la dimensione blocco. La dimensione
può essere modificata manualmente dopo aver selezionato il profilo.

**Veloce** massimizza la velocità disabilitando l'analisi di immagini e grafici
e usando blocchi grandi. Adatto a documenti con prevalente contenuto testuale.

**Bilanciato** (default) bilancia velocità e qualità; ottimizzato per fascicoli
di uso comune.

**Accurato** attiva l'analisi di immagini e grafici e usa blocchi più piccoli per
maggiore robustezza. Adatto a documenti con tabelle complesse o contenuto misto.

## Elaborazione locale

L'OCR viene eseguito localmente: nessun documento viene caricato su servizi
cloud. Il PDF originale viene solo letto; i blocchi PDF e Markdown intermedi
sono conservati in una sottocartella `.gdlex_ocr_*` nella cartella di output.

Il Markdown prodotto è ottimizzato per l'uso con LLM e sistemi RAG. Le
immagini embedded e i relativi payload base64 non vengono inclusi: la loro
posizione nel documento viene conservata tramite un placeholder testuale
breve. Un controllo aggiuntivo rimuove eventuali payload residui prima
dell'unione dei blocchi.

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
