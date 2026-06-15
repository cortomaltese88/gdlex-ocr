"""Offline tests for standard OCR output paths."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.output_layout import (
    build_job_output_dir,
    build_output_layout,
    create_unique_output_dir,
    make_unique_output_dir,
)


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

    def test_input_without_extension(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "out"
            layout = build_output_layout(Path(td) / "fascicolo", output_dir)

            self.assertEqual(output_dir / "fascicolo_ocr.md", layout["markdown"])
            self.assertEqual(
                output_dir / "fascicolo_searchable.pdf", layout["searchable_pdf"]
            )

    def test_input_with_multiple_dots_uses_correct_stem(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "out"
            layout = build_output_layout(Path(td) / "doc.v2.pdf", output_dir)

            self.assertEqual(output_dir / "doc.v2_ocr.md", layout["markdown"])
            self.assertEqual(
                output_dir / "doc.v2_searchable.pdf", layout["searchable_pdf"]
            )

    def test_fixed_filenames_use_constants(self) -> None:
        from gdlex_ocr.output_layout import LOG_FILENAME, MANIFEST_FILENAME

        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "out"
            layout = build_output_layout(Path(td) / "doc.pdf", output_dir)

            self.assertEqual(output_dir / MANIFEST_FILENAME, layout["manifest"])
            self.assertEqual(output_dir / LOG_FILENAME, layout["run_log"])

    def test_structured_layout_uses_job_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output_root = root / "output"
            layout = build_output_layout(
                root / "Fascicolo civile.pdf",
                output_root,
                structured=True,
            )
            job_dir = output_root / "Fascicolo civile_ocr_job"

            self.assertEqual(
                job_dir / "Fascicolo civile_ocr.md",
                layout["markdown"],
            )
            self.assertEqual(job_dir / "run.log", layout["run_log"])
            self.assertEqual(job_dir / "manifest.json", layout["manifest"])
            self.assertFalse(job_dir.exists())

    def test_structured_layout_preserves_multiple_dots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            layout = build_output_layout(
                root / "atto.v2.final.pdf",
                root / "output",
                structured=True,
            )

            self.assertEqual(
                root / "output" / "atto.v2.final_ocr_job",
                layout["markdown"].parent,
            )
            self.assertEqual("atto.v2.final_ocr.md", layout["markdown"].name)

    def test_make_unique_output_dir_is_pure_and_progressive(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "sample_ocr_job"
            base.mkdir()
            (Path(td) / "sample_ocr_job_2").mkdir()

            result = make_unique_output_dir(base)

            self.assertEqual(Path(td) / "sample_ocr_job_3", result)
            self.assertFalse(result.exists())

    def test_create_unique_output_dir_never_reuses_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "sample_ocr_job"
            first = create_unique_output_dir(base)
            marker = first / "keep.txt"
            marker.write_text("existing", encoding="utf-8")
            second = create_unique_output_dir(base)

            self.assertEqual(base, first)
            self.assertEqual(Path(td) / "sample_ocr_job_2", second)
            self.assertEqual("existing", marker.read_text(encoding="utf-8"))

    def test_build_job_output_dir_does_not_create_any_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output_root = Path(td) / "missing"
            result = build_job_output_dir(
                Path(td) / "input con spazi.pdf",
                output_root,
            )

            self.assertEqual(output_root / "input con spazi_ocr_job", result)
            self.assertFalse(output_root.exists())
