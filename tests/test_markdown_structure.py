"""Offline tests for conservative Markdown heading promotion."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from gdlex_ocr.bookmarks import select_bookmarks
from gdlex_ocr.markdown_structure import add_conservative_headings


class MarkdownStructureTest(unittest.TestCase):
    def test_promotes_isolated_uppercase_titles(self) -> None:
        markdown = (
            "Testo introduttivo.\n\n"
            "CAPITOLO PRIMO\n\n"
            "Contenuto del capitolo.\n\n"
            "SEZIONE II - DISPOSIZIONI FINALI\n\n"
            "Altro testo.\n"
        )

        result = add_conservative_headings(markdown)

        self.assertIn("## CAPITOLO PRIMO", result.markdown)
        self.assertIn("## SEZIONE II - DISPOSIZIONI FINALI", result.markdown)
        self.assertEqual(2, result.headings_added)

    def test_promotes_articles_to_level_three(self) -> None:
        markdown = (
            "Premessa.\n\n"
            "Art. 1 - Oggetto\n\n"
            "Testo dell'articolo.\n\n"
            "Articolo 2 - Ambito di applicazione\n\n"
            "Testo seguente.\n"
        )

        result = add_conservative_headings(markdown)

        self.assertIn("### Art. 1 - Oggetto", result.markdown)
        self.assertIn("### Articolo 2 - Ambito di applicazione", result.markdown)
        self.assertEqual(2, result.headings_added)

    def test_promotes_numbered_titles_to_level_three(self) -> None:
        markdown = (
            "\n1. Oggetto\n\n"
            "Testo.\n\n"
            "1.1 Ambito di applicazione\n\n"
            "Testo.\n\n"
            "I. Disposizioni generali\n\n"
            "Testo.\n\n"
            "A) Definizioni\n\n"
        )

        result = add_conservative_headings(markdown)

        self.assertIn("### 1. Oggetto", result.markdown)
        self.assertIn("### 1.1 Ambito di applicazione", result.markdown)
        self.assertIn("### I. Disposizioni generali", result.markdown)
        self.assertIn("### A) Definizioni", result.markdown)
        self.assertEqual(4, result.headings_added)

    def test_does_not_promote_long_ordinary_sentence(self) -> None:
        sentence = (
            "Questa è una frase ordinaria sufficientemente lunga che descrive "
            "il contenuto sostanziale del documento e termina con un punto."
        )
        result = add_conservative_headings(f"\n{sentence}\n\n")

        self.assertEqual(f"\n{sentence}\n\n", result.markdown)
        self.assertEqual(0, result.headings_added)

    def test_does_not_promote_urls_emails_hashes_or_base64(self) -> None:
        hash_value = "a" * 64
        payload = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVo=" * 3
        markdown = (
            "\nHTTP://EXAMPLE.COM/CAPITOLO\n\n"
            "INFO@EXAMPLE.COM\n\n"
            f"{hash_value}\n\n"
            f"{payload}\n\n"
            "data:image/png;base64,QUJD\n"
        )

        result = add_conservative_headings(markdown)

        self.assertEqual(markdown, result.markdown)
        self.assertEqual(0, result.headings_added)

    def test_preserves_fenced_code_indented_code_and_tables(self) -> None:
        markdown = (
            "```text\n"
            "CAPITOLO NEL CODICE\n"
            "```\n\n"
            "    CAPITOLO INDENTATO\n\n"
            "| CAPITOLO | VALORE |\n"
            "|---|---|\n"
            "| SEZIONE | TESTO |\n"
        )

        result = add_conservative_headings(markdown)

        self.assertEqual(markdown, result.markdown)
        self.assertEqual(0, result.headings_added)

    def test_preserves_quotes_and_lists(self) -> None:
        markdown = (
            "> CAPITOLO CITATO\n\n"
            "- CAPITOLO IN ELENCO\n\n"
            "* SEZIONE IN ELENCO\n"
        )

        result = add_conservative_headings(markdown)

        self.assertEqual(markdown, result.markdown)
        self.assertEqual(0, result.headings_added)

    def test_existing_headings_are_not_duplicated(self) -> None:
        markdown = (
            "## CAPITOLO PRIMO\n\n"
            "CAPITOLO PRIMO\n\n"
            "Testo.\n"
        )

        result = add_conservative_headings(markdown)

        self.assertEqual(markdown, result.markdown)
        self.assertEqual(0, result.headings_added)

    def test_promoted_headings_feed_bookmark_selection(self) -> None:
        markdown = (
            "<!-- Blocco 1: pagine originali 1-2 -->\n\n"
            "## Blocco 1 - Pagine 1-2\n\n"
            "CAPITOLO I - PRINCIPI GENERALI\n\n"
            "Testo ordinario.\n"
        )
        structured = add_conservative_headings(markdown)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown_path = root / "source.md"
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            writer.add_blank_page(width=595, height=842)
            with pdf.open("wb") as output:
                writer.write(output)
            markdown_path.write_text(structured.markdown, encoding="utf-8")

            bookmarks = select_bookmarks(
                pdf,
                markdown_path,
                block_size=2,
                total_pages=2,
            )

        self.assertEqual(1, structured.headings_added)
        self.assertEqual("markdown_headings", bookmarks.strategy)
        self.assertEqual("CAPITOLO I - PRINCIPI GENERALI", bookmarks.items[0].title)


if __name__ == "__main__":
    unittest.main()
