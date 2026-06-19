"""Tests for deterministic folder-profile detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gdlex_ocr.casefile import analyze_case_folder
from gdlex_ocr.casefile_profile import detect_casefile_profile


class CaseFileProfileTest(unittest.TestCase):
    def test_ministeriale_tiap_with_numeric_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid in ("100", "200", "300"):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "COMPLETE").write_bytes(b"")
                (d / "ListaAllegati.html").write_text(
                    '<html><body><a href="doc.pdf">Doc</a></body></html>',
                    encoding="utf-8",
                )

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("ministeriale_tiap", profile.profile)
            self.assertEqual("high", profile.confidence)
            self.assertIn("3", profile.reason)
            self.assertIn("ListaAllegati.html", profile.reason)

    def test_immagini_scansioni_tiff_majority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(8):
                (root / f"scan_{i:03d}.tiff").write_bytes(b"II*\x00")
            (root / "note.txt").write_bytes(b"note")
            (root / "extra.jpg").write_bytes(b"\xff\xd8")

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("immagini_scansioni", profile.profile)
            self.assertIn(profile.confidence, ("high", "medium"))

    def test_immagini_scansioni_jpg_majority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(6):
                (root / f"foto_{i:03d}.jpg").write_bytes(b"\xff\xd8")
            (root / "readme.txt").write_bytes(b"info")

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("immagini_scansioni", profile.profile)

    def test_pdf_sciolti_with_loose_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(5):
                (root / f"doc_{i:03d}.pdf").write_bytes(b"%PDF-1.4")

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("pdf_sciolti", profile.profile)
            self.assertIn(profile.confidence, ("high", "medium"))

    def test_misto_pdf_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc1.pdf").write_bytes(b"%PDF-1.4")
            (root / "doc2.pdf").write_bytes(b"%PDF-1.4")
            (root / "scan.tiff").write_bytes(b"II*\x00")
            (root / "notes.txt").write_bytes(b"note")

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("misto", profile.profile)
            self.assertEqual("medium", profile.confidence)

    def test_sconosciuto_empty_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("sconosciuto", profile.profile)
            self.assertEqual("low", profile.confidence)

    def test_sconosciuto_few_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "readme.txt").write_bytes(b"hello")

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("sconosciuto", profile.profile)

    def test_ministeriale_tiap_two_units_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for uid in ("100", "200"):
                d = root / uid
                d.mkdir()
                (d / f"{uid}.pdf").write_bytes(b"%PDF-synthetic")
                (d / "ListaAllegati.html").write_text(
                    '<html><body><a href="d.pdf">D</a></body></html>',
                    encoding="utf-8",
                )

            analysis = analyze_case_folder(root)
            profile = detect_casefile_profile(analysis)

            self.assertEqual("ministeriale_tiap", profile.profile)


if __name__ == "__main__":
    unittest.main()
