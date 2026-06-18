"""Tests for PDP/TIAP ministerial documentary unit detection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import (
    DocumentType,
    analyze_case_folder,
)
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    format_casefile_analysis_markdown,
)


def _create_ministerial_fixture(root: Path) -> None:
    for unit_id in ("711273", "711274"):
        unit_dir = root / unit_id
        unit_dir.mkdir()
        (unit_dir / f"{unit_id}.pdf").write_bytes(b"%PDF-synthetic")
        (unit_dir / "COMPLETE").write_bytes(b"")
        (unit_dir / "ListaAllegati.html").write_text(
            "<html><body><a href=\"doc.pdf\">Documento</a></body></html>",
            encoding="utf-8",
        )


class CaseFileUnitsTest(unittest.TestCase):
    def test_detects_ministerial_numeric_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)

            self.assertEqual(2, len(analysis.units))
            self.assertEqual(
                ["711273", "711274"],
                [u.unit_id for u in analysis.units],
            )

    def test_unit_detects_main_pdf_lista_allegati_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)

            unit = next(u for u in analysis.units if u.unit_id == "711273")
            self.assertEqual("711273/711273.pdf", unit.main_pdf_path)
            self.assertEqual(
                "711273/ListaAllegati.html",
                unit.attachment_index_path,
            )
            self.assertEqual("711273/COMPLETE", unit.complete_marker_path)
            self.assertIsNotNone(unit.main_document_id)

    def test_lista_allegati_detected_as_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)

            self.assertGreater(len(analysis.indexes), 0)
            lista_indexes = [
                idx
                for idx in analysis.indexes
                if "ListaAllegati.html" in idx.relative_path
            ]
            self.assertGreater(len(lista_indexes), 0)
            for idx in lista_indexes:
                self.assertEqual("html", idx.detected_format)
                self.assertIn(idx.confidence, ("high", "medium"))

    def test_complete_marker_classified_as_technical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)

            complete_docs = [
                d
                for d in analysis.documents
                if d.filename == "COMPLETE"
            ]
            self.assertGreater(len(complete_docs), 0)
            for doc in complete_docs:
                self.assertEqual(DocumentType.MARKER_TECNICO, doc.document_type)

    def test_duplicate_complete_markers_do_not_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)

            duplicate_warnings = [
                w
                for w in analysis.warnings
                if w.code == "duplicate_file"
                and w.path
                and "COMPLETE" in w.path
            ]
            self.assertEqual(0, len(duplicate_warnings))

    def test_casefile_json_exports_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)

            self.assertIn("units", payload)
            self.assertEqual(2, payload["summary"]["total_units"])
            unit_ids = [u["unit_id"] for u in payload["units"]]
            self.assertIn("711273", unit_ids)
            self.assertIn("711274", unit_ids)
            json.dumps(payload, ensure_ascii=False)

    def test_casefile_markdown_prioritizes_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_ministerial_fixture(root)

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Unità documentali PDP/TIAP", markdown)
            self.assertIn("711273", markdown)
            self.assertIn("ListaAllegati.html", markdown)
            units_pos = markdown.index("## Unità documentali PDP/TIAP")
            docs_pos = markdown.index("## Documenti")
            self.assertLess(units_pos, docs_pos)

    def test_existing_generic_casefile_behavior_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sentenza.pdf").write_bytes(b"%PDF-1.4")
            (root / "memoria.pdf").write_bytes(b"%PDF-1.4 memoria")

            analysis = analyze_case_folder(root)

            self.assertEqual(0, len(analysis.units))
            self.assertEqual(2, analysis.total_files)
            self.assertEqual(2, analysis.total_pdf_files)
            types = {d.document_type for d in analysis.documents}
            self.assertIn(DocumentType.SENTENZA, types)
            self.assertIn(DocumentType.MEMORIA, types)

    def test_numeric_pdf_classification_can_use_unit_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit_dir = root / "999"
            unit_dir.mkdir()
            (unit_dir / "999.pdf").write_bytes(b"%PDF-synthetic")

            analysis = analyze_case_folder(root)

            self.assertEqual(1, len(analysis.units))
            unit = analysis.units[0]
            self.assertEqual("999", unit.unit_id)
            self.assertEqual("999/999.pdf", unit.main_pdf_path)
            doc = next(
                d for d in analysis.documents if d.relative_path == "999/999.pdf"
            )
            self.assertIsNotNone(doc)
            self.assertIsNotNone(unit.main_document_id)
            self.assertEqual(doc.id, unit.main_document_id)


if __name__ == "__main__":
    unittest.main()
