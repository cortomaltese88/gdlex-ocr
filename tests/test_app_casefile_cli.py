"""CLI tests for casefile folder analysis."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import app


def _make_synthetic_casefile(root: Path) -> None:
    """Create a minimal synthetic casefile folder with a fake PDF and index."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "atto_citazione.pdf").write_bytes(b"%PDF-1.4 fake")
    (root / "comparsa_risposta.pdf").write_bytes(b"%PDF-1.4 fake2")
    index = root / "indice_fascicolo.html"
    index.write_text(
        "<html><body><table>"
        "<tr><td>1</td><td>atto_citazione.pdf</td></tr>"
        "<tr><td>2</td><td>comparsa_risposta.pdf</td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )


class AppCasefileCliTest(unittest.TestCase):
    def test_analyze_casefile_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            _make_synthetic_casefile(case_dir)

            stdout = io.StringIO()
            with redirect_stdout(stdout), patch(
                "app.QApplication",
                side_effect=AssertionError("GUI should not start"),
            ):
                status = app.main([
                    "--analyze-casefile", str(case_dir),
                    "--output", str(out_dir),
                ])

            self.assertEqual(0, status)

            json_path = out_dir / "fascicolo_index.json"
            md_path = out_dir / "fascicolo_index.md"
            units_csv_path = out_dir / "fascicolo_unita.csv"
            merge_json_path = out_dir / "fascicolo_merge_plan.json"
            merge_csv_path = out_dir / "fascicolo_merge_plan.csv"
            merge_md_path = out_dir / "fascicolo_merge_plan.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue(units_csv_path.exists())
            self.assertTrue(merge_json_path.exists())
            self.assertTrue(merge_csv_path.exists())
            self.assertTrue(merge_md_path.exists())

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("summary", payload)

            md_content = md_path.read_text(encoding="utf-8")
            self.assertIn("# Indice fascicolo", md_content)

            printed = stdout.getvalue()
            self.assertIn("fascicolo_index.json", printed)
            self.assertIn("fascicolo_index.md", printed)
            self.assertIn("fascicolo_unita.csv", printed)
            self.assertIn("fascicolo_merge_plan.json", printed)
            self.assertIn("fascicolo_merge_plan.csv", printed)
            self.assertIn("fascicolo_merge_plan.md", printed)

    def test_analyze_casefile_requires_output(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.main(["--analyze-casefile", "/tmp/some_folder"])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("--output", error.getvalue())
        self.assertIn("obbligatorio", error.getvalue())

    def test_analyze_casefile_rejects_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "non_esiste"
            out_dir = Path(temp_dir) / "output"
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main([
                    "--analyze-casefile", str(missing),
                    "--output", str(out_dir),
                ])

            self.assertNotEqual(0, status)
            self.assertIn("cartella non trovata", error.getvalue())

    def test_analyze_casefile_rejects_file_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "not_a_dir.txt"
            file_path.write_text("hello", encoding="utf-8")
            out_dir = Path(temp_dir) / "output"
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main([
                    "--analyze-casefile", str(file_path),
                    "--output", str(out_dir),
                ])

            self.assertNotEqual(0, status)
            self.assertIn("non e' una cartella", error.getvalue())

    def test_analyze_casefile_rejects_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            _make_synthetic_casefile(case_dir)
            out_file = Path(temp_dir) / "existing_file.txt"
            out_file.write_text("occupied", encoding="utf-8")
            error = io.StringIO()

            with redirect_stderr(error):
                status = app.main([
                    "--analyze-casefile", str(case_dir),
                    "--output", str(out_file),
                ])

            self.assertNotEqual(0, status)
            self.assertIn("e' un file", error.getvalue())

    def test_analyze_casefile_rejects_conflicting_pdf_input(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.main([
                "--analyze-casefile", "/tmp/some_folder",
                "--output", "/tmp/out",
                "some.pdf",
            ])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("input_pdf", error.getvalue())

    def test_analyze_casefile_rejects_conflicting_judgment_mode(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as ctx:
            app.main([
                "--analyze-casefile", "/tmp/some_folder",
                "--analyze-judgment", "input.md",
                "--output", "/tmp/out",
            ])

        self.assertEqual(2, ctx.exception.code)
        self.assertIn("--analyze-judgment", error.getvalue())

    def test_analyze_casefile_output_no_absolute_path_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            _make_synthetic_casefile(case_dir)

            app.main([
                "--analyze-casefile", str(case_dir),
                "--output", str(out_dir),
            ])

            json_text = (out_dir / "fascicolo_index.json").read_text(
                encoding="utf-8",
            )
            md_text = (out_dir / "fascicolo_index.md").read_text(
                encoding="utf-8",
            )
            units_csv_text = (out_dir / "fascicolo_unita.csv").read_text(
                encoding="utf-8",
            )
            merge_text = "".join(
                (out_dir / name).read_text(encoding="utf-8-sig")
                for name in (
                    "fascicolo_merge_plan.json",
                    "fascicolo_merge_plan.csv",
                    "fascicolo_merge_plan.md",
                )
            )

            self.assertNotIn(temp_dir, json_text)
            self.assertNotIn(temp_dir, md_text)
            self.assertNotIn(temp_dir, units_csv_text)
            self.assertNotIn(temp_dir, merge_text)

    def test_help_mentions_analyze_casefile(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output), self.assertRaises(SystemExit) as ctx:
            app.main(["--help"])

        self.assertEqual(0, ctx.exception.code)
        self.assertIn("--analyze-casefile", output.getvalue())


if __name__ == "__main__":
    unittest.main()
