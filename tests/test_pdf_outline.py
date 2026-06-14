"""Offline tests for PDF outline (bookmark) generation.

Creates synthetic PDFs using pypdf; no real OCR, no user PDFs.
"""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.pdf_outline import add_technical_fallback_bookmarks


def _synthetic_pdf(num_pages: int) -> bytes:
    """Return bytes of a minimal valid PDF with *num_pages* blank pages."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class AddBlockBookmarksTest(unittest.TestCase):
    def test_bookmarks_are_added(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(_synthetic_pdf(10))

            add_technical_fallback_bookmarks(pdf_path, block_size=3)

            outline = PdfReader(pdf_path).outline
            # ceil(10/3) = 4 entries: [1-3, 4-6, 7-9, 10-10]
            self.assertEqual(4, len(outline))

    def test_bookmark_titles_contain_page_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(_synthetic_pdf(6))

            add_technical_fallback_bookmarks(pdf_path, block_size=3)

            outline = PdfReader(pdf_path).outline
            self.assertEqual(2, len(outline))
            self.assertTrue(outline[0].title.startswith("Fallback tecnico"))
            self.assertIn("1", outline[0].title)
            self.assertIn("3", outline[0].title)
            self.assertIn("4", outline[1].title)
            self.assertIn("6", outline[1].title)

    def test_single_block_produces_one_bookmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(_synthetic_pdf(5))

            add_technical_fallback_bookmarks(pdf_path, block_size=10)

            outline = PdfReader(pdf_path).outline
            self.assertEqual(1, len(outline))

    def test_pdf_is_still_valid_and_page_count_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(_synthetic_pdf(8))

            add_technical_fallback_bookmarks(pdf_path, block_size=4)

            reader = PdfReader(pdf_path)
            self.assertEqual(8, len(reader.pages))

    def test_no_leftover_tmp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf_path.write_bytes(_synthetic_pdf(4))

            add_technical_fallback_bookmarks(pdf_path, block_size=2)

            tmp = pdf_path.with_suffix(".tmp_outline.pdf")
            self.assertFalse(tmp.exists())

    def test_invalid_block_size_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            add_technical_fallback_bookmarks(
                Path("/tmp/nonexistent.pdf"),
                block_size=0,
            )

    def test_total_pages_limits_bookmarks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            # PDF has 10 pages but only the first 6 belong to the source.
            pdf_path.write_bytes(_synthetic_pdf(10))

            add_technical_fallback_bookmarks(
                pdf_path,
                block_size=3,
                total_pages=6,
            )

            outline = PdfReader(pdf_path).outline
            # Only 6 pages → [1-3, 4-6] = 2 entries
            self.assertEqual(2, len(outline))


if __name__ == "__main__":
    unittest.main()
