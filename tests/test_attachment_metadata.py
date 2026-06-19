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

    def test_skips_faldone_and_page_count(self) -> None:
        meta = parse_attachment_index_metadata(_MINISTERIAL_HTML)
        if meta.description:
            self.assertNotIn("FALDONE", meta.description)


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
