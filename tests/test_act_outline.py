"""Offline tests for the experimental Markdown act index."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.act_outline import (
    extract_act_titles,
    normalize_title,
    write_act_index,
)


SYNTHETIC_MARKDOWN = """\
# Fascicolo OCR

<!-- Blocco 1: pagine originali 1-3 -->

## Blocco 1 - Pagine 1-3

# PROCURA DELLA REPUBBLICA

## Annotazione   di P.G. ##

Pagina 1 di 3

Il presente decreto viene trasmesso alle parti.

<!-- Blocco 2: pagine originali 4-6 -->

## Blocco 2 - Pagine 4-6

**VERBALE DI SOMMARIE INFORMAZIONI**

Verbale di sommarie informazioni

<!-- Blocco 3: pagine originali 7-9 -->

## Blocco 3 - Pagine 7-9

### Richiesta di archiviazione
"""


class ExtractActTitlesTest(unittest.TestCase):
    def test_extracts_titles_with_block_start_pages(self) -> None:
        entries = extract_act_titles(SYNTHETIC_MARKDOWN)

        self.assertEqual(
            [
                ("Annotazione di P.G", 1, 1),
                ("VERBALE DI SOMMARIE INFORMAZIONI", 4, 2),
                ("Richiesta di archiviazione", 7, 3),
            ],
            [(entry.title, entry.page, entry.block) for entry in entries],
        )

    def test_ignores_generic_lines_and_body_sentences(self) -> None:
        titles = [entry.title for entry in extract_act_titles(SYNTHETIC_MARKDOWN)]

        self.assertNotIn("PROCURA DELLA REPUBBLICA", titles)
        self.assertNotIn("Pagina 1 di 3", titles)
        self.assertFalse(any(title.startswith("Il presente") for title in titles))

    def test_deduplicates_equivalent_titles(self) -> None:
        titles = [entry.title for entry in extract_act_titles(SYNTHETIC_MARKDOWN)]

        self.assertEqual(
            1,
            sum("verbale di sommarie informazioni" in title.casefold()
                for title in titles),
        )

    def test_normalizes_markdown_noise_and_truncates(self) -> None:
        dirty = "## **Decreto**   " + ("x" * 120) + " | �"

        normalized = normalize_title(dirty)

        self.assertTrue(normalized.startswith("Decreto x"))
        self.assertLessEqual(len(normalized), 100)
        self.assertNotIn("|", normalized)
        self.assertNotIn("�", normalized)


class WriteActIndexTest(unittest.TestCase):
    def test_creates_experimental_audit_index_without_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            markdown_path = root / "fascicolo_ocr.md"
            markdown_path.write_text(SYNTHETIC_MARKDOWN, encoding="utf-8")

            result = write_act_index(markdown_path)

            self.assertEqual(
                [
                    "Annotazione di P.G",
                    "VERBALE DI SOMMARIE INFORMAZIONI",
                    "Richiesta di archiviazione",
                ],
                [entry.title for entry in result.entries],
            )
            self.assertTrue(result.index_path.is_file())
            index = result.index_path.read_text(encoding="utf-8")
            self.assertIn("Indice atti sperimentale", index)
            self.assertIn("non genera segnalibri PDF", index)
            self.assertIn("inizio del blocco Docling", index)
            self.assertIn("| Richiesta di archiviazione | 7 | 3 |", index)

    def test_creates_index_without_reliable_titles(self) -> None:
        markdown = """\
## Blocco 1 - Pagine 1-3

PROCURA DELLA REPUBBLICA
Pagina 1

## Blocco 2 - Pagine 4-6

Testo ordinario senza denominazioni di atti.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            markdown_path = root / "fascicolo_ocr.md"
            markdown_path.write_text(markdown, encoding="utf-8")

            result = write_act_index(markdown_path)

            self.assertEqual((), result.entries)
            self.assertTrue(result.index_path.is_file())
            index = result.index_path.read_text(encoding="utf-8")
            self.assertIn("Pagina stimata (inizio blocco)", index)


if __name__ == "__main__":
    unittest.main()
