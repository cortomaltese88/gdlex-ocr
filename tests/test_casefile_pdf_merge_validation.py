"""Validation tests for case-file PDF merge plans."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from gdlex_ocr.casefile_pdf_merge import validate_casefile_merge_plan


def _write_pdf(path: Path, pages: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as stream:
        writer.write(stream)


def _write_plan(path: Path, items: list[dict[str, object]]) -> None:
    defaults = {
        "final_order": 1,
        "unit_id": "1",
        "source_pdf": "one.pdf",
        "include_in_merged_pdf": True,
        "exclude_reason": None,
        "merge_candidate": True,
        "bookmark_title": "Atto",
        "bookmark_label": "001 - Atto",
        "act_title": None,
        "act_number": None,
        "act_category": None,
        "suggested_order": 1,
        "sort_group": None,
        "sort_priority": None,
        "faldone_number": None,
        "index_date": None,
        "pg_progressive": None,
        "total_pages": 1,
        "warnings": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"items": [{**defaults, **item} for item in items]}),
        encoding="utf-8",
    )


class CasefilePdfMergeValidationTest(unittest.TestCase):
    def test_valid_plan_prefers_revised_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            _write_pdf(root / "one.pdf")
            _write_plan(output / "fascicolo_merge_plan.json", [{
                "source_pdf": "missing.pdf",
            }])
            _write_plan(output / "fascicolo_merge_plan_revised.json", [{
                "source_pdf": "one.pdf",
            }])

            validation = validate_casefile_merge_plan(root, output)

            self.assertTrue(validation["ok"])
            self.assertEqual("fascicolo_merge_plan_revised.json", validation["source_plan"])
            self.assertEqual(1, validation["total_items"])
            self.assertEqual(1, validation["included_items"])
            self.assertEqual([], validation["errors"])

    def test_reports_blocking_and_non_blocking_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            _write_pdf(root / "one.pdf")
            (root / "empty.pdf").parent.mkdir(parents=True, exist_ok=True)
            (root / "empty.pdf").write_bytes(b"")
            _write_plan(output / "fascicolo_merge_plan.json", [
                {
                    "final_order": 1,
                    "source_pdf": "one.pdf",
                    "warnings": [{"code": "synthetic", "message": "warning sintetico"}],
                },
                {
                    "final_order": 1,
                    "unit_id": "2",
                    "source_pdf": "missing.pdf",
                    "bookmark_label": "",
                    "bookmark_title": "",
                    "total_pages": 0,
                },
                {
                    "final_order": None,
                    "unit_id": "3",
                    "source_pdf": "empty.pdf",
                    "include_in_merged_pdf": True,
                },
                {
                    "final_order": None,
                    "unit_id": "4",
                    "source_pdf": "one.pdf",
                    "include_in_merged_pdf": False,
                    "exclude_reason": "duplicato",
                },
            ])

            validation = validate_casefile_merge_plan(root, output)

            self.assertFalse(validation["ok"])
            errors = "\n".join(validation["errors"])
            warnings = "\n".join(validation["warnings"])
            self.assertIn("PDF sorgente non trovato: missing.pdf", errors)
            self.assertIn("Ordine duplicato", errors)
            self.assertIn("Item 4 escluso", warnings)
            self.assertIn("warning sintetico", warnings)
            self.assertIn("bookmark/titolo vuoto", warnings)
            self.assertIn("numero pagine mancante o zero", warnings)
            self.assertIn("PDF sorgente vuoto: empty.pdf", warnings)
            self.assertIn("ordine mancante", warnings)

    def test_reports_missing_plan_and_does_not_create_pdf_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            root.mkdir()
            output.mkdir()

            validation = validate_casefile_merge_plan(root, output)

            self.assertFalse(validation["ok"])
            self.assertIn("Merge plan non trovato", "\n".join(validation["errors"]))
            self.assertFalse((output / "fascicolo_unico.pdf").exists())
            self.assertFalse((output / "fascicolo_unico_light.pdf").exists())

    def test_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            root.mkdir()
            output.mkdir()
            (output / "fascicolo_merge_plan.json").write_text("{", encoding="utf-8")

            validation = validate_casefile_merge_plan(root, output)

            self.assertFalse(validation["ok"])
            self.assertIn("JSON non valido", "\n".join(validation["errors"]))

    def test_reports_plan_without_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            root.mkdir()
            output.mkdir()
            (output / "fascicolo_merge_plan.json").write_text("{}", encoding="utf-8")

            validation = validate_casefile_merge_plan(root, output)

            self.assertFalse(validation["ok"])
            self.assertIn("lista 'items'", "\n".join(validation["errors"]))

    def test_reports_no_included_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "case"
            output = Path(temp_dir) / "output"
            _write_pdf(root / "one.pdf")
            _write_plan(output / "fascicolo_merge_plan.json", [{
                "include_in_merged_pdf": False,
                "exclude_reason": "manuale",
            }])

            validation = validate_casefile_merge_plan(root, output)

            self.assertFalse(validation["ok"])
            self.assertIn("Nessun item incluso", "\n".join(validation["errors"]))
