"""Tests for merge-planning metadata computation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    format_casefile_analysis_markdown,
    format_casefile_units_csv,
)


def _create_enriched_fixture(root: Path) -> None:
    """Create a TIAP fixture with act titles and numbers for merge planning."""
    for uid, num, title in (
        ("100", "4", "CERTIFICATO PENALE"),
        ("200", "12", "VERBALE DI ARRESTO"),
        ("300", None, "ANNOTAZIONE"),
    ):
        d = root / uid
        d.mkdir()
        (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic-" + uid.encode())
        (d / "COMPLETE").write_bytes(b"")
        if num:
            title_tag = f"<title>Documento: {num} - {title}</title>"
        else:
            title_tag = f"<title>{title}</title>"
        (d / "ListaAllegati.html").write_text(
            f"<html><head>{title_tag}</head>"
            f'<body><a href="doc.pdf">{title}</a></body></html>',
            encoding="utf-8",
        )


class CaseFileMergePlanTest(unittest.TestCase):
    def test_bookmark_title_uses_act_number_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")

            self.assertIsNotNone(unit_100.bookmark_title)
            self.assertIn("004", unit_100.bookmark_title)
            self.assertIn("CERTIFICATO PENALE", unit_100.bookmark_title)

    def test_bookmark_title_fallback_without_act_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            unit_300 = next(u for u in analysis.units if u.unit_id == "300")

            self.assertIsNotNone(unit_300.bookmark_title)
            self.assertIn("300", unit_300.bookmark_title)

    def test_suggested_order_uses_act_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")
            unit_200 = next(u for u in analysis.units if u.unit_id == "200")

            self.assertEqual(4, unit_100.suggested_order)
            self.assertEqual(12, unit_200.suggested_order)

    def test_suggested_order_fallback_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            unit_300 = next(u for u in analysis.units if u.unit_id == "300")

            self.assertIsNotNone(unit_300.suggested_order)
            self.assertIsInstance(unit_300.suggested_order, int)

    def test_merge_candidate_true_with_main_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)

            for unit in analysis.units:
                self.assertTrue(
                    unit.merge_candidate,
                    f"unit {unit.unit_id} should be merge candidate",
                )

    def test_merge_candidate_false_without_main_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "999"
            d.mkdir()
            (d / "other.pdf").write_bytes(b"%PDF-1.4")
            (d / "ListaAllegati.html").write_text(
                '<html><body><a href="doc.pdf">Doc</a></body></html>',
                encoding="utf-8",
            )
            d2 = root / "998"
            d2.mkdir()
            (d2 / "998.pdf").write_bytes(b"%PDF-1.4")
            (d2 / "ListaAllegati.html").write_text(
                '<html><body><a href="doc.pdf">Doc</a></body></html>',
                encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            unit_999 = next(
                (u for u in analysis.units if u.unit_id == "999"), None
            )
            if unit_999 is not None:
                self.assertFalse(unit_999.merge_candidate)

    def test_sort_group_assigned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)

            for unit in analysis.units:
                self.assertIsNotNone(unit.sort_group)
                self.assertIsNotNone(unit.sort_priority)

    def test_json_contains_merge_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)

            unit_dict = payload["units"][0]
            self.assertIn("bookmark_title", unit_dict)
            self.assertIn("sort_group", unit_dict)
            self.assertIn("sort_priority", unit_dict)
            self.assertIn("suggested_order", unit_dict)
            self.assertIn("merge_candidate", unit_dict)

    def test_json_contains_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)

            self.assertIn("casefile_profile", payload)
            self.assertIn("casefile_profile_confidence", payload)
            self.assertIn("casefile_profile_reason", payload)
            self.assertEqual("ministeriale_tiap", payload["casefile_profile"])

    def test_markdown_contains_profilo_fascicolo_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            md = format_casefile_analysis_markdown(analysis)

            self.assertIn("## Profilo fascicolo", md)
            self.assertIn("Profilo rilevato:", md)
            self.assertIn("Confidenza:", md)
            self.assertIn("Motivo:", md)
            self.assertIn("Strategia suggerita:", md)

    def test_markdown_units_table_has_order_and_bookmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            md = format_casefile_analysis_markdown(analysis)

            self.assertIn("Ordine", md)
            self.assertIn("Segnalibro", md)

    def test_units_csv_has_new_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            header = csv_text.splitlines()[0]

            self.assertIn("Ordine suggerito", header)
            self.assertIn("Segnalibro", header)
            self.assertIn("Gruppo ordinamento", header)
            self.assertIn("Priorità ordinamento", header)
            self.assertIn("Includi in PDF unico", header)

    def test_units_csv_contains_merge_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertIn("CERTIFICATO PENALE", csv_text)
            self.assertIn("sì", csv_text)

    def test_no_absolute_paths_in_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertNotIn(str(root), csv_text)

    def test_no_absolute_paths_in_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            md = format_casefile_analysis_markdown(analysis)

            self.assertNotIn(str(root), md)

    def test_no_absolute_paths_in_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)
            serialized = json.dumps(payload, ensure_ascii=False)

            self.assertNotIn(str(root), serialized)


if __name__ == "__main__":
    unittest.main()
