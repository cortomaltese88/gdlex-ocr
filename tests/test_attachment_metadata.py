"""Tests for ministerial ListaAllegati.html metadata extraction."""

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
from gdlex_ocr.casefile_index import (
    AttachmentIndexMetadata,
    parse_attachment_index_metadata,
)

_MINISTERIAL_HTML = """\
<html>
  <head>
    <title>Documento : 021 - SEGUITO D'INDAGINE</title>
  </head>
  <body>
    <td class="testata">Documento : 021 - SEGUITO D'INDAGINE</td>
    <table class="infoDoc">
      <tr><td><li><strong>Faldone</strong> : FALDONE 1</li></td></tr>
      <tr><td><li><strong>Data</strong> : 08/11/2024</li></td></tr>
      <tr><td><li><strong>Tot. Pagine</strong> : 7</li></td></tr>
      <tr><td><li><strong>Data inserimento</strong> : 29/05/2025</li></td></tr>
      <tr><td><li><strong>NR. FASCICOLO</strong> : N 266/3 TRASMISSIONE ATTI</li></td></tr>
    </table>
  </body>
</html>
"""

_MINIMAL_HTML = """\
<html><head><title>Documento : 350 - VERBALE DI CONFERIMENTO</title></head>
<body><li><strong>Data</strong> : 30/10/2024</li></body></html>
"""

_UGLY_HTML = """\
<HTML><HEAD><TITLE>Documento : 378 - ALTRO</TITLE></HEAD>
<BODY>
<LI><STRONG>Faldone</STRONG> : F1</LI>
<LI><STRONG>Data</STRONG> : 04/11/2024</LI>
<LI><STRONG>Tot. Pagine</STRONG> : 80</LI>
<LI><STRONG>ALTRO</STRONG> : FASCICOLO GIP RICHIESTA CONVALIDA</LI>
</BODY></HTML>
"""

_HTML_WITH_PG_PROGRESSIVE = """\
<html><head><title>Documento : 100 - INFORMATIVA</title></head>
<body>
<li><strong>Faldone</strong> : FALDONE 2-FALDONE 2</li>
<li><strong>Data</strong> : 15/11/2024</li>
<li><strong>Tot. Pagine</strong> : 24</li>
<li><strong>Data inserimento</strong> : 29/05/2025</li>
<li><strong>NR. FASCICOLO</strong> : N 266/3-16/2024 TRASMISSIONE ATTI</li>
<li><strong>NOTE</strong> : ESECUZIONE FERMO</li>
</body></html>
"""

_HTML_WITH_ALTRO = """\
<html><head><title>Documento : 378 - ALTRO</title></head>
<body>
<li><strong>Faldone</strong> : FALDONE 1-FALDONE 1</li>
<li><strong>Data</strong> : 04/11/2024</li>
<li><strong>Tot. Pagine</strong> : 5</li>
<li><strong>Data inserimento</strong> : 29/05/2025</li>
<li><strong>ALTRO</strong> : CONVALIDA DI PERQUISIZIONE</li>
</body></html>
"""

_HTML_ANOMALOUS_DATE = """\
<html><head><title>Documento : 050 - VERBALE</title></head>
<body>
<li><strong>Faldone</strong> : FALDONE 1-FALDONE 1</li>
<li><strong>Data</strong> : 08/11/5202</li>
<li><strong>Tot. Pagine</strong> : 3</li>
<li><strong>Data inserimento</strong> : 29/05/2025</li>
</body></html>
"""


class ParseAttachmentIndexMetadataTest(unittest.TestCase):
    def test_extracts_title_from_ministerial_html(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual("SEGUITO D'INDAGINE", meta.act_title)
        self.assertEqual("021", meta.act_number)

    def test_extracts_date_from_ministerial_html(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual("08/11/2024", meta.index_date)

    def test_extracts_description_from_ministerial_html(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertIsNotNone(meta.description)
        self.assertIn("TRASMISSIONE ATTI", meta.description)

    def test_extracts_faldone_and_faldone_number(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual("FALDONE 1", meta.faldone)
        self.assertEqual(1, meta.faldone_number)

    def test_extracts_faldone_number_from_duplicate_pattern(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_PG_PROGRESSIVE)
        self.assertEqual("FALDONE 2-FALDONE 2", meta.faldone)
        self.assertEqual(2, meta.faldone_number)

    def test_extracts_total_pages_as_int(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual(7, meta.total_pages)
        self.assertIsInstance(meta.total_pages, int)

    def test_extracts_total_pages_80(self) -> None:
        meta = parse_attachment_index_metadata(_UGLY_HTML)
        self.assertEqual(80, meta.total_pages)

    def test_extracts_insertion_date(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual("29/05/2025", meta.insertion_date)

    def test_extracts_pg_protocol(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual("N 266/3 TRASMISSIONE ATTI", meta.pg_protocol)

    def test_extracts_pg_progressive(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_PG_PROGRESSIVE)
        self.assertEqual(16, meta.pg_progressive)
        self.assertIsInstance(meta.pg_progressive, int)

    def test_pg_progressive_none_without_pattern(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertIsNone(meta.pg_progressive)

    def test_extracts_notes(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_PG_PROGRESSIVE)
        self.assertEqual("ESECUZIONE FERMO", meta.notes)

    def test_extracts_altro_as_extra_description(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_ALTRO)
        self.assertEqual("CONVALIDA DI PERQUISIZIONE", meta.extra_description)

    def test_description_does_not_merge_all_fields(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_PG_PROGRESSIVE)
        self.assertIsNotNone(meta.pg_protocol)
        self.assertIsNotNone(meta.notes)
        self.assertNotEqual(meta.description, meta.notes)

    def test_description_falls_back_to_pg_protocol(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        self.assertEqual(meta.description, meta.pg_protocol)

    def test_description_falls_back_to_extra_description(self) -> None:
        meta = parse_attachment_index_metadata(_HTML_WITH_ALTRO)
        self.assertEqual(meta.description, meta.extra_description)

    def test_minimal_html_extracts_title_and_date(self) -> None:
        meta = parse_attachment_index_metadata(_MINIMAL_HTML)
        self.assertEqual("VERBALE DI CONFERIMENTO", meta.act_title)
        self.assertEqual("350", meta.act_number)
        self.assertEqual("30/10/2024", meta.index_date)

    def test_ugly_html_case_insensitive(self) -> None:
        meta = parse_attachment_index_metadata(_UGLY_HTML)
        self.assertEqual("ALTRO", meta.act_title)
        self.assertEqual("378", meta.act_number)
        self.assertEqual("04/11/2024", meta.index_date)
        self.assertIsNotNone(meta.description)
        self.assertIn("FASCICOLO GIP", meta.description)

    def test_empty_html_returns_empty_metadata(self) -> None:
        meta = parse_attachment_index_metadata("")
        self.assertIsNone(meta.act_title)
        self.assertIsNone(meta.act_number)
        self.assertIsNone(meta.description)
        self.assertIsNone(meta.index_date)
        self.assertIsNone(meta.faldone)
        self.assertIsNone(meta.faldone_number)
        self.assertIsNone(meta.total_pages)
        self.assertIsNone(meta.insertion_date)
        self.assertIsNone(meta.pg_protocol)
        self.assertIsNone(meta.pg_progressive)
        self.assertIsNone(meta.notes)
        self.assertIsNone(meta.extra_description)

    def test_malformed_html_does_not_crash(self) -> None:
        meta = parse_attachment_index_metadata("<html><head><title></title>")
        self.assertIsInstance(meta, AttachmentIndexMetadata)

    def test_garbage_input_does_not_crash(self) -> None:
        meta = parse_attachment_index_metadata("not html at all \x00\xff")
        self.assertIsInstance(meta, AttachmentIndexMetadata)

    def test_no_title_pattern_returns_none_fields(self) -> None:
        html = "<html><head><title>Some other page</title></head></html>"
        meta = parse_attachment_index_metadata(html)
        self.assertIsNone(meta.act_title)
        self.assertIsNone(meta.act_number)

    def test_skips_faldone_from_description(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        if meta.description:
            self.assertNotIn("FALDONE", meta.description)

    def test_pg_progressive_without_year(self) -> None:
        html = (
            "<html><head><title>Documento : 010 - SIT</title></head>"
            "<body><li><strong>NR. FASCICOLO</strong>"
            " : N 161/3-6 VERBALE SIT</li></body></html>"
        )
        meta = parse_attachment_index_metadata(html)
        self.assertEqual(6, meta.pg_progressive)

    def test_pg_progressive_with_year(self) -> None:
        html = (
            "<html><head><title>Documento : 010 - INFORMATIVA</title></head>"
            "<body><li><strong>NR. FASCICOLO</strong>"
            " : N 266/3-16/2024 TRASMISSIONE ATTI</li></body></html>"
        )
        meta = parse_attachment_index_metadata(html)
        self.assertEqual(16, meta.pg_progressive)

    def test_privacy_fields_not_in_description(self) -> None:
        html = (
            "<html><head><title>Documento : 004 - CERT</title></head>"
            "<body>"
            "<li><strong>Data</strong> : 01/01/2024</li>"
            "<li><strong>Soggetto Cognome/Nome</strong> : ROSSI/MARIO</li>"
            "</body></html>"
        )
        meta = parse_attachment_index_metadata(html)
        self.assertIsNone(meta.extra_description)


class UnitEnrichmentTest(unittest.TestCase):
    def test_unit_enriched_from_lista_allegati(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "100"
            d.mkdir()
            (d / "100.pdf").write_bytes(b"%PDF-synthetic")
            (d / "COMPLETE").write_bytes(b"")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            unit = analysis.units[0]

            self.assertEqual("SEGUITO D'INDAGINE", unit.act_title)
            self.assertEqual("021", unit.act_number)
            self.assertEqual("08/11/2024", unit.index_date)
            self.assertIsNotNone(unit.description)
            self.assertEqual("FALDONE 1", unit.faldone)
            self.assertEqual(1, unit.faldone_number)
            self.assertEqual(7, unit.total_pages)
            self.assertEqual("29/05/2025", unit.insertion_date)
            self.assertIsNotNone(unit.pg_protocol)

    def test_unit_without_lista_allegati_has_no_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "200"
            d.mkdir()
            (d / "200.pdf").write_bytes(b"%PDF-synthetic")

            analysis = analyze_case_folder(root)
            unit = analysis.units[0]

            self.assertIsNone(unit.act_title)
            self.assertIsNone(unit.act_number)
            self.assertIsNone(unit.index_date)
            self.assertIsNone(unit.faldone)
            self.assertIsNone(unit.faldone_number)
            self.assertIsNone(unit.total_pages)

    def test_unit_with_empty_lista_allegati(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "300"
            d.mkdir()
            (d / "300.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text("", encoding="utf-8")

            analysis = analyze_case_folder(root)
            unit = analysis.units[0]

            self.assertIsNone(unit.act_title)

    def test_unit_with_unreadable_lista_allegati(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "400"
            d.mkdir()
            (d / "400.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_bytes(b"\x80\x81\x82")

            analysis = analyze_case_folder(root)

            self.assertEqual(1, len(analysis.units))


class SuggestedOrderTest(unittest.TestCase):
    def test_suggested_order_does_not_use_act_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid, html in (
                ("100", _MINISTERIAL_HTML),
                ("200", _HTML_WITH_PG_PROGRESSIVE),
            ):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")
            unit_200 = next(u for u in analysis.units if u.unit_id == "200")

            self.assertIsNotNone(unit_100.suggested_order)
            self.assertIsNotNone(unit_200.suggested_order)
            self.assertNotEqual(int(unit_100.act_number), unit_100.suggested_order)

    def test_order_uses_faldone_date_pg_unit_id_hierarchy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            htmls = {
                "100": (
                    "<html><head><title>Documento : 001 - A</title></head>"
                    "<body>"
                    "<li><strong>Faldone</strong> : FALDONE 2-FALDONE 2</li>"
                    "<li><strong>Data</strong> : 01/01/2024</li>"
                    "</body></html>"
                ),
                "200": (
                    "<html><head><title>Documento : 002 - B</title></head>"
                    "<body>"
                    "<li><strong>Faldone</strong> : FALDONE 1-FALDONE 1</li>"
                    "<li><strong>Data</strong> : 15/06/2024</li>"
                    "</body></html>"
                ),
                "300": (
                    "<html><head><title>Documento : 003 - C</title></head>"
                    "<body>"
                    "<li><strong>Faldone</strong> : FALDONE 1-FALDONE 1</li>"
                    "<li><strong>Data</strong> : 01/01/2024</li>"
                    "</body></html>"
                ),
            }
            for uid, html in htmls.items():
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)
            orders = {u.unit_id: u.suggested_order for u in analysis.units}

            self.assertLess(orders["300"], orders["200"])
            self.assertLess(orders["200"], orders["100"])

    def test_anomalous_date_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid, html in (
                ("100", _HTML_ANOMALOUS_DATE),
                ("200", _MINISTERIAL_HTML),
            ):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)

            self.assertEqual(2, len(analysis.units))
            for unit in analysis.units:
                self.assertIsNotNone(unit.suggested_order)

    def test_anomalous_date_gets_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid, html in (
                ("100", _HTML_ANOMALOUS_DATE),
                ("200", _MINISTERIAL_HTML),
            ):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")

            warning_codes = [w.code for w in unit_100.warnings]
            self.assertIn("anomalous_date", warning_codes)

    def test_anomalous_date_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid, html in (
                ("100", _HTML_ANOMALOUS_DATE),
                ("200", _MINISTERIAL_HTML),
            ):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)
            unit_100 = next(u for u in analysis.units if u.unit_id == "100")

            self.assertEqual("low", unit_100.order_source_confidence)

    def test_order_source_fields_populated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "100"
            d.mkdir()
            (d / "100.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )
            d2 = root / "200"
            d2.mkdir()
            (d2 / "200.pdf").write_bytes(b"%PDF-synthetic")
            (d2 / "ListaAllegati.html").write_text(
                _HTML_WITH_PG_PROGRESSIVE, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)

            for unit in analysis.units:
                self.assertIsNotNone(unit.order_source_kind)
                self.assertIsNotNone(unit.order_source_value)
                self.assertIsNotNone(unit.order_source_confidence)

    def test_stable_order_with_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html = (
                "<html><head><title>Documento : 001 - A</title></head>"
                "<body>"
                "<li><strong>Faldone</strong> : FALDONE 1-FALDONE 1</li>"
                "<li><strong>Data</strong> : 01/01/2024</li>"
                "</body></html>"
            )
            for uid in ("100", "200", "300"):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(html, encoding="utf-8")

            analysis = analyze_case_folder(root)
            orders = [u.suggested_order for u in analysis.units]

            self.assertEqual(sorted(orders), orders)
            self.assertEqual(len(set(orders)), len(orders))


class EnrichedJsonExportTest(unittest.TestCase):
    def test_json_contains_new_act_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "500"
            d.mkdir()
            (d / "500.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)
            unit = payload["units"][0]

            self.assertEqual("SEGUITO D'INDAGINE", unit["act_title"])
            self.assertEqual("021", unit["act_number"])
            self.assertEqual("08/11/2024", unit["index_date"])
            self.assertIn("description", unit)
            json.dumps(payload, ensure_ascii=False)

    def test_json_contains_enriched_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "500"
            d.mkdir()
            (d / "500.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _HTML_WITH_PG_PROGRESSIVE, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)
            unit = payload["units"][0]

            self.assertEqual(2, unit["faldone_number"])
            self.assertEqual(24, unit["total_pages"])
            self.assertEqual("29/05/2025", unit["insertion_date"])
            self.assertIn("266/3-16/2024", unit["pg_protocol"] or "")
            self.assertEqual(16, unit["pg_progressive"])
            self.assertEqual("ESECUZIONE FERMO", unit["notes"])
            self.assertIn("order_source_kind", unit)
            self.assertIn("order_source_value", unit)
            self.assertIn("order_source_confidence", unit)
            json.dumps(payload, ensure_ascii=False)

    def test_json_act_fields_null_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "600"
            d.mkdir()
            (d / "600.pdf").write_bytes(b"%PDF-synthetic")

            analysis = analyze_case_folder(root)
            payload = casefile_analysis_to_dict(analysis)
            unit = payload["units"][0]

            self.assertIsNone(unit["act_title"])
            self.assertIsNone(unit["act_number"])
            self.assertIsNone(unit["faldone"])
            self.assertIsNone(unit["faldone_number"])
            self.assertIsNone(unit["total_pages"])
            self.assertIsNone(unit["pg_protocol"])
            self.assertIsNone(unit["pg_progressive"])
            self.assertIsNone(unit["notes"])
            self.assertIsNone(unit["extra_description"])


class EnrichedMarkdownExportTest(unittest.TestCase):
    def test_markdown_units_table_has_atto_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "700"
            d.mkdir()
            (d / "700.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("Atto/Titolo", markdown)
            self.assertIn("SEGUITO D'INDAGINE", markdown)

    def test_markdown_units_table_has_faldone_and_pg_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "700"
            d.mkdir()
            (d / "700.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _HTML_WITH_PG_PROGRESSIVE, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("Faldone", markdown)
            self.assertIn("Progr. PG", markdown)
            self.assertIn("| 2 |", markdown)
            self.assertIn("| 16", markdown)

    def test_markdown_strategy_mentions_hierarchy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid in ("100", "200"):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(
                    _MINISTERIAL_HTML, encoding="utf-8",
                )

            analysis = analyze_case_folder(root)
            markdown = format_casefile_analysis_markdown(analysis)

            self.assertIn("faldone + data atto + progressivo PG + unit_id", markdown)


class EnrichedUnitsCsvExportTest(unittest.TestCase):
    def test_units_csv_has_atto_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "800"
            d.mkdir()
            (d / "800.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            lines = csv_text.strip().splitlines()

            self.assertIn("Atto", lines[0])
            self.assertIn("Descrizione", lines[0])
            self.assertIn("Data indice", lines[0])
            self.assertIn("SEGUITO D'INDAGINE", csv_text)

    def test_units_csv_has_new_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "800"
            d.mkdir()
            (d / "800.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _HTML_WITH_PG_PROGRESSIVE, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)
            header = csv_text.splitlines()[0]

            self.assertIn("Faldone", header)
            self.assertIn("Tot. pagine", header)
            self.assertIn("Data inserimento", header)
            self.assertIn("Protocollo PG", header)
            self.assertIn("Progressivo PG", header)
            self.assertIn("Note", header)
            self.assertIn("Descrizione extra", header)
            self.assertIn("Fonte ordine", header)
            self.assertIn("Confidenza ordine", header)

    def test_units_csv_no_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / "900"
            d.mkdir()
            (d / "900.pdf").write_bytes(b"%PDF-synthetic")
            (d / "ListaAllegati.html").write_text(
                _MINISTERIAL_HTML, encoding="utf-8",
            )

            analysis = analyze_case_folder(root)
            csv_text = format_casefile_units_csv(analysis)

            self.assertNotIn(str(root), csv_text)


if __name__ == "__main__":
    unittest.main()
