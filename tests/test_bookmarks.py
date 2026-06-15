"""Offline tests for progressive bookmark selection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from gdlex_ocr.bookmarks import select_bookmarks, write_bookmark_index


def _write_pdf(path: Path, pages: int, outline: bool = False) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if outline:
        writer.add_outline_item("Titolo nativo", 2)
    with path.open("wb") as output:
        writer.write(output)


class BookmarkSelectionTest(unittest.TestCase):
    def test_pdf_outline_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown = root / "source.md"
            _write_pdf(pdf, 5, outline=True)
            markdown.write_text(
                "<!-- Blocco 1: pagine originali 1-5 -->\n"
                "# Heading Markdown\n",
                encoding="utf-8",
            )

            result = select_bookmarks(
                pdf,
                markdown,
                block_size=2,
                total_pages=5,
            )

        self.assertEqual("pdf_outline", result.strategy)
        self.assertFalse(result.fallback)
        self.assertEqual(
            [("Titolo nativo", 2)],
            [(item.title, item.page_index) for item in result.items],
        )

    def test_markdown_headings_are_deduplicated_with_block_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown = root / "source.md"
            _write_pdf(pdf, 6)
            markdown.write_text(
                "<!-- Blocco 1: pagine originali 1-3 -->\n"
                "## Blocco 1 - Pagine 1-3\n"
                "# CAPITOLO PRIMO\n"
                "# CAPITOLO PRIMO\n"
                "<!-- Blocco 2: pagine originali 4-6 -->\n"
                "# CAPITOLO PRIMO\n"
                "### Articolo 2 - Disposizioni finali\n",
                encoding="utf-8",
            )

            result = select_bookmarks(
                pdf,
                markdown,
                block_size=3,
                total_pages=6,
            )

        self.assertEqual("markdown_headings", result.strategy)
        self.assertEqual(
            [("CAPITOLO PRIMO", 0), ("Articolo 2 - Disposizioni finali", 3)],
            [(item.title, item.page_index) for item in result.items],
        )

    def test_text_heuristics_are_conservative_and_ignore_base64(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown = root / "source.md"
            _write_pdf(pdf, 4)
            markdown.write_text(
                "<!-- Blocco 1: pagine originali 1-2 -->\n"
                "CAPITOLO I - PRINCIPI GENERALI\n"
                "Questa è una normale frase del corpo del documento.\n"
                "data:image/png;base64,AAAA\n"
                "<!-- Blocco 2: pagine originali 3-4 -->\n"
                "ART. 7 - Entrata in vigore\n",
                encoding="utf-8",
            )

            result = select_bookmarks(
                pdf,
                markdown,
                block_size=2,
                total_pages=4,
            )

        self.assertEqual("text_heuristics", result.strategy)
        self.assertEqual(
            [("CAPITOLO I - PRINCIPI GENERALI", 0),
             ("ART. 7 - Entrata in vigore", 2)],
            [(item.title, item.page_index) for item in result.items],
        )

    def test_page_chunks_are_only_final_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown = root / "source.md"
            _write_pdf(pdf, 5)
            markdown.write_text(
                "<!-- Blocco 1: pagine originali 1-5 -->\n"
                "Testo ordinario senza titoli affidabili.\n",
                encoding="utf-8",
            )

            result = select_bookmarks(
                pdf,
                markdown,
                block_size=2,
                total_pages=5,
            )

        self.assertEqual("page_chunks", result.strategy)
        self.assertTrue(result.fallback)
        self.assertEqual(3, len(result.items))
        self.assertTrue(result.warnings)

    def test_index_records_selected_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf = root / "source.pdf"
            markdown = root / "source.md"
            _write_pdf(pdf, 2)
            markdown.write_text(
                "<!-- Blocco 1: pagine originali 1-2 -->\n"
                "# SEZIONE PRIMA\n",
                encoding="utf-8",
            )
            result = select_bookmarks(
                pdf,
                markdown,
                block_size=2,
                total_pages=2,
            )

            index_path = write_bookmark_index(markdown, result)
            index = index_path.read_text(encoding="utf-8")

        self.assertIn("`markdown_headings`", index)
        self.assertIn("| SEZIONE PRIMA | 1 |", index)


if __name__ == "__main__":
    unittest.main()
