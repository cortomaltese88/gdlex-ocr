"""Offline tests for the synthetic benchmark helper.

No real PDFs are read and no OCR subprocess is launched.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

from gdlex_ocr.profiles import PROFILES
from gdlex_ocr.version import APP_VERSION


def _load_benchmark_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "benchmark_synthetic.py"
    )
    spec = importlib.util.spec_from_file_location(
        "benchmark_synthetic_for_tests",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


benchmark = _load_benchmark_module()


class BenchmarkSyntheticTest(unittest.TestCase):
    def test_creates_searchable_pdf_with_extractable_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "synthetic_searchable.pdf"

            benchmark.create_searchable_pdf(pdf_path, pages=2)

            reader = PdfReader(pdf_path)
            self.assertEqual(2, len(reader.pages))
            extracted = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            self.assertIn("GD LEX OCR synthetic searchable page 1", extracted)
            self.assertIn("GD LEX OCR synthetic searchable page 2", extracted)

    def test_image_pdf_reports_missing_pillow_clearly(self) -> None:
        real_import_module = importlib.import_module

        def fake_import(name: str):
            if name.startswith("PIL."):
                raise ImportError(name)
            return real_import_module(name)

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "benchmark_synthetic_for_tests.importlib.import_module",
            side_effect=fake_import,
        ):
            with self.assertRaises(benchmark.OptionalDependencyError) as ctx:
                benchmark.create_image_like_pdf(
                    Path(tmpdir) / "synthetic_image.pdf",
                    pages=1,
                )

        self.assertIn("Pillow non disponibile", str(ctx.exception))
        self.assertIn("--cases searchable", str(ctx.exception))

    def test_run_benchmark_writes_json_for_searchable_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result_json = root / "results" / "benchmark.json"
            args = Namespace(
                output_dir=root,
                result_json=result_json,
                pages=2,
                runs=1,
                cases=("searchable",),
                profile="PDF già ricercabile",
                block_size=None,
                run_ocr=False,
                ocr_language="ita",
                ocr_timeout=30,
                ocr_jobs=None,
            )

            report = benchmark.run_benchmark(args)

            self.assertTrue(result_json.is_file())
            self.assertEqual(APP_VERSION, report["app_version"])
            self.assertEqual(
                PROFILES["PDF già ricercabile"].block_size,
                report["block_size"],
            )
            self.assertEqual(["searchable"], [
                result["case"] for result in report["results"]
            ])
            self.assertEqual(2, report["results"][0]["input"]["pages"])
            self.assertEqual(
                2,
                report["results"][0]["input"]["pages_with_text"],
            )


if __name__ == "__main__":
    unittest.main()
