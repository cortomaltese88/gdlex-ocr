# GD LEX OCR

[README italiano](README.md)

Local-first OCR and Markdown conversion for legal PDF workflows.

GD LEX OCR is a desktop application for converting legal PDF bundles and
documents into Markdown while keeping the workflow local, inspectable and
repeatable. It combines Docling-based PDF conversion, optional OCRmyPDF /
Tesseract searchable-PDF generation, processing profiles and an audit manifest
for each job.

## What It Does

- Converts PDF files into Markdown for review, LLM and RAG workflows.
- Splits large PDFs into controlled processing blocks.
- Preserves the original PDF as read-only input.
- Can create a searchable PDF through a local OCR backend.
- Writes `manifest.json` and `run.log` next to the generated outputs.
- Offers a PySide6 desktop GUI with local diagnostics.

## Why Local-First

The application does not upload documents to cloud services. PDF input is read
locally, and generated Markdown, searchable PDFs, logs and manifests stay in
the selected output folder.

Docling and its upstream dependencies may download models on first use. Those
downloads, caches and licenses are controlled by the upstream projects and
should be reviewed before distributing a bundled runtime.

## Installation via GD LEX APT Repository

On Debian/Ubuntu amd64 clients:

```bash
curl -fsSL https://cortomaltese88.github.io/gdlex-apt-repo/keys/gdlex-archive-keyring.asc \
  | gpg --dearmor \
  | sudo tee /usr/share/keyrings/gdlex-archive-keyring.gpg >/dev/null

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gdlex-archive-keyring.gpg] https://cortomaltese88.github.io/gdlex-apt-repo stable main" \
  | sudo tee /etc/apt/sources.list.d/gdlex.list

sudo apt update
sudo apt install gdlex-ocr
```

Do not use `trusted=yes`; the repository is intended to be verified through
the configured keyring.

## Quick Start

```bash
gdlex-ocr
```

To prepare or refresh the user virtual environment:

```bash
gdlex-ocr --setup-venv
```

To run diagnostics without opening the GUI:

```bash
gdlex-ocr --doctor
```

To check the installed version:

```bash
gdlex-ocr --version
```

Advanced OCR options:

- `--ocr-timeout SECONDS`: sets the maximum OCRmyPDF timeout; default is 1800
  seconds.
- `--ocr-jobs N`: passes the number of parallel jobs to OCRmyPDF; when omitted,
  OCRmyPDF keeps its default behavior.

The GUI exposes the same OCRmyPDF timeout and jobs controls in the OCR backend
settings and persists them with `QSettings`, without saving input paths or
auto-derived output paths. OCRmyPDF stdout and stderr are streamed to the GUI
log and `run.log` in realtime while keeping timeout and error handling active.

Judgment analysis after PDF-to-Markdown conversion:

```bash
gdlex-ocr judgment.pdf --output output/ --analyze-judgment-after-conversion
```

This creates `sentenza_analysis.md` next to the main Markdown file without
modifying it. It works locally on the Markdown just generated and does not
calculate final appeal deadlines.

The same judgment analysis is also available from the GUI through a dedicated
checkbox.

Judgment analysis from already-generated Markdown:

```bash
gdlex-ocr --analyze-judgment judgment.md --output judgment_analysis.md
gdlex-ocr --analyze-judgment judgment.md --output judgment_with_card.md --prepend
```

This mode works offline on an existing Markdown file, does not run OCR, does
not invoke Docling and does not modify the input. The card is heuristic: it
does not calculate final appeal deadlines and does not replace professional
review.

For a repeatable local-first synthetic benchmark, without real documents:

```bash
.venv/bin/python scripts/benchmark_synthetic.py
```

Synthetic PDFs, temporary chunks and runtime results are generated under
`tmp/benchmark-synthetic/`. See [BENCHMARK.md](BENCHMARK.md) for options and
limitations. The benchmark also includes coverage for the `Fascicolo legale`
profile.

If a development wrapper in `~/.local/bin/gdlex-ocr` shadows the packaged
binary, run `/usr/bin/gdlex-ocr --doctor` to inspect the APT-installed copy.

## Profiles

The GUI provides six processing profiles:

| Profile | Main Use |
|---|---|
| Veloce | Faster conversion with larger blocks and minimal enrichment. |
| Bilanciato | Default profile for common legal bundles. |
| Accurato testo | More conservative text extraction; can create a searchable PDF first. |
| PDF già ricercabile | Uses an existing text layer and disables Docling OCR. |
| Fascicolo legale | Conservative long-bundle profile; keeps OCR optional and Markdown structured. |
| Accurato | Enables picture and chart enrichment for mixed content. |

OCR backends include OCRmyPDF/Tesseract for searchable PDFs, a configurable
external command, and Docling internal/transitive OCR components such as
RapidOCR when enabled by the selected profile and upstream configuration.

## Manifest and Audit Trail

Each completed or failed job writes a `manifest.json` with app identity, job
UUID, timestamps, input path, input SHA-256, page count, selected profile,
block statistics, OCR backend metadata, output paths, warnings and errors.

The manifest helps verify which input was processed and which outputs were
created without committing sensitive files to the repository.

## OCR Limitations

OCR output must be reviewed by a human, especially in legal work. Accuracy can
drop with low-quality scans, skewed pages, handwriting, stamps, complex
tables, multi-column layouts, rotated pages, image-heavy attachments and very
large bundles.

Always compare generated Markdown and searchable PDFs with the original
document before using them for legal drafting, filings, evidence review or
professional advice.

## Third-Party Credits

GD LEX OCR uses Docling, ONNX Runtime, PySide6 and pypdf as Python
dependencies. OCRmyPDF, Tesseract and language data are optional system tools.
Docling may use transitive OCR components such as RapidOCR.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for license notes and
upstream verification guidance.

## License

GD LEX OCR project code is released under the MIT license; see [LICENSE](LICENSE).
Third-party components keep their own licenses.

## Roadmap

See [ROADMAP.md](ROADMAP.md).
