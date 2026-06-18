"""CLI tests for judgment analysis after synthetic PDF conversion."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import app
from gdlex_ocr.version import APP_VERSION


SYNTHETIC_CONDANNA = """\
# Sentenza sintetica

TRIBUNALE DI PADOVA
Sezione penale - in composizione monocratica
Sentenza n. 123/2026
R.G. n. 456/2025

Il Giudice dott.ssa Maria Rossi ha pronunciato la seguente sentenza.
All'udienza del 18 giugno 2026 viene letto il dispositivo.

P.Q.M.
Dichiara l'imputato colpevole e lo condanna alla pena di mesi sei.
Motivazione riservata nel termine di 90 giorni.
"""

NON_SENTENZA = """\
# Appunti riunione

Questi appunti descrivono un'attivita' amministrativa interna.
Non contengono un dispositivo ne' dati di una sentenza.
"""


class _Signal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args) -> None:
        for callback in self._callbacks:
            callback(*args)


class _FakeWorker:
    markdown_text = SYNTHETIC_CONDANNA
    should_fail = False
    corrupt_manifest = False
    run_count = 0

    def __init__(
        self,
        pdf_path: str,
        output_dir: str,
        pages_per_block,
        profile,
        **kwargs,
    ) -> None:
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.log_message = _Signal()
        self.progress_changed = _Signal()
        self.completed = _Signal()
        self.failed = _Signal()
        self.cancelled = _Signal()

    def run(self) -> None:
        type(self).run_count += 1
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_message.emit("conversione sintetica")
        manifest_path = self.output_dir / "manifest.json"
        if self.should_fail:
            manifest_path.write_text(
                json.dumps(
                    {
                        "job": {"status": "failed"},
                        "outputs": {"manifest": str(manifest_path)},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.failed.emit("conversione fallita")
            return
        markdown_path = self.output_dir / f"{self.pdf_path.stem}_ocr.md"
        markdown_path.write_text(self.markdown_text, encoding="utf-8")
        if self.corrupt_manifest:
            manifest_path.write_text("{bad json", encoding="utf-8")
        else:
            manifest_path.write_text(
                json.dumps(
                    {
                        "job": {"status": "success"},
                        "outputs": {
                            "markdown": str(markdown_path),
                            "manifest": str(manifest_path),
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        self.completed.emit(str(markdown_path), str(self.output_dir), "0s", "1.0 pag/min")


class AppJudgmentPdfFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        _FakeWorker.markdown_text = SYNTHETIC_CONDANNA
        _FakeWorker.should_fail = False
        _FakeWorker.corrupt_manifest = False
        _FakeWorker.run_count = 0

    def test_pdf_flow_with_judgment_analysis_writes_separate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker", _FakeWorker
        ), patch(
            "app.QApplication",
            side_effect=AssertionError("GUI should not start for PDF CLI"),
        ):
            root = Path(temp_dir)
            pdf_path = root / "sentenza.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF synthetic")
            output = io.StringIO()

            with redirect_stdout(output):
                status = app.main(
                    [
                        str(pdf_path),
                        "--output",
                        str(output_dir),
                        "--analyze-judgment-after-conversion",
                    ]
                )

            self.assertEqual(0, status)
            summary = output_dir / app.JUDGMENT_ANALYSIS_FILENAME
            self.assertTrue(summary.is_file())
            text = summary.read_text(encoding="utf-8")
            self.assertIn("# Scheda sentenza", text)
            self.assertIn("- Autorità giudiziaria: TRIBUNALE DI PADOVA", text)
            self.assertIn("- Dispositivo: condanna", text)
            manifest = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            judgment = manifest["judgment_analysis"]
            self.assertTrue(judgment["enabled"])
            self.assertTrue(judgment["detected"])
            self.assertEqual(app.JUDGMENT_ANALYSIS_FILENAME, judgment["output_file"])
            self.assertIn("missing_fields", judgment)
            self.assertIn("warnings", judgment)
            for name in (
                "authority",
                "composition",
                "judge",
                "sentence_number",
                "proceeding_number",
                "hearing_or_decision_date",
                "motivation_type",
                "motivation_deadline",
                "deposit_date",
                "outcome",
            ):
                with self.subTest(name=name):
                    self.assertIn("value", judgment["fields"][name])
                    self.assertIn("confidence", judgment["fields"][name])
            serialized = json.dumps(judgment, ensure_ascii=False)
            self.assertNotIn("Dichiara l'imputato colpevole", serialized)
            self.assertNotIn("alla pena di mesi sei", serialized)
            self.assertEqual(
                SYNTHETIC_CONDANNA,
                (output_dir / "sentenza_ocr.md").read_text(encoding="utf-8"),
            )

    def test_pdf_flow_without_flag_does_not_write_judgment_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker", _FakeWorker
        ):
            root = Path(temp_dir)
            pdf_path = root / "sentenza.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF synthetic")
            output = io.StringIO()

            with redirect_stdout(output):
                status = app.main([str(pdf_path), "--output", str(output_dir)])

            self.assertEqual(0, status)
            self.assertFalse((output_dir / app.JUDGMENT_ANALYSIS_FILENAME).exists())
            self.assertTrue((output_dir / "sentenza_ocr.md").is_file())
            manifest = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("judgment_analysis", manifest)

    def test_failed_conversion_does_not_try_to_write_analysis(self) -> None:
        _FakeWorker.should_fail = True
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker", _FakeWorker
        ):
            root = Path(temp_dir)
            pdf_path = root / "sentenza.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF synthetic")
            error = io.StringIO()
            output = io.StringIO()

            with redirect_stderr(error), redirect_stdout(output):
                status = app.main(
                    [
                        str(pdf_path),
                        "--output",
                        str(output_dir),
                        "--analyze-judgment-after-conversion",
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("conversione fallita", error.getvalue())
            self.assertFalse((output_dir / app.JUDGMENT_ANALYSIS_FILENAME).exists())
            manifest = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("judgment_analysis", manifest)

    def test_non_judgment_markdown_writes_warning_summary(self) -> None:
        _FakeWorker.markdown_text = NON_SENTENZA
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker", _FakeWorker
        ):
            root = Path(temp_dir)
            pdf_path = root / "appunti.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF synthetic")
            output = io.StringIO()

            with redirect_stdout(output):
                status = app.main(
                    [
                        str(pdf_path),
                        "--output",
                        str(output_dir),
                        "--analyze-judgment-after-conversion",
                    ]
                )

            self.assertEqual(0, status)
            summary = output_dir / app.JUDGMENT_ANALYSIS_FILENAME
            self.assertIn(
                "Testo non riconosciuto come sentenza.",
                summary.read_text(encoding="utf-8"),
            )
            manifest = json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            judgment = manifest["judgment_analysis"]
            self.assertTrue(judgment["enabled"])
            self.assertFalse(judgment["detected"])
            self.assertEqual(app.JUDGMENT_ANALYSIS_FILENAME, judgment["output_file"])
            self.assertIn("il testo non sembra una sentenza", output.getvalue())

    def test_manifest_corrupt_json_in_pdf_flow(self) -> None:
        _FakeWorker.corrupt_manifest = True
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker", _FakeWorker
        ), patch(
            "app.QApplication",
            side_effect=AssertionError("GUI should not start for PDF CLI"),
        ):
            root = Path(temp_dir)
            pdf_path = root / "sentenza.pdf"
            output_dir = root / "output"
            pdf_path.write_bytes(b"%PDF synthetic")
            output = io.StringIO()

            with redirect_stdout(output):
                status = app.main(
                    [
                        str(pdf_path),
                        "--output",
                        str(output_dir),
                        "--analyze-judgment-after-conversion",
                    ]
                )

            self.assertEqual(0, status)
            summary = output_dir / app.JUDGMENT_ANALYSIS_FILENAME
            self.assertTrue(summary.is_file())
            text = summary.read_text(encoding="utf-8")
            self.assertIn("# Scheda sentenza", text)
            self.assertIn("manifest non aggiornato", output.getvalue())

    def test_offline_judgment_cli_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "app.OcrWorker",
            side_effect=AssertionError("PDF conversion should not run"),
        ):
            root = Path(temp_dir)
            input_path = root / "input.md"
            output_path = root / "out.md"
            input_path.write_text(SYNTHETIC_CONDANNA, encoding="utf-8")

            status = app.main(
                [
                    "--analyze-judgment",
                    str(input_path),
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(0, status)
            self.assertIn(
                "- Autorità giudiziaria: TRIBUNALE DI PADOVA",
                output_path.read_text(encoding="utf-8"),
            )

    def test_help_version_and_doctor_do_not_run_pdf_conversion(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), patch(
            "app.OcrWorker",
            side_effect=AssertionError("PDF conversion should not run"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                app.main(["--help"])

        self.assertEqual(0, ctx.exception.code)
        self.assertIn("--analyze-judgment-after-conversion", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output), patch(
            "app.OcrWorker",
            side_effect=AssertionError("PDF conversion should not run"),
        ):
            status = app.main(["--version"])

        self.assertEqual(0, status)
        self.assertEqual(f"{APP_VERSION}\n", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output), patch(
            "app.OcrWorker",
            side_effect=AssertionError("PDF conversion should not run"),
        ):
            status = app.main(["--doctor"])

        self.assertEqual(0, status)
        self.assertIn("gdlex-ocr --doctor", output.getvalue())


if __name__ == "__main__":
    unittest.main()
