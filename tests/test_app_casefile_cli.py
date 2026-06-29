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
from pypdf import PdfReader, PdfWriter


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


def _write_synthetic_pdf(path: Path, pages: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)


def _write_merge_plan(path: Path, items: list[dict[str, object]]) -> None:
    defaults = {
        "exclude_reason": None, "merge_candidate": True,
        "bookmark_title": "Atto", "act_title": None, "act_number": None,
        "act_category": None, "suggested_order": None, "sort_group": None,
        "sort_priority": None, "faldone_number": None, "index_date": None,
        "pg_progressive": None, "total_pages": None, "warnings": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"items": [{**defaults, **item} for item in items]}),
        encoding="utf-8",
    )


class AppCasefileCliTest(unittest.TestCase):
    def test_merge_casefile_pdf_generates_pdf_and_reports_from_revised_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            case_dir.mkdir()
            out_dir.mkdir()
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with (case_dir / "atto.pdf").open("wb") as stream:
                writer.write(stream)
            item = {
                "final_order": 1, "unit_id": "1", "source_pdf": "atto.pdf",
                "include_in_merged_pdf": True, "exclude_reason": None,
                "merge_candidate": True, "bookmark_title": "Atto",
                "bookmark_label": "001 - Atto", "act_title": None,
                "act_number": None, "act_category": None,
                "suggested_order": 1, "sort_group": None,
                "sort_priority": None, "faldone_number": None,
                "index_date": None, "pg_progressive": None,
                "total_pages": 1, "warnings": [],
            }
            (out_dir / "fascicolo_merge_plan.json").write_text(
                json.dumps({"items": [{**item, "bookmark_label": "Originale"}]}),
                encoding="utf-8",
            )
            (out_dir / "fascicolo_merge_plan_revised.json").write_text(
                json.dumps({"items": [item]}), encoding="utf-8"
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout), patch(
                "app.QApplication", side_effect=AssertionError("GUI should not start")
            ):
                status = app.main([
                    "--merge-casefile-pdf", str(case_dir),
                    "--output", str(out_dir),
                ])
            self.assertEqual(0, status)
            self.assertEqual(1, len(PdfReader(out_dir / "fascicolo_unico.pdf").pages))
            report = json.loads((out_dir / "fascicolo_unico_report.json").read_text())
            self.assertEqual("fascicolo_merge_plan_revised.json", report["source_plan"])
            self.assertIn("fascicolo_unico.pdf", stdout.getvalue())
            self.assertTrue((out_dir / "fascicolo_unico_report.md").is_file())
            self.assertFalse((out_dir / "fascicolo_unico_light.pdf").exists())

    def test_merge_casefile_pdf_forwards_optimization_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            case_dir.mkdir()
            out_dir.mkdir()
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with (case_dir / "atto.pdf").open("wb") as stream:
                writer.write(stream)
            item = {
                "final_order": 1, "unit_id": "1", "source_pdf": "atto.pdf",
                "include_in_merged_pdf": True, "exclude_reason": None,
                "merge_candidate": True, "bookmark_title": "Atto",
                "bookmark_label": "001 - Atto", "act_title": None,
                "act_number": None, "act_category": None,
                "suggested_order": 1, "sort_group": None,
                "sort_priority": None, "faldone_number": None,
                "index_date": None, "pg_progressive": None,
                "total_pages": 1, "warnings": [],
            }
            (out_dir / "fascicolo_merge_plan.json").write_text(
                json.dumps({"items": [item]}), encoding="utf-8"
            )

            def fake_optimize(source, output, profile):
                self.assertEqual("balanced", profile)
                output.write_bytes(source.read_bytes())
                return output

            stdout = io.StringIO()
            with redirect_stdout(stdout), patch(
                "gdlex_ocr.casefile_pdf_merge.optimize_casefile_pdf",
                side_effect=fake_optimize,
            ) as optimize:
                status = app.main([
                    "--merge-casefile-pdf", str(case_dir),
                    "--output", str(out_dir), "--pdf-optimize", "balanced",
                ])
            self.assertEqual(0, status)
            optimize.assert_called_once()
            self.assertTrue((out_dir / "fascicolo_unico_light.pdf").is_file())
            self.assertIn("PDF ottimizzato è più grande", stdout.getvalue())

    def test_merge_casefile_pdf_reports_missing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            case_dir.mkdir()
            out_dir.mkdir()
            error = io.StringIO()
            with redirect_stderr(error):
                status = app.main([
                    "--merge-casefile-pdf", str(case_dir),
                    "--output", str(out_dir),
                ])
            self.assertEqual(1, status)
            self.assertIn("Merge plan non trovato", error.getvalue())

    def test_estimate_casefile_pdf_prints_summary_and_does_not_generate_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            _write_synthetic_pdf(case_dir / "one.pdf", 2)
            _write_synthetic_pdf(case_dir / "two.pdf", 1)
            _write_merge_plan(out_dir / "fascicolo_merge_plan.json", [
                {"final_order": 1, "unit_id": "one", "source_pdf": "one.pdf",
                 "include_in_merged_pdf": True, "bookmark_label": "One"},
                {"final_order": None, "unit_id": "two", "source_pdf": "two.pdf",
                 "include_in_merged_pdf": False, "bookmark_label": "Two",
                 "exclude_reason": "duplicato"},
            ])

            stdout = io.StringIO()
            with redirect_stdout(stdout), patch(
                "app.QApplication", side_effect=AssertionError("GUI should not start")
            ):
                status = app.main([
                    "--estimate-casefile-pdf", str(case_dir),
                    "--output", str(out_dir),
                ])

            self.assertEqual(0, status)
            printed = stdout.getvalue()
            self.assertIn("Piano usato: fascicolo_merge_plan.json", printed)
            self.assertIn("Atti inclusi: 1", printed)
            self.assertIn("Atti esclusi: 1", printed)
            self.assertIn("Pagine stimate: 2", printed)
            self.assertIn("Dimensione stimata:", printed)
            self.assertIn("Nessun PDF generato.", printed)
            self.assertFalse((out_dir / "fascicolo_unico.pdf").exists())
            self.assertFalse((out_dir / "fascicolo_unico_light.pdf").exists())
            self.assertFalse((out_dir / "fascicolo_unico_report.json").exists())

    def test_estimate_casefile_pdf_reports_missing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "fascicolo"
            out_dir = Path(temp_dir) / "output"
            case_dir.mkdir()
            out_dir.mkdir()
            error = io.StringIO()
            with redirect_stderr(error):
                status = app.main([
                    "--estimate-casefile-pdf", str(case_dir),
                    "--output", str(out_dir),
                ])
            self.assertEqual(1, status)
            self.assertIn("Merge plan non trovato", error.getvalue())

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
        self.assertIn("--merge-casefile-pdf", output.getvalue())
        self.assertIn("--estimate-casefile-pdf", output.getvalue())
        self.assertIn("--pdf-optimize", output.getvalue())

    def test_pdf_optimize_defaults_to_none_and_rejects_invalid_profile(self) -> None:
        self.assertEqual("none", app.parse_args([]).pdf_optimize)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            app.parse_args(["--pdf-optimize", "invalid"])
        self.assertEqual(2, ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
