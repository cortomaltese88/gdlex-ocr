"""Synthetic tests for safe, bookmarked case-file PDF generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

from gdlex_ocr.casefile_pdf_merge import (
    CaseFilePdfMergeError,
    build_casefile_pdf_merge_job,
    estimate_casefile_pdf_merge_size,
    format_bytes,
    merge_casefile_pdfs,
    optimize_casefile_pdf,
    resolve_safe_source_pdf,
    select_casefile_pdf_for_ocr,
    select_casefile_merge_plan,
)


def _pdf(path: Path, pages: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)


def _plan(path: Path, items: list[dict[str, object]]) -> None:
    defaults = {
        "exclude_reason": None, "merge_candidate": True,
        "bookmark_title": "Atto", "act_title": None, "act_number": None,
        "act_category": None, "suggested_order": None, "sort_group": None,
        "sort_priority": None, "faldone_number": None, "index_date": None,
        "pg_progressive": None, "total_pages": None, "warnings": [],
    }
    payload = {"items": [{**defaults, **item} for item in items]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class CaseFilePdfMergeTest(unittest.TestCase):
    def test_ocr_pdf_selection_prefers_light_and_falls_back_to_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            original = output / "fascicolo_unico.pdf"
            light = output / "fascicolo_unico_light.pdf"
            original.write_bytes(b"not-opened-original")
            self.assertEqual(original, select_casefile_pdf_for_ocr(output))
            light.write_bytes(b"not-opened-light")
            self.assertEqual(light, select_casefile_pdf_for_ocr(output))
            self.assertEqual(
                original, select_casefile_pdf_for_ocr(output, prefer_light=False)
            )

    def test_ocr_pdf_selection_handles_missing_outputs_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(select_casefile_pdf_for_ocr(Path(tmp)))
        with self.assertRaisesRegex(
            CaseFilePdfMergeError, "Cartella output del fascicolo non trovata"
        ):
            select_casefile_pdf_for_ocr(Path("/tmp/nonexistent-casefile-output"))

    def test_format_bytes(self) -> None:
        self.assertEqual("499 MB", format_bytes(499 * 1024 * 1024))
        self.assertEqual("1.2 GB", format_bytes(1288490189))

    def test_estimate_sums_only_included_pdf_sizes_and_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp) / "root", Path(tmp) / "output"
            _pdf(root / "one.pdf", 1)
            _pdf(root / "two.pdf", 2)
            _pdf(root / "excluded.pdf", 1)
            _plan(output / "fascicolo_merge_plan.json", [
                {"final_order": 1, "unit_id": "1", "source_pdf": "one.pdf",
                 "include_in_merged_pdf": True, "bookmark_label": "One",
                 "total_pages": 1},
                {"final_order": 2, "unit_id": "2", "source_pdf": "two.pdf",
                 "include_in_merged_pdf": True, "bookmark_label": "Two",
                 "total_pages": 2},
                {"final_order": None, "unit_id": "3", "source_pdf": "excluded.pdf",
                 "include_in_merged_pdf": False, "bookmark_label": "Excluded",
                 "total_pages": 1},
            ])
            estimate = estimate_casefile_pdf_merge_size(
                build_casefile_pdf_merge_job(root, output)
            )
            expected = (root / "one.pdf").stat().st_size + (root / "two.pdf").stat().st_size
            self.assertEqual(expected, estimate.source_size_bytes)
            self.assertEqual(2, estimate.included_pdf_count)
            self.assertEqual(1, estimate.excluded_pdf_count)
            self.assertEqual(3, estimate.estimated_page_count)
            self.assertEqual(expected / 3, estimate.average_bytes_per_page)

    def test_optimization_requires_ghostscript_and_preserves_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "original.pdf"
            output = Path(tmp) / "light.pdf"
            _pdf(source, 1)
            original = source.read_bytes()
            with patch("gdlex_ocr.casefile_pdf_merge.shutil.which", return_value=None):
                with self.assertRaisesRegex(CaseFilePdfMergeError, "Ghostscript non disponibile"):
                    optimize_casefile_pdf(source, output, "balanced")
            self.assertEqual(original, source.read_bytes())
            self.assertFalse(output.exists())

    def test_optimization_uses_tmp_and_expected_ghostscript_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "original.pdf"
            output = Path(tmp) / "light.pdf"
            _pdf(source, 1)

            def fake_run(command, **kwargs):
                target = Path(next(x.split("=", 1)[1] for x in command if x.startswith("-sOutputFile=")))
                _pdf(target, 1)
                return type("Completed", (), {"returncode": 0, "stderr": "", "stdout": ""})()

            with (
                patch("gdlex_ocr.casefile_pdf_merge.shutil.which", return_value="/usr/bin/gs"),
                patch("gdlex_ocr.casefile_pdf_merge.subprocess.run", side_effect=fake_run) as run,
            ):
                result = optimize_casefile_pdf(source, output, "balanced")
            self.assertEqual(output, result)
            self.assertTrue(output.is_file())
            self.assertFalse((Path(tmp) / "light.pdf.tmp").exists())
            command = run.call_args.args[0]
            self.assertIn("-dPDFSETTINGS=/printer", command)
            self.assertIn(f"-sOutputFile={output}.tmp", command)
            self.assertEqual(str(source), command[-1])

    def test_none_profile_does_not_call_ghostscript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "original.pdf"
            _pdf(source, 1)
            with patch("gdlex_ocr.casefile_pdf_merge.subprocess.run") as run:
                self.assertEqual(source, optimize_casefile_pdf(source, Path(tmp) / "x.pdf", "none"))
            run.assert_not_called()

    def test_plan_selection_prefers_revised_and_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            original = output / "fascicolo_merge_plan.json"
            original.write_text("{}", encoding="utf-8")
            self.assertEqual(original, select_casefile_merge_plan(output))
            revised = output / "fascicolo_merge_plan_revised.json"
            revised.write_text("{}", encoding="utf-8")
            self.assertEqual(revised, select_casefile_merge_plan(output))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(CaseFilePdfMergeError, "Merge plan non trovato"):
                select_casefile_merge_plan(Path(tmp))

    def test_safe_source_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            source = root / "a" / "one.pdf"
            _pdf(source, 1)
            self.assertEqual(source.resolve(), resolve_safe_source_pdf(root, "a/one.pdf"))
            for unsafe in ("/tmp/one.pdf", "../one.pdf", "a/../../one.pdf"):
                with self.subTest(unsafe=unsafe), self.assertRaises(CaseFilePdfMergeError):
                    resolve_safe_source_pdf(root, unsafe)
            with self.assertRaisesRegex(CaseFilePdfMergeError, "non è un PDF"):
                resolve_safe_source_pdf(root, "a/one.txt")
            with self.assertRaisesRegex(CaseFilePdfMergeError, "non trovato"):
                resolve_safe_source_pdf(root, "missing.pdf")

    def test_rejects_symlink_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "root"
            root.mkdir()
            outside = base / "outside.pdf"
            _pdf(outside, 1)
            (root / "link.pdf").symlink_to(outside)
            with self.assertRaisesRegex(CaseFilePdfMergeError, "esce"):
                resolve_safe_source_pdf(root, "link.pdf")

    def test_merge_order_exclusions_bookmarks_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, output = base / "private" / "root", base / "output"
            _pdf(root / "a.pdf", 2)
            _pdf(root / "b.pdf", 1)
            _pdf(root / "excluded.pdf", 4)
            _plan(output / "fascicolo_merge_plan_revised.json", [
                {"final_order": 2, "unit_id": "a", "source_pdf": "a.pdf",
                 "include_in_merged_pdf": True, "bookmark_label": "002 - Secondo"},
                {"final_order": None, "unit_id": "x", "source_pdf": "excluded.pdf",
                 "include_in_merged_pdf": False, "exclude_reason": "duplicato",
                 "bookmark_label": "Escluso"},
                {"final_order": 1, "unit_id": "b", "source_pdf": "b.pdf",
                 "include_in_merged_pdf": True, "bookmark_label": "001 - Primo"},
            ])

            result = merge_casefile_pdfs(build_casefile_pdf_merge_job(root, output))

            reader = PdfReader(result.pdf_path)
            self.assertEqual(3, len(reader.pages))
            self.assertEqual(["001 - Primo", "002 - Secondo"], [x.title for x in reader.outline])
            self.assertEqual([0, 1], [reader.get_destination_page_number(x) for x in reader.outline])
            report = json.loads(result.report_json_path.read_text(encoding="utf-8"))
            self.assertEqual("fascicolo_merge_plan_revised.json", report["source_plan"])
            self.assertEqual(3, report["total_pages"])
            self.assertEqual(2, report["included_items"])
            self.assertEqual(1, report["excluded_items"])
            expected_size = (root / "a.pdf").stat().st_size + (root / "b.pdf").stat().st_size
            self.assertEqual(expected_size, report["estimated_source_size_bytes"])
            self.assertEqual(result.pdf_path.stat().st_size, report["actual_output_size_bytes"])
            self.assertEqual("none", report["optimization_profile"])
            self.assertIsNone(report["optimized_output_pdf"])
            self.assertEqual(["b.pdf", "a.pdf"], [x["source_pdf"] for x in report["items"]])
            combined = result.report_json_path.read_text() + result.report_markdown_path.read_text()
            self.assertNotIn(str(base), combined)
            self.assertIn("## Atti inclusi", combined)
            self.assertIn("## Atti esclusi", combined)
            self.assertIn("## Dimensione PDF", combined)

    def test_preflight_failure_leaves_no_temporary_or_final_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, output = Path(tmp) / "root", Path(tmp) / "output"
            root.mkdir()
            (root / "bad.pdf").write_text("not a PDF", encoding="utf-8")
            _plan(output / "fascicolo_merge_plan.json", [{
                "final_order": 1, "unit_id": "bad", "source_pdf": "bad.pdf",
                "include_in_merged_pdf": True, "bookmark_label": "Bad",
            }])
            with self.assertRaisesRegex(CaseFilePdfMergeError, "non leggibile"):
                merge_casefile_pdfs(build_casefile_pdf_merge_job(root, output))
            self.assertFalse((output / "fascicolo_unico.pdf").exists())
            self.assertFalse((output / "fascicolo_unico.pdf.tmp").exists())


if __name__ == "__main__":
    unittest.main()
