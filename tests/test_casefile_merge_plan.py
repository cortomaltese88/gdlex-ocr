"""Tests for merge-planning metadata computation."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_export import (
    casefile_analysis_to_dict,
    format_casefile_analysis_markdown,
    format_casefile_units_csv,
)
from gdlex_ocr.casefile_merge_plan_export import (
    build_casefile_merge_plan,
    default_casefile_merge_plan_csv_path,
    default_casefile_merge_plan_json_path,
    default_casefile_merge_plan_markdown_path,
    format_casefile_merge_plan_csv,
    format_casefile_merge_plan_markdown,
    load_casefile_merge_plan,
    merge_plan_to_dict,
    move_merge_plan_item,
    renumber_merge_plan_items,
    resolve_merge_plan_source_pdf,
    save_revised_merge_plan,
    set_item_bookmark_title,
    set_item_included,
    write_casefile_merge_plan_json,
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
    def test_load_valid_merge_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture"
            root.mkdir()
            _create_enriched_fixture(root)
            original = build_casefile_merge_plan(analyze_case_folder(root))
            path = Path(tmp) / "fascicolo_merge_plan.json"
            write_casefile_merge_plan_json(original, path)

            loaded = load_casefile_merge_plan(path)

            self.assertEqual(original.total_items, loaded.total_items)
            self.assertEqual(original.items[0].source_pdf, loaded.items[0].source_pdf)

    def test_move_renumbers_order_and_bookmark_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)
            plan = build_casefile_merge_plan(analyze_case_folder(root))
            first_unit = plan.items[0].unit_id

            moved = move_merge_plan_item(plan.items, 0, 2)

            self.assertEqual(first_unit, moved[2].unit_id)
            self.assertEqual([1, 2, 3], [item.final_order for item in moved])
            self.assertEqual(
                ["001", "002", "003"],
                [item.bookmark_label[:3] for item in moved],
            )

    def test_manual_exclusion_and_reinclusion_are_coherent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)
            item = build_casefile_merge_plan(analyze_case_folder(root)).items[0]

            excluded = set_item_included(item, False)
            self.assertFalse(excluded.include_in_merged_pdf)
            self.assertEqual("escluso_manualmente", excluded.exclude_reason)

            renumbered = renumber_merge_plan_items((excluded, item))
            self.assertIsNone(renumbered[0].final_order)
            self.assertEqual(1, renumbered[1].final_order)
            self.assertTrue(renumbered[1].bookmark_label.startswith("001 - "))

            reincluded = set_item_included(excluded, True, "duplicato")
            self.assertTrue(reincluded.include_in_merged_pdf)
            self.assertIsNone(reincluded.exclude_reason)

    def test_bookmark_title_edit_recalculates_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)
            item = build_casefile_merge_plan(analyze_case_folder(root)).items[0]

            edited = set_item_bookmark_title(item, "Titolo rivisto")

            self.assertEqual("Titolo rivisto", edited.bookmark_title)
            self.assertEqual("001 - Titolo rivisto", edited.bookmark_label)

    def test_save_revised_plan_writes_privacy_safe_json_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private" / "Desktop" / "fixture"
            root.mkdir(parents=True)
            _create_enriched_fixture(root)
            plan = build_casefile_merge_plan(analyze_case_folder(root))
            output = Path(tmp) / "output"

            json_path, csv_path, markdown_path = save_revised_merge_plan(
                plan, output
            )

            self.assertEqual("fascicolo_merge_plan_revised.json", json_path.name)
            self.assertEqual("fascicolo_merge_plan_revised.csv", csv_path.name)
            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())
            self.assertIsNotNone(markdown_path)
            exported = (
                json_path.read_text(encoding="utf-8")
                + csv_path.read_text(encoding="utf-8-sig")
                + markdown_path.read_text(encoding="utf-8")
            )
            self.assertNotIn(str(root), exported)
            self.assertNotIn("Desktop", exported)

    def test_resolve_source_pdf_accepts_only_paths_inside_casefile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fascicolo"
            expected = root / "100" / "atto.pdf"

            self.assertEqual(
                expected.resolve(),
                resolve_merge_plan_source_pdf(root, "100/atto.pdf"),
            )
            with self.assertRaises(ValueError):
                resolve_merge_plan_source_pdf(root, "/tmp/atto.pdf")
            with self.assertRaises(ValueError):
                resolve_merge_plan_source_pdf(root, "../atto.pdf")
            with self.assertRaises(ValueError):
                resolve_merge_plan_source_pdf(root, "100/../../atto.pdf")

    def test_reviewable_plan_default_output_paths(self) -> None:
        output_dir = Path("output")

        self.assertEqual(
            output_dir / "fascicolo_merge_plan.json",
            default_casefile_merge_plan_json_path(output_dir),
        )
        self.assertEqual(
            output_dir / "fascicolo_merge_plan.csv",
            default_casefile_merge_plan_csv_path(output_dir),
        )
        self.assertEqual(
            output_dir / "fascicolo_merge_plan.md",
            default_casefile_merge_plan_markdown_path(output_dir),
        )

    def test_reviewable_plan_has_one_included_item_per_main_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            plan = build_casefile_merge_plan(analyze_case_folder(root))

            self.assertEqual(3, plan.total_items)
            self.assertEqual(3, plan.total_merge_candidates)
            self.assertEqual(3, plan.total_included)
            self.assertEqual(0, plan.total_excluded)
            self.assertTrue(all(i.include_in_merged_pdf for i in plan.items))
            self.assertTrue(all(i.exclude_reason is None for i in plan.items))

    def test_reviewable_plan_order_and_bookmarks_do_not_use_act_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            plan = build_casefile_merge_plan(analyze_case_folder(root))

            self.assertEqual([1, 2, 3], [i.final_order for i in plan.items])
            self.assertEqual(
                ["001", "002", "003"],
                [i.bookmark_label[:3] for i in plan.items],
            )
            numbered = next(i for i in plan.items if i.act_number == "12")
            self.assertFalse(numbered.bookmark_label.startswith("012"))

    def test_reviewable_plan_tie_is_stable_by_unit_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)
            analysis = analyze_case_folder(root)
            tied = replace(
                analysis,
                units=tuple(
                    replace(u, suggested_order=1)
                    for u in reversed(analysis.units)
                ),
            )

            plan = build_casefile_merge_plan(tied)

            self.assertEqual(["100", "200", "300"], [i.unit_id for i in plan.items])

    def test_reviewable_plan_exports_are_privacy_safe_and_revision_friendly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)
            plan = build_casefile_merge_plan(analyze_case_folder(root))

            serialized = json.dumps(merge_plan_to_dict(plan), ensure_ascii=False)
            csv_text = format_casefile_merge_plan_csv(plan)
            markdown = format_casefile_merge_plan_markdown(plan)

            self.assertNotIn(str(root), serialized + csv_text + markdown)
            for column in (
                "Ordine finale", "Includi", "Motivo esclusione", "Segnalibro"
            ):
                self.assertIn(column, csv_text.splitlines()[0])
            self.assertIn("## Riepilogo merge plan", markdown)
            self.assertIn("Inclusi: 3", markdown)
            self.assertIn("Esclusi: 0", markdown)

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

    def test_suggested_order_does_not_use_act_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _create_enriched_fixture(root)

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")
            unit_200 = next(u for u in analysis.units if u.unit_id == "200")

            self.assertIsNotNone(unit_100.suggested_order)
            self.assertIsNotNone(unit_200.suggested_order)
            self.assertNotEqual(4, unit_100.suggested_order)
            self.assertNotEqual(12, unit_200.suggested_order)

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
