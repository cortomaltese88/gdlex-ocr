"""Offline tests for content-aware act outlines."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.act_outline import (
    create_content_aware_outline,
    extract_act_titles,
    normalize_title,
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


def _synthetic_pdf(num_pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


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


class CreateContentAwareOutlineTest(unittest.TestCase):
    def test_creates_content_outline_and_audit_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf_path = root / "fascicolo.pdf"
            markdown_path = root / "fascicolo_ocr.md"
            pdf_path.write_bytes(_synthetic_pdf(9))
            markdown_path.write_text(SYNTHETIC_MARKDOWN, encoding="utf-8")

            result = create_content_aware_outline(
                pdf_path,
                markdown_path,
                block_size=3,
                total_pages=9,
            )

            reader = PdfReader(pdf_path)
            outline = reader.outline
            self.assertFalse(result.used_fallback)
            self.assertEqual(
                [
                    "Annotazione di P.G",
                    "VERBALE DI SOMMARIE INFORMAZIONI",
                    "Richiesta di archiviazione",
                ],
                [item.title for item in outline],
            )
            self.assertEqual(
                [0, 3, 6],
                [reader.get_destination_page_number(item) for item in outline],
            )
            self.assertTrue(result.index_path.is_file())
            index = result.index_path.read_text(encoding="utf-8")
            self.assertIn("Modalità outline: content-aware", index)
            self.assertIn("| Richiesta di archiviazione | 7 | 3 |", index)

    def test_uses_technical_fallback_without_reliable_titles(self) -> None:
        markdown = """\
## Blocco 1 - Pagine 1-3

PROCURA DELLA REPUBBLICA
Pagina 1

## Blocco 2 - Pagine 4-6

Testo ordinario senza denominazioni di atti.
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf_path = root / "fascicolo.pdf"
            markdown_path = root / "fascicolo_ocr.md"
            pdf_path.write_bytes(_synthetic_pdf(6))
            markdown_path.write_text(markdown, encoding="utf-8")

            result = create_content_aware_outline(
                pdf_path,
                markdown_path,
                block_size=3,
            )

            titles = [item.title for item in PdfReader(pdf_path).outline]
            self.assertTrue(result.used_fallback)
            self.assertEqual(2, len(titles))
            self.assertTrue(
                all(title.startswith("Fallback tecnico - Pagine") for title in titles)
            )
            index = result.index_path.read_text(encoding="utf-8")
            self.assertIn("Modalità outline: fallback tecnico", index)


if __name__ == "__main__":
    unittest.main()
