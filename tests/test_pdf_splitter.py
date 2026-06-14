"""Offline tests for PDF page counting and splitting."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.pdf_splitter import count_pdf_pages, split_pdf


class PdfSplitterTest(unittest.TestCase):
    def test_count_and_split_synthetic_pdf_without_modifying_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "synthetic.pdf"
            blocks_directory = root / "blocks"
            self._create_blank_pdf(source, page_count=5)
            original_bytes = source.read_bytes()

            self.assertEqual(5, count_pdf_pages(source))
            blocks = split_pdf(source, blocks_directory, pages_per_block=2)

            self.assertEqual(original_bytes, source.read_bytes())
            self.assertEqual(
                [(1, 1, 2), (2, 3, 4), (3, 5, 5)],
                [
                    (block.index, block.start_page, block.end_page)
                    for block in blocks
                ],
            )
            self.assertEqual([2, 2, 1], [block.page_count for block in blocks])
            for block in blocks:
                with self.subTest(block=block.index):
                    self.assertEqual(blocks_directory, block.path.parent)
                    self.assertTrue(block.path.is_file())
                    self.assertEqual(
                        block.page_count,
                        len(PdfReader(block.path).pages),
                    )

    @staticmethod
    def _create_blank_pdf(path: Path, page_count: int) -> None:
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=595, height=842)
        with path.open("wb") as output:
            writer.write(output)


if __name__ == "__main__":
    unittest.main()
