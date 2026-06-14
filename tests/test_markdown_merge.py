"""Smoke tests for deterministic Markdown block merging."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.markdown_merge import MarkdownBlock, merge_markdown


class MarkdownMergeTest(unittest.TestCase):
    def test_merge_creates_output_with_page_headers_in_block_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "first.md"
            second = root / "second.md"
            first.write_text("Contenuto primo blocco\n", encoding="utf-8")
            second.write_text("Contenuto secondo blocco\n", encoding="utf-8")
            destination = root / "merged" / "final.md"

            result = merge_markdown(
                [
                    MarkdownBlock(2, 3, 4, second),
                    MarkdownBlock(1, 1, 2, first),
                ],
                destination,
                "synthetic.pdf",
            )
            merged = result.read_text(encoding="utf-8")

            self.assertEqual(destination, result)
            self.assertTrue(result.is_file())
            self.assertIn("## Blocco 1 - Pagine 1-2", merged)
            self.assertIn("## Blocco 2 - Pagine 3-4", merged)
            self.assertIn(
                "<!-- Blocco 1: pagine originali 1-2 -->",
                merged,
            )
            self.assertLess(
                merged.index("Contenuto primo blocco"),
                merged.index("Contenuto secondo blocco"),
            )


if __name__ == "__main__":
    unittest.main()
