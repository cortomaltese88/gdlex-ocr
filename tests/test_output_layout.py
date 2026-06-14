"""Offline tests for standard OCR output paths."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.output_layout import build_output_layout


class OutputLayoutTest(unittest.TestCase):
    def test_standard_names_and_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_dir = root / "output"
            layout = build_output_layout(
                root / "Fascicolo civile.PDF",
                output_dir,
            )

            self.assertEqual(
                output_dir / "Fascicolo civile_ocr.md",
                layout["markdown"],
            )
            self.assertEqual(
                output_dir / "Fascicolo civile_ocr_index.md",
                layout["index_markdown"],
            )
            self.assertEqual(
                output_dir / "Fascicolo civile_searchable.pdf",
                layout["searchable_pdf"],
            )
            self.assertEqual(output_dir / "run.log", layout["run_log"])
            self.assertEqual(
                output_dir / "manifest.json",
                layout["manifest"],
            )

    def test_does_not_create_files_or_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "missing-output"
            layout = build_output_layout(Path(td) / "input.pdf", output_dir)

            self.assertFalse(output_dir.exists())
            self.assertTrue(all(not path.exists() for path in layout.values()))
