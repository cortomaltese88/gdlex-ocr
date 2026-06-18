"""CLI tests for offline judgment Markdown analysis."""

from __future__ import annotations

import io
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

Depositata in cancelleria il 20 giugno 2026.
"""


class AppJudgmentCliTest(unittest.TestCase):
    def test_analyze_judgment_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.md"
            output_path = Path(temp_dir) / "sentenza_analysis.md"
            input_path.write_text(SYNTHETIC_CONDANNA, encoding="utf-8")

            with patch(
                "app.QApplication",
                side_effect=AssertionError("GUI should not start for analysis"),
            ):
                status = app.main(
                    [
                        "--analyze-judgment",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(0, status)
            output = output_path.read_text(encoding="utf-8")
            self.assertIn("# Scheda sentenza", output)
            self.assertIn("- Autorità giudiziaria: TRIBUNALE DI PADOVA", output)
            self.assertIn("- Dispositivo: condanna", output)
            self.assertNotIn("# Sentenza sintetica", output)

    def test_analyze_judgment_prepend_writes_summary_and_original(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.md"
            output_path = Path(temp_dir) / "sentenza_con_scheda.md"
            input_path.write_text(SYNTHETIC_CONDANNA, encoding="utf-8")

            status = app.main(
                [
                    "--analyze-judgment",
                    str(input_path),
                    "--output",
                    str(output_path),
                    "--prepend",
                ]
            )

            self.assertEqual(0, status)
            output = output_path.read_text(encoding="utf-8")
            self.assertTrue(output.startswith("# Scheda sentenza"))
            self.assertIn("- Dispositivo: condanna", output)
            self.assertIn("\n---\n\n# Sentenza sintetica", output)
            self.assertEqual(
                SYNTHETIC_CONDANNA,
                input_path.read_text(encoding="utf-8"),
            )

    def test_analyze_judgment_rejects_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "missing.md"
            output_path = Path(temp_dir) / "out.md"
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main(
                    [
                        "--analyze-judgment",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("input Markdown non trovato", error.getvalue())
            self.assertFalse(output_path.exists())

    def test_analyze_judgment_requires_output(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.main(["--analyze-judgment", "input.md"])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("--output", error.getvalue())
        self.assertIn("obbligatorio", error.getvalue())

    def test_analyze_judgment_rejects_directory_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main(
                    [
                        "--analyze-judgment",
                        temp_dir,
                        "--output",
                        str(Path(temp_dir) / "out.md"),
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("input Markdown non e' un file", error.getvalue())

    def test_analyze_judgment_rejects_unwritable_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.md"
            output_path = Path(temp_dir) / "missing" / "out.md"
            input_path.write_text(SYNTHETIC_CONDANNA, encoding="utf-8")
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main(
                    [
                        "--analyze-judgment",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("impossibile scrivere l'output Markdown", error.getvalue())

    def test_output_same_as_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "sentenza.md"
            input_path.write_text(SYNTHETIC_CONDANNA, encoding="utf-8")
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main(
                    [
                        "--analyze-judgment",
                        str(input_path),
                        "--output",
                        str(input_path),
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("coincidere", error.getvalue())
            self.assertEqual(
                SYNTHETIC_CONDANNA,
                input_path.read_text(encoding="utf-8"),
            )

    def test_path_with_spaces_and_accents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            nested = Path(temp_dir) / "cartella con spazi"
            nested.mkdir()
            input_path = nested / "sentenza àè.md"
            output_path = nested / "analisi àè.md"
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
            output = output_path.read_text(encoding="utf-8")
            self.assertIn("# Scheda sentenza", output)
            self.assertIn("- Dispositivo: condanna", output)

    def test_non_utf8_input_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "latin1.md"
            output_path = Path(temp_dir) / "out.md"
            input_path.write_bytes(b"Sentenza c\xe0sa \x80 testo")
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main(
                    [
                        "--analyze-judgment",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertNotEqual(0, status)
            self.assertIn("UTF-8", error.getvalue())
            self.assertFalse(output_path.exists())

    def test_help_version_and_doctor_do_not_run_analysis(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), patch(
            "app.analyze_judgment_markdown",
            side_effect=AssertionError("analysis should not run for --version"),
        ):
            status = app.main(["--version"])

        self.assertEqual(0, status)
        self.assertEqual(f"{APP_VERSION}\n", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output), patch(
            "app.analyze_judgment_markdown",
            side_effect=AssertionError("analysis should not run for --doctor"),
        ):
            status = app.main(["--doctor"])

        self.assertEqual(0, status)
        self.assertIn("gdlex-ocr --doctor", output.getvalue())

        output = io.StringIO()
        with redirect_stdout(output), patch(
            "app.analyze_judgment_markdown",
            side_effect=AssertionError("analysis should not run for --help"),
        ):
            with self.assertRaises(SystemExit) as ctx:
                app.main(["--help"])

        self.assertEqual(0, ctx.exception.code)
        self.assertIn("--analyze-judgment INPUT.md", output.getvalue())


if __name__ == "__main__":
    unittest.main()
