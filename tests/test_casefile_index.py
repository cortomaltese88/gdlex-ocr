"""Offline tests for case-file index detection and light parsing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_index import (
    detect_casefile_indexes,
    parse_casefile_index,
)


class CaseFileIndexTest(unittest.TestCase):
    def test_detects_html_index_high_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "indice.html"
            index.write_text("<html></html>", encoding="utf-8")

            indexes = detect_casefile_indexes(root, (index,))

            self.assertEqual(1, len(indexes))
            self.assertEqual("indice.html", indexes[0].relative_path)
            self.assertEqual(".html", indexes[0].extension)
            self.assertEqual("high", indexes[0].confidence)
            self.assertEqual("filename", indexes[0].source)
            self.assertEqual("html", indexes[0].detected_format)

    def test_detects_xml_index_high_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "index.xml"
            index.write_text("<index />", encoding="utf-8")

            indexes = detect_casefile_indexes(root, (index,))

            self.assertEqual(1, len(indexes))
            self.assertEqual("index.xml", indexes[0].relative_path)
            self.assertEqual("high", indexes[0].confidence)
            self.assertEqual("xml", indexes[0].detected_format)

    def test_detects_txt_elenco_medium_or_low(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_text("fixture", encoding="utf-8")

            indexes = detect_casefile_indexes(root, (index,))

            self.assertEqual(1, len(indexes))
            self.assertIn(indexes[0].confidence, {"medium", "low"})
            self.assertEqual("text", indexes[0].detected_format)

    def test_ignores_unrelated_html(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = root / "pagina_web.html"
            page.write_text("<html></html>", encoding="utf-8")

            indexes = detect_casefile_indexes(root, (page,))

            self.assertEqual((), indexes)

    def test_detected_paths_are_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "sub"
            nested.mkdir()
            index = nested / "indice.html"
            index.write_text("<html></html>", encoding="utf-8")

            indexes = detect_casefile_indexes(root, (index,))

            self.assertEqual("sub/indice.html", indexes[0].relative_path)
            self.assertNotIn(str(root), indexes[0].relative_path)

    def test_indexes_are_sorted_by_confidence_then_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            low = root / "pdp.txt"
            medium = root / "z_elenco.txt"
            high_b = root / "b_index.xml"
            high_a = root / "a_indice.html"
            for path in (low, medium, high_b, high_a):
                path.write_text("fixture", encoding="utf-8")

            indexes = detect_casefile_indexes(
                root,
                (low, medium, high_b, high_a),
            )

            self.assertEqual(
                [
                    "a_indice.html",
                    "b_index.xml",
                    "z_elenco.txt",
                    "pdp.txt",
                ],
                [index.relative_path for index in indexes],
            )

    def test_multiple_high_confidence_indexes_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "indice.html").write_text("<html></html>", encoding="utf-8")
            (root / "index.xml").write_text("<index />", encoding="utf-8")

            analysis = analyze_case_folder(root)

            self.assertEqual(2, len(analysis.indexes))
            self.assertEqual(
                ["multiple_casefile_indexes"],
                [warning.code for warning in analysis.warnings],
            )
            self.assertIsNone(analysis.warnings[0].path)
            self.assertNotIn(str(root), analysis.warnings[0].message)

    def test_no_index_is_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "documento.pdf").write_bytes(b"synthetic pdf")

            analysis = analyze_case_folder(root)

            self.assertEqual((), analysis.indexes)
            self.assertEqual((), analysis.warnings)

    def test_parse_txt_index_extracts_pdf_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_text(
                "Documento principale 001_sentenza.pdf\n",
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual(1, len(parsed.entries))
            self.assertEqual("001_sentenza.pdf", parsed.entries[0].referenced_path)
            self.assertEqual("medium", parsed.entries[0].confidence)

    def test_parse_txt_index_extracts_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_text(
                "18/06/2026 - sentenza.pdf\n",
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual("18/06/2026", parsed.entries[0].document_date)

    def test_parse_csv_index_semicolon(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.csv"
            index.write_text(
                "data;file;tipo\n18/06/2026;atti/001_sentenza.pdf;Sentenza\n",
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual(1, len(parsed.entries))
            self.assertEqual("atti/001_sentenza.pdf", parsed.entries[0].referenced_path)
            self.assertEqual("18/06/2026", parsed.entries[0].document_date)
            self.assertEqual("medium", parsed.entries[0].confidence)

    def test_parse_html_index_extracts_pdf_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "indice.html"
            index.write_text(
                '<a href="atti/001_sentenza.pdf">Sentenza</a>',
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual(1, len(parsed.entries))
            self.assertEqual("Sentenza", parsed.entries[0].label)
            self.assertEqual("atti/001_sentenza.pdf", parsed.entries[0].referenced_path)
            self.assertEqual("high", parsed.entries[0].confidence)

    def test_parse_xml_index_extracts_pdf_attribute(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "index.xml"
            index.write_text(
                '<index><doc file="atti/001_sentenza.pdf" /></index>',
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual(1, len(parsed.entries))
            self.assertEqual("atti/001_sentenza.pdf", parsed.entries[0].referenced_path)
            self.assertEqual("medium", parsed.entries[0].confidence)

    def test_parse_index_too_large_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_bytes(b"x" * (2 * 1024 * 1024 + 1))

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual((), parsed.entries)
            self.assertEqual(["index_too_large"], [warning.code for warning in parsed.warnings])

    def test_parse_index_latin1_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_bytes("Sentenza à 001_sentenza.pdf".encode("latin-1"))

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual(1, len(parsed.entries))
            self.assertIn("à", parsed.entries[0].label)
            self.assertEqual("001_sentenza.pdf", parsed.entries[0].referenced_path)

    def test_parse_index_error_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "index.xml"
            index.write_text(
                '<index><doc file="atti/001_sentenza.pdf"></index>',
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertEqual((), parsed.entries)
            self.assertEqual(
                ["index_parse_error"],
                [warning.code for warning in parsed.warnings],
            )

    def test_analyze_case_folder_populates_index_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "atti").mkdir()
            index = root / "indice.html"
            pdf = root / "atti" / "001_sentenza.pdf"
            index.write_text(
                '<a href="atti/001_sentenza.pdf">Sentenza</a>',
                encoding="utf-8",
            )
            pdf.write_bytes(b"synthetic pdf")

            analysis = analyze_case_folder(root)

            self.assertEqual(1, len(analysis.indexes))
            self.assertEqual(1, len(analysis.indexes[0].entries))
            self.assertEqual(
                "atti/001_sentenza.pdf",
                analysis.indexes[0].entries[0].referenced_path,
            )

    def test_index_entry_labels_are_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            index = root / "elenco_documenti.txt"
            index.write_text(
                f"{'Sentenza ' * 40}001_sentenza.pdf\n",
                encoding="utf-8",
            )

            parsed = parse_casefile_index(
                root,
                detect_casefile_indexes(root, (index,))[0],
            )

            self.assertLessEqual(len(parsed.entries[0].label), 160)


if __name__ == "__main__":
    unittest.main()
