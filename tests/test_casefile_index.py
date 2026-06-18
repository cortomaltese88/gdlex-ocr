"""Offline tests for filename-only case-file index detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_index import detect_casefile_indexes


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


if __name__ == "__main__":
    unittest.main()
